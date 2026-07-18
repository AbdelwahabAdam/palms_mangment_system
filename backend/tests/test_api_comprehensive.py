"""End-to-end coverage for every registered Palms API route and worker flow."""

from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO
import re
import sys
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from PIL import Image
from sqlalchemy import select
from webtest import TestApp

from palms_api.config import Settings
from palms_api.database import Database
from palms_api.email_service import EmailService, MemoryEmailTransport
from palms_api.models import (
    Base,
    PalmImage,
    PasswordResetToken,
    ReportRun,
    ReportSchedule,
    ReportScheduleRecipient,
    Role,
    UserSession,
    utcnow,
)
from palms_api.reporting import (
    RQReportExecutor,
    SynchronousReportExecutor,
    execute_report_run,
)
from palms_api.scheduler import report_executor, run_due_schedules
from palms_api.seeding import seed_system_rbac
from palms_api.storage import MemoryStorageClient, safe_storage_key
from palms_api.worker import generate_report_job

PASSWORD = "StrongPassword123"


def _image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGBA", (480, 320), (40, 120, 75, 160)).save(output, format="PNG")
    return output.getvalue()


def _message_text(message) -> str:
    body = message.get_body(preferencelist=("plain",))
    assert body is not None
    return body.get_content()


def _token_from_message(message) -> str:
    match = re.search(r"token=([A-Za-z0-9_-]+)", _message_text(message))
    assert match is not None
    return match.group(1)


def _role_id(app, role_name: str) -> str:
    session = app.registry.palms_database.session_factory()
    try:
        role = session.scalar(select(Role).where(Role.name == role_name))
        assert role is not None
        return str(role.id)
    finally:
        session.close()


def _create_palm(client: TestApp, *, donor_id: str, section_id: str, code: str) -> dict:
    return client.post_json(
        "/api/v1/admin/palms",
        {
            "code": code,
            "donor_id": donor_id,
            "section_id": section_id,
            "plantation_date": "2021-06-01",
            "status": "active",
            "current_health_status": "healthy",
        },
    ).json["data"]


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("get", "/api/v1/auth/me", None),
        ("post_json", "/api/v1/auth/logout", {}),
        (
            "post_json",
            "/api/v1/auth/change-password",
            {"current_password": PASSWORD, "new_password": "ChangedPassword456"},
        ),
        ("post_json", "/api/v1/auth/2fa/enable", {}),
        ("get", "/api/v1/admin/profile", None),
        ("patch_json", "/api/v1/admin/profile", {"full_name": "Unauthenticated"}),
        ("get", "/api/v1/admin/donors", None),
        ("get", "/api/v1/admin/dashboard/overview", None),
        ("get", "/api/v1/admin/reports/types", None),
    ],
)
def test_authenticated_route_families_reject_missing_sessions(
    client: TestApp, method: str, path: str, payload: dict | None
) -> None:
    """Every private API family reaches authorization before performing work."""
    request = getattr(client, method)
    response = request(path, payload, status=401) if payload is not None else request(path, status=401)
    assert response.json["error"]["code"] == "unauthorized"


def test_auth_profile_reset_two_factor_and_session_failures(
    app, client: TestApp, make_user, login, memory_email
) -> None:
    account = make_user(email="auth@example.com")
    make_user(email="taken@example.com")

    login(client, email=account["email"])
    assert client.post_json("/api/v1/auth/2fa/enable", {}).json["data"] == {
        "enabled": True,
        "mode": "placeholder",
    }
    assert client.post_json("/api/v1/auth/2fa/disable", {}).json["data"] == {
        "enabled": False,
        "mode": "placeholder",
    }
    assert client.get("/api/v1/admin/profile").json["data"]["email"] == account["email"]
    assert client.patch_json(
        "/api/v1/admin/profile", {"full_name": "Updated Auth User"}
    ).json["data"]["full_name"] == "Updated Auth User"
    assert client.patch_json("/api/v1/admin/profile", {}, status=422).json["error"]["code"] == "validation_error"

    assert client.post_json(
        "/api/v1/admin/profile/change-email",
        {"current_password": "wrong", "new_email": "renamed@example.com"},
        status=400,
    ).json["error"]["code"] == "invalid_current_password"
    assert client.post_json(
        "/api/v1/admin/profile/change-email",
        {"current_password": PASSWORD, "new_email": "taken@example.com"},
        status=409,
    ).json["error"]["code"] == "conflict"
    changed_email = client.post_json(
        "/api/v1/admin/profile/change-email",
        {"current_password": PASSWORD, "new_email": "renamed@example.com"},
    )
    assert changed_email.json["data"]["email"] == "renamed@example.com"

    assert client.post_json(
        "/api/v1/admin/profile/change-password",
        {"current_password": "wrong", "new_password": "ChangedPassword456"},
        status=400,
    ).json["error"]["code"] == "invalid_current_password"
    assert client.post_json(
        "/api/v1/admin/profile/change-password",
        {"current_password": PASSWORD, "new_password": "ChangedPassword456"},
    ).json["data"]["reauthentication_required"] is True
    client.get("/api/v1/auth/me", status=401)
    login(client, email="renamed@example.com", password="ChangedPassword456")

    generic_missing = client.post_json(
        "/api/v1/auth/forgot-password", {"email": "missing@example.com"}
    )
    generic_existing = client.post_json(
        "/api/v1/auth/forgot-password", {"email": "renamed@example.com"}
    )
    assert generic_missing.json == generic_existing.json
    assert "token" not in generic_existing.text.lower()
    assert len(memory_email.messages) == 1
    expired_token = _token_from_message(memory_email.messages[-1])
    assert expired_token not in generic_existing.text

    session = app.registry.palms_database.session_factory()
    try:
        reset = session.scalar(
            select(PasswordResetToken).order_by(PasswordResetToken.created_at.desc())
        )
        assert reset is not None
        reset.expires_at = utcnow() - timedelta(seconds=1)
        session.commit()
    finally:
        session.close()
    assert client.post_json(
        "/api/v1/auth/reset-password",
        {"token": expired_token, "password": "ResetPassword789"},
        status=400,
    ).json["error"]["code"] == "invalid_reset_token"

    client.post_json("/api/v1/auth/forgot-password", {"email": "renamed@example.com"})
    fresh_token = _token_from_message(memory_email.messages[-1])
    assert client.post_json(
        "/api/v1/auth/reset-password",
        {"token": fresh_token, "password": "ResetPassword789"},
    ).json["data"] == {"password_reset": True}
    assert client.post_json(
        "/api/v1/auth/reset-password",
        {"token": fresh_token, "password": "ResetPassword789"},
        status=400,
    ).json["error"]["code"] == "invalid_reset_token"

    login(client, email="renamed@example.com", password="ResetPassword789")
    assert client.post_json(
        "/api/v1/auth/change-password",
        {"current_password": "ResetPassword789", "new_password": "FinalPassword987"},
    ).json["data"]["password_changed"] is True
    login(client, email="renamed@example.com", password="FinalPassword987")

    session = app.registry.palms_database.session_factory()
    try:
        active_session = session.scalar(
            select(UserSession)
            .where(UserSession.user_id == UUID(account["id"]))
            .order_by(UserSession.created_at.desc())
        )
        assert active_session is not None
        active_session.expires_at = utcnow() - timedelta(seconds=1)
        session.commit()
    finally:
        session.close()
    assert client.get("/api/v1/auth/me", status=401).json["error"]["code"] == "unauthorized"


def test_roles_overrides_users_invitations_and_audit_endpoints(
    app, client: TestApp, make_user, login, memory_email
) -> None:
    super_admin = make_user(email="super@example.com")
    second_super = make_user(email="second-super@example.com")
    admin = make_user(role_name="Admin", email="admin-role@example.com")
    editor = make_user(role_name="Editor", email="editor-role@example.com")
    viewer = make_user(role_name="Viewer", email="viewer-role@example.com")
    login(client, email=super_admin["email"])

    listed = client.get("/api/v1/admin/users?query=role&page_size=2&sort=email&order=asc")
    assert listed.json["data"]["pagination"]["total"] >= 3
    assert client.get(f"/api/v1/admin/users/{editor['id']}").json["data"]["email"] == editor["email"]
    assert client.get("/api/v1/admin/users/not-a-uuid", status=422).json["error"]["code"] == "validation_error"
    assert client.get(f"/api/v1/admin/users/{uuid4()}", status=404).json["error"]["code"] == "not_found"
    assert client.patch_json(
        f"/api/v1/admin/users/{super_admin['id']}",
        {"permission_overrides": {"palms.read": False}},
        status=409,
    ).json["error"]["code"] == "conflict"
    assert client.patch_json(
        f"/api/v1/admin/users/{editor['id']}",
        {"permission_overrides": {"unknown.permission": True}},
        status=422,
    ).json["error"]["code"] == "validation_error"
    patched = client.patch_json(
        f"/api/v1/admin/users/{editor['id']}",
        {
            "full_name": "Override Editor",
            "permission_overrides": {"donors.delete": True, "palms.read": False},
        },
    )
    assert patched.json["data"]["full_name"] == "Override Editor"
    assert client.patch_json(
        f"/api/v1/admin/users/{editor['id']}",
        {"role_id": str(uuid4())},
        status=404,
    ).json["error"]["code"] == "not_found"

    invitation = client.post_json(
        "/api/v1/admin/users/invite",
        {
            "email": "invitee@example.com",
            "full_name": "Invited Editor",
            "role_id": _role_id(app, "Editor"),
        },
    )
    assert invitation.status_code == 201
    assert "token" not in invitation.text.lower()
    assert "hash" not in invitation.text.lower()
    assert _token_from_message(memory_email.messages[-1]) not in invitation.text
    assert client.post_json(
        "/api/v1/admin/users/invite",
        {
            "email": "invitee@example.com",
            "full_name": "Invited Editor",
            "role_id": _role_id(app, "Editor"),
        },
        status=409,
    ).json["error"]["code"] == "conflict"
    assert client.post_json(
        "/api/v1/admin/users/invite",
        {"email": "missing-role@example.com", "full_name": "Missing", "role_id": str(uuid4())},
        status=404,
    ).json["error"]["code"] == "not_found"

    second_super_client = TestApp(app)
    login(second_super_client, email=second_super["email"])
    disabled = client.post(f"/api/v1/admin/users/{second_super['id']}/disable")
    assert disabled.json["data"]["is_active"] is False
    assert second_super_client.get("/api/v1/auth/me", status=401).json["error"]["code"] == "unauthorized"
    assert client.post(
        f"/api/v1/admin/users/{second_super['id']}/reset-password", status=409
    ).json["error"]["code"] == "conflict"
    assert client.post(
        f"/api/v1/admin/users/{second_super['id']}/enable"
    ).json["data"]["is_active"] is True
    reset = client.post(f"/api/v1/admin/users/{second_super['id']}/reset-password")
    assert reset.json["data"] == {"password_reset_requested": True}
    assert "token" not in reset.text.lower()
    audit = client.get(f"/api/v1/admin/users/{super_admin['id']}/audit-logs?page_size=100")
    assert any(item["action"] == "users.invited" for item in audit.json["data"]["items"])

    admin_client = TestApp(app)
    login(admin_client, email=admin["email"])
    assert admin_client.get("/api/v1/admin/users", status=403).json["error"]["code"] == "forbidden"

    editor_client = TestApp(app)
    login(editor_client, email=editor["email"])
    editor_donor = editor_client.post_json(
        "/api/v1/admin/donors", {"full_name": "Editor Created"}
    ).json["data"]
    assert editor_client.delete(
        f"/api/v1/admin/donors/{editor_donor['id']}"
    ).json["data"]["deleted"] is True
    assert editor_client.get("/api/v1/admin/palms", status=403).json["error"]["code"] == "forbidden"
    assert editor_client.post_json(
        "/api/v1/admin/report-schedules",
        {
            "name": "Forbidden",
            "report_type": "palms",
            "frequency": "daily",
            "run_time": "09:00",
            "timezone": "UTC",
            "format": "csv",
            "fields": ["code"],
            "recipients": ["reports@example.com"],
        },
        status=403,
    ).json["error"]["code"] == "forbidden"

    viewer_client = TestApp(app)
    login(viewer_client, email=viewer["email"])
    assert viewer_client.get("/api/v1/admin/dashboard/overview").status_code == 200
    assert viewer_client.post_json(
        "/api/v1/admin/donors", {"full_name": "Forbidden Viewer"}, status=403
    ).json["error"]["code"] == "forbidden"


def test_donor_section_palm_lists_soft_deletes_and_bulk_operations(
    client: TestApp, make_user, login, domain_builder
) -> None:
    make_user()
    login(client)
    data = domain_builder(client, suffix="101")
    extra_donor = client.post_json(
        "/api/v1/admin/donors",
        {"full_name": "Zara Donor", "phone": "+15550101010", "email": "zara@example.com"},
    ).json["data"]
    extra_section = client.post_json(
        "/api/v1/admin/sections", {"name": "Zebra Grove", "location_name": "West"}
    ).json["data"]
    child = _create_palm(
        client,
        donor_id=data["donor"]["id"],
        section_id=data["section"]["id"],
        code="PALM-102",
    )

    donors = client.get("/api/v1/admin/donors?query=Donor&sort=full_name&order=asc&page_size=1")
    assert donors.json["data"]["pagination"] == {
        "page": 1,
        "page_size": 1,
        "total": 2,
        "total_pages": 2,
    }
    assert client.get("/api/v1/admin/donors?sort=phone", status=422).json["error"]["code"] == "validation_error"
    assert client.get("/api/v1/admin/donors?page=0", status=422).json["error"]["code"] == "validation_error"
    assert client.get(
        f"/api/v1/admin/donors/{data['donor']['id']}"
    ).json["data"]["full_name"] == data["donor"]["full_name"]
    patched_donor = client.patch_json(
        f"/api/v1/admin/donors/{data['donor']['id']}",
        {"address": "1 Palm Way", "notes": "Long-term donor"},
    )
    assert patched_donor.json["data"]["address"] == "1 Palm Way"
    assert client.get(f"/api/v1/admin/donors/{uuid4()}", status=404).json["error"]["code"] == "not_found"
    client.delete(f"/api/v1/admin/donors/{extra_donor['id']}")
    assert client.get(f"/api/v1/admin/donors/{extra_donor['id']}", status=404).json["error"]["code"] == "not_found"

    sections = client.get("/api/v1/admin/sections?query=Section&sort=name&order=asc")
    assert sections.json["data"]["pagination"]["total"] == 2
    assert client.patch_json(
        f"/api/v1/admin/sections/{data['section']['id']}",
        {"description": "Updated plot", "gps_latitude": "12.1234567"},
    ).json["data"]["description"] == "Updated plot"
    assert client.get(
        f"/api/v1/admin/sections/{data['section']['id']}"
    ).json["data"]["name"] == data["section"]["name"]
    assert client.delete(f"/api/v1/admin/sections/{extra_section['id']}").json["data"]["deleted"] is True
    assert client.delete(
        f"/api/v1/admin/sections/{data['section']['id']}?reassign_to_section_id={data['section']['id']}",
        status=422,
    ).json["error"]["code"] == "validation_error"
    assert client.delete(f"/api/v1/admin/sections/{data['section']['id']}", status=409).json["error"]["code"] == "conflict"

    palm = data["palm"]
    assert client.get(
        f"/api/v1/admin/donors/{data['donor']['id']}/palms?sort=code&order=asc"
    ).json["data"]["pagination"]["total"] == 2
    listed = client.get(
        f"/api/v1/admin/palms?query=PALM-10&donor_id={data['donor']['id']}"
        f"&section_id={data['section']['id']}&status=active&health_status=healthy&sort=code&order=asc"
    )
    assert [item["code"] for item in listed.json["data"]["items"]] == ["PALM-101", "PALM-102"]
    assert client.get("/api/v1/admin/palms?donor_id=not-a-uuid", status=422).json["error"]["code"] == "validation_error"
    updated_palm = client.patch_json(
        f"/api/v1/admin/palms/{palm['id']}",
        {"code": "PALM-101-RENAMED", "status": "inactive"},
    ).json["data"]
    assert updated_palm["status"] == "inactive"
    assert client.get("/api/v1/admin/palms?status=inactive").json["data"]["pagination"]["total"] == 1
    assert client.get(f"/api/v1/admin/palms/{uuid4()}", status=404).json["error"]["code"] == "not_found"

    reassigned = client.post_json(
        "/api/v1/admin/palms/bulk-update-section",
        {"palm_ids": [palm["id"], child["id"]], "section_id": data["alternate_section"]["id"]},
    )
    assert reassigned.json["data"]["updated_count"] == 2
    assert client.delete(
        f"/api/v1/admin/sections/{data['section']['id']}?reassign_to_section_id={data['alternate_section']['id']}"
    ).json["data"]["reassigned_palm_count"] == 0
    assert client.post_json(
        "/api/v1/admin/palms/bulk-delete",
        {"palm_ids": [palm["id"], palm["id"]]},
        status=422,
    ).json["error"]["code"] == "validation_error"
    assert client.post_json(
        "/api/v1/admin/palms/bulk-delete", {"palm_ids": [str(uuid4())]}, status=404
    ).json["error"]["code"] == "not_found"
    assert client.post_json(
        "/api/v1/admin/palms/bulk-delete", {"palm_ids": [palm["id"], child["id"]]}
    ).json["data"]["deleted_count"] == 2
    assert client.get(f"/api/v1/admin/palms/{palm['id']}", status=404).json["error"]["code"] == "not_found"

    standalone = _create_palm(
        client,
        donor_id=data["donor"]["id"],
        section_id=data["alternate_section"]["id"],
        code="PALM-STANDALONE",
    )
    assert client.delete(f"/api/v1/admin/palms/{standalone['id']}").json["data"]["deleted"] is True


def test_all_palm_history_and_relationship_endpoints(
    client: TestApp, make_user, login, domain_builder
) -> None:
    make_user()
    login(client)
    data = domain_builder(client, suffix="201")
    palm = data["palm"]
    child = _create_palm(
        client,
        donor_id=data["donor"]["id"],
        section_id=data["section"]["id"],
        code="PALM-202",
    )
    harvest = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/harvests",
        {"harvest_date": "2025-02-01", "amount": "2.50", "unit": "kg", "revenue": "12.50"},
    ).json["data"]
    assert client.patch_json(
        f"/api/v1/admin/palms/{palm['id']}/harvests/{harvest['id']}", {"amount": "3.25"}
    ).json["data"]["amount"] == "3.25"
    assert client.patch_json(
        f"/api/v1/admin/palms/{child['id']}/harvests/{harvest['id']}", {"amount": "4.00"}, status=404
    ).json["error"]["code"] == "not_found"

    disease = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/diseases",
        {"disease_name": "Leaf Spot", "detected_at": "2025-02-02", "notes": "Observe"},
    ).json["data"]
    assert client.patch_json(
        f"/api/v1/admin/palms/{palm['id']}/diseases/{disease['id']}", {"status": "resolved"}
    ).json["data"]["status"] == "resolved"
    treatment = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/diseases/{disease['id']}/treatments",
        {"treatment_name": "Organic Spray", "treatment_date": "2025-02-03"},
    ).json["data"]
    assert client.patch_json(
        f"/api/v1/admin/palms/{palm['id']}/diseases/{disease['id']}/treatments/{treatment['id']}",
        {"notes": "Completed"},
    ).json["data"]["notes"] == "Completed"
    note = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/notes", {"body": "Inspect next week"}
    ).json["data"]
    assert client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/relationships", {"child_palm_id": palm["id"]}, status=422
    ).json["error"]["code"] == "validation_error"
    relationship = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/relationships",
        {"child_palm_id": child["id"], "relationship_type": "parent_child"},
    ).json["data"]
    assert client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/relationships", {"child_palm_id": child["id"]}, status=409
    ).json["error"]["code"] == "conflict"

    detail = client.get(f"/api/v1/admin/palms/{palm['id']}").json["data"]
    assert detail["harvests"][0]["id"] == harvest["id"]
    assert detail["diseases"][0]["treatments"][0]["id"] == treatment["id"]
    assert detail["notes"][0]["id"] == note["id"]
    assert detail["children"][0]["id"] == relationship["id"]

    assert client.delete(
        f"/api/v1/admin/palms/{palm['id']}/harvests/{harvest['id']}"
    ).json["data"]["deleted"] is True
    assert client.delete(
        f"/api/v1/admin/palms/{palm['id']}/diseases/{disease['id']}/treatments/{treatment['id']}"
    ).json["data"]["deleted"] is True
    replacement_treatment = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/diseases/{disease['id']}/treatments",
        {"treatment_name": "Follow Up", "treatment_date": "2025-02-04"},
    ).json["data"]
    assert replacement_treatment["id"]
    assert client.delete(
        f"/api/v1/admin/palms/{palm['id']}/notes/{note['id']}"
    ).json["data"]["deleted"] is True
    assert client.delete(
        f"/api/v1/admin/palms/{palm['id']}/relationships/{relationship['id']}"
    ).json["data"]["deleted"] is True
    assert client.delete(
        f"/api/v1/admin/palms/{palm['id']}/diseases/{disease['id']}"
    ).json["data"]["deleted"] is True
    assert client.delete(
        f"/api/v1/admin/palms/{palm['id']}/relationships/{relationship['id']}", status=404
    ).json["error"]["code"] == "not_found"


def test_media_public_search_and_dashboard_contracts(
    app, client: TestApp, make_user, login, domain_builder, monkeypatch
) -> None:
    make_user()
    login(client)
    data = domain_builder(client, suffix="301")
    palm = data["palm"]
    image_path = f"/api/v1/admin/palms/{palm['id']}/images"
    assert client.post_json(image_path, {}, status=415).json["error"]["code"] == "unsupported_media_type"
    assert client.post(
        image_path,
        upload_files=[("file", "not-an-image.txt", b"not an image")],
        status=422,
    ).json["error"]["code"] == "invalid_image"
    app.registry.palms_settings.image_max_upload_mb = 1
    assert client.post(
        image_path,
        upload_files=[("file", "oversized.png", b"x" * (1024 * 1024 + 1))],
        status=422,
    ).json["error"]["code"] == "validation_error"
    uploaded = client.post(
        image_path, upload_files=[("file", "palm.png", _image_bytes())]
    ).json["data"]
    storage = app.registry.palms_storage
    assert len(storage.objects) == 4
    assert storage.objects[next(key for key in storage.objects if key.endswith(".webp"))][1] == "image/webp"
    assert uploaded["metadata"]["metadata_stripped"] is True

    section_path = f"/api/v1/admin/sections/{data['section']['id']}/image"
    assert client.post(
        section_path, upload_files=[("file", "section.png", _image_bytes())]
    ).json["data"]["image_url"].endswith("full.jpg")
    assert client.post(
        "/api/v1/admin/profile/avatar", upload_files=[("file", "avatar.png", _image_bytes())]
    ).json["data"]["avatar_url"].endswith("medium.jpg")

    original_delete = storage.delete_file

    def fail_one_variant(key: str) -> None:
        if key.endswith("medium.jpg"):
            raise RuntimeError("simulated storage outage")
        original_delete(key)

    monkeypatch.setattr(storage, "delete_file", fail_one_variant)
    failed_delete = client.delete(f"{image_path}/{uploaded['id']}", status=503)
    assert failed_delete.json["error"]["code"] == "storage_error"
    session = app.registry.palms_database.session_factory()
    try:
        assert session.get(PalmImage, UUID(uploaded["id"])) is not None
    finally:
        session.close()

    assert client.get("/api/v1/public/search?query=Donor%20301").json["data"]["items"][0]["palm_code"] == "PALM-301"
    assert client.get("/api/v1/public/search?query=15550100301").json["data"]["items"][0]["palm_code"] == "PALM-301"
    assert client.get("/api/v1/public/search?query=palm-301&page_size=1").json["data"]["pagination"]["total"] == 1
    assert client.get("/api/v1/public/search?query=", status=422).json["error"]["code"] == "validation_error"
    assert client.get("/api/v1/public/donors/suggest?query=donor&limit=bad", status=422).json["error"]["code"] == "validation_error"
    suggestions = client.get("/api/v1/public/donors/suggest?query=donor&limit=500").json["data"]["items"]
    assert len(suggestions) <= 20 and set(suggestions[0]) == {"id", "full_name"}
    profile = client.get("/api/v1/public/palms/palm-301").json["data"]
    assert profile["current_age"] is not None
    assert profile["donor"] == {"full_name": "Donor 301"}
    assert "phone" not in str(profile) and "email" not in str(profile)
    assert client.get("/api/v1/public/palms/missing", status=404).json["error"]["code"] == "not_found"

    client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/harvests",
        {"harvest_date": "2025-03-01", "amount": "5.00", "unit": "kg", "revenue": "22.50"},
    )
    overview = client.get("/api/v1/admin/dashboard/overview").json["data"]
    assert overview["totals"]["palms"] == 1
    assert overview["totals"]["revenue"] == "22.50"
    assert client.get("/api/v1/admin/dashboard/activity?page_size=1").json["data"]["pagination"]["total"] >= 1
    anonymous = TestApp(app)
    assert anonymous.get("/api/v1/admin/dashboard/activity", status=401).json["error"]["code"] == "unauthorized"


def test_reports_templates_schedules_downloads_and_validation(
    app, client: TestApp, make_user, login, domain_builder, memory_email
) -> None:
    make_user()
    login(client)
    domain_builder(client, suffix="401")

    types = client.get("/api/v1/admin/reports/types").json["data"]["items"]
    assert {item["code"] for item in types} == {"palms", "donors", "sections"}
    preview = client.post_json(
        "/api/v1/admin/reports/preview",
        {"report_type": "palms", "fields": ["code", "donor_name"], "filters": {"status": "active"}},
    ).json["data"]
    assert preview["items"][0]["code"] == "PALM-401"
    assert client.post_json(
        "/api/v1/admin/reports/preview",
        {"report_type": "palms", "fields": ["unknown"]},
        status=422,
    ).json["error"]["code"] == "validation_error"

    csv_run = client.post_json(
        "/api/v1/admin/reports/generate",
        {"report_type": "palms", "fields": ["code", "donor_name"], "format": "csv"},
    ).json["data"]
    assert csv_run["status"] == "succeeded"
    assert client.get(
        f"/api/v1/admin/report-runs/{csv_run['id']}/download"
    ).json["data"]["files"][0]["download_url"].startswith("memory://")
    pdf_run = client.post_json(
        "/api/v1/admin/reports/generate",
        {"report_type": "sections", "fields": ["name"], "format": "pdf"},
    ).json["data"]
    session = app.registry.palms_database.session_factory()
    try:
        persisted_pdf = session.get(ReportRun, UUID(pdf_run["id"]))
        assert persisted_pdf is not None and persisted_pdf.files
        assert app.registry.palms_storage.get_bytes(persisted_pdf.files[0].storage_key).startswith(b"%PDF")
        session.add(
            ReportRun(
                report_type="palms",
                format="csv",
                fields_json=["code"],
                filters_json={},
                status="queued",
            )
        )
        session.commit()
        queued = session.scalar(select(ReportRun).where(ReportRun.status == "queued"))
        assert queued is not None
        queued_id = str(queued.id)
    finally:
        session.close()
    assert client.get(f"/api/v1/admin/report-runs/{queued_id}/download", status=409).json["error"]["code"] == "report_not_ready"
    assert client.get(f"/api/v1/admin/report-runs/{uuid4()}/download", status=404).json["error"]["code"] == "not_found"

    assert client.get("/api/v1/admin/reports/templates").json["data"]["items"] == []
    template = client.post_json(
        "/api/v1/admin/reports/templates",
        {"name": "Palm Snapshot", "report_type": "palms", "fields": ["code", "section_name"]},
    ).json["data"]
    assert client.get("/api/v1/admin/reports/templates").json["data"]["items"][0]["id"] == template["id"]
    assert client.post_json(
        "/api/v1/admin/report-schedules",
        {
            "name": "Missing Fields",
            "report_type": "palms",
            "frequency": "daily",
            "run_time": "09:00",
            "timezone": "UTC",
            "format": "csv",
            "recipients": ["reports@example.com"],
        },
        status=422,
    ).json["error"]["code"] == "validation_error"
    schedule = client.post_json(
        "/api/v1/admin/report-schedules",
        {
            "name": "Daily Palm Snapshot",
            "report_type": "palms",
            "template_id": template["id"],
            "frequency": "daily",
            "run_time": "09:00",
            "timezone": "UTC",
            "format": "csv",
            "recipients": ["reports@example.com"],
            "attach_file": False,
        },
    ).json["data"]
    assert schedule["next_run_at"]
    assert client.get("/api/v1/admin/report-schedules").json["data"]["items"][0]["id"] == schedule["id"]
    assert client.get(
        f"/api/v1/admin/report-schedules/{schedule['id']}"
    ).json["data"]["recipients"] == ["reports@example.com"]
    assert client.patch_json(
        f"/api/v1/admin/report-schedules/{schedule['id']}",
        {"name": "Renamed Snapshot", "recipients": ["new-reports@example.com"], "enabled": False},
    ).json["data"]["next_run_at"] is None
    assert client.post(
        f"/api/v1/admin/report-schedules/{schedule['id']}/resume"
    ).json["data"]["enabled"] is True
    assert client.post(
        f"/api/v1/admin/report-schedules/{schedule['id']}/pause"
    ).json["data"]["enabled"] is False
    assert client.get(
        f"/api/v1/admin/report-schedules/{schedule['id']}/runs"
    ).json["data"]["pagination"]["total"] == 0
    assert client.delete(
        f"/api/v1/admin/report-schedules/{schedule['id']}"
    ).json["data"]["deleted"] is True
    assert client.get(
        f"/api/v1/admin/report-schedules/{schedule['id']}", status=404
    ).json["error"]["code"] == "not_found"
    assert memory_email.messages == []


def test_report_executors_scheduler_worker_and_storage_fakes(tmp_path, monkeypatch) -> None:
    database_path = (tmp_path / "scheduler.db").as_posix()
    settings = Settings(
        app_environment="testing",
        database_url=f"sqlite+pysqlite:///{database_path}",
        email_enabled=False,
    )
    database = Database(settings)
    Base.metadata.create_all(database.engine)
    session = database.session_factory()
    try:
        seed_system_rbac(session)
        due = ReportSchedule(
            name="Due Report",
            report_type="sections",
            frequency="daily",
            run_time="09:00",
            timezone="UTC",
            format="csv",
            fields_json=["name"],
            filters_json={},
            next_run_at=datetime(2025, 1, 1, 9, 0),
        )
        due.recipients = [ReportScheduleRecipient(email="scheduled@example.com")]
        incomplete = ReportSchedule(
            name="Broken Template Schedule",
            report_type="sections",
            frequency="daily",
            run_time="09:00",
            timezone="UTC",
            format="csv",
            fields_json=None,
            filters_json={},
            next_run_at=datetime(2025, 1, 1, 9, 0),
        )
        session.add_all([due, incomplete])
        session.commit()
        due_id, incomplete_id = str(due.id), str(incomplete.id)
    finally:
        session.close()
        database.dispose()

    assert isinstance(report_executor(settings), SynchronousReportExecutor)
    assert run_due_schedules(settings, now=datetime(2025, 1, 2)) == 1
    database = Database(settings)
    session = database.session_factory()
    try:
        run = session.scalar(select(ReportRun).where(ReportRun.schedule_id == UUID(due_id)))
        assert run is not None and run.status == "succeeded" and run.files
        incomplete = session.get(ReportSchedule, UUID(incomplete_id))
        assert incomplete is not None and incomplete.enabled is False
        failing_schedule = ReportSchedule(
            name="Failed Delivery",
            report_type="sections",
            frequency="daily",
            run_time="10:00",
            timezone="UTC",
            format="csv",
            fields_json=["name"],
            filters_json={},
        )
        failing_schedule.recipients = [ReportScheduleRecipient(email="failure@example.com")]
        failed_run = ReportRun(
            schedule=failing_schedule,
            report_type="sections",
            format="csv",
            fields_json=["name"],
            filters_json={},
            status="queued",
        )
        session.add(failed_run)
        session.flush()
        failed_run_id = str(failed_run.id)
        session.commit()
    finally:
        session.close()
        database.dispose()

    class FailingStorage(MemoryStorageClient):
        def upload_bytes(self, key: str, content: bytes, *, content_type: str) -> None:
            raise RuntimeError("upload failed")

    database = Database(settings)
    session = database.session_factory()
    transport = MemoryEmailTransport()
    try:
        settings.email_enabled = True
        failed_run = session.get(ReportRun, UUID(failed_run_id))
        assert failed_run is not None
        execute_report_run(
            session,
            run=failed_run,
            storage=FailingStorage(),
            email_service=EmailService(settings, transport),
        )
        session.commit()
        assert failed_run.status == "failed"
        assert "upload failed" in (failed_run.error_message or "")
        assert transport.messages and "failed" in _message_text(transport.messages[-1]).lower()
        successful_run = ReportRun(
            schedule_id=failed_run.schedule_id,
            report_type="sections",
            format="csv",
            fields_json=["name"],
            filters_json={},
            status="queued",
        )
        session.add(successful_run)
        session.flush()
        execute_report_run(
            session,
            run=successful_run,
            storage=MemoryStorageClient(),
            email_service=EmailService(settings, transport),
        )
        session.commit()
        assert successful_run.status == "succeeded"
        assert len(transport.messages) == 2
        assert next(transport.messages[-1].iter_attachments()).get_filename().endswith(".csv")
        session.add(
            ReportRun(
                report_type="sections",
                format="csv",
                fields_json=["name"],
                filters_json={},
                status="queued",
            )
        )
        session.commit()
        queued = session.scalar(select(ReportRun).where(ReportRun.status == "queued"))
        assert queued is not None
        queued_id = str(queued.id)
    finally:
        session.close()
        database.dispose()

    monkeypatch.setattr("palms_api.worker.build_storage_client", lambda _: FailingStorage())
    generate_report_job(settings.model_dump(mode="json"), queued_id)
    database = Database(settings)
    session = database.session_factory()
    try:
        worker_run = session.get(ReportRun, UUID(queued_id))
        assert worker_run is not None and worker_run.status == "failed"
    finally:
        session.close()
        database.dispose()

    queued_jobs: list[tuple[str, tuple]] = []

    class FakeRedis:
        @staticmethod
        def from_url(url: str):
            return f"connection:{url}"

    class FakeQueue:
        def __init__(self, name: str, connection: str) -> None:
            assert connection == "connection:redis://fake"
            self.name = name

        def enqueue(self, path: str, *args) -> None:
            queued_jobs.append((path, args))

    monkeypatch.setitem(sys.modules, "redis", SimpleNamespace(Redis=FakeRedis))
    monkeypatch.setitem(sys.modules, "rq", SimpleNamespace(Queue=FakeQueue))
    queued_run = SimpleNamespace(id=uuid4())
    executor = RQReportExecutor("redis://fake", "test-reports", {"app_environment": "testing"})
    assert executor.submit(None, queued_run) is queued_run
    assert queued_jobs[0][0] == "palms_api.worker.generate_report_job"

    storage = MemoryStorageClient(bucket_name="fake assets")
    storage.upload_bytes("reports/example.csv", b"code\nPALM-1\n", content_type="text/csv")
    assert storage.get_bytes("reports/example.csv").startswith(b"code")
    assert storage.get_signed_url("reports/example.csv", expires_in=60).startswith("memory://fake%20assets/")
    with pytest.raises(ValueError):
        safe_storage_key("../outside")
    with pytest.raises(ValueError):
        storage.get_signed_url("reports/example.csv", expires_in=0)

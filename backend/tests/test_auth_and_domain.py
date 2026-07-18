"""Integration coverage for authentication, RBAC, and core domain CRUD."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select
from webtest import TestApp

from palms_api.models import AuditLog, Role, User
from palms_api.security import hash_password

PASSWORD = "StrongPassword123"


def create_user(app, *, role_name: str = "Super Admin", email: str = "admin@example.com") -> User:
    """Create a deterministic fixture user from seeded RBAC data."""
    session = app.registry.palms_database.session_factory()
    try:
        role = session.scalar(select(Role).where(Role.name == role_name))
        assert role is not None
        user = User(
            email=email,
            full_name=f"{role_name} Fixture",
            password_hash=hash_password(PASSWORD),
            role_id=role.id,
        )
        session.add(user)
        session.commit()
        return user
    finally:
        session.close()


def login(client: TestApp, *, email: str = "admin@example.com"):
    """Log in through the real cookie session endpoint."""
    return client.post_json(
        "/api/v1/auth/login",
        {"email": email, "password": PASSWORD},
    )


def test_secure_session_authentication_and_validation(app, client: TestApp) -> None:
    create_user(app)

    unauthenticated = client.get("/api/v1/auth/me", status=401)
    assert unauthenticated.json["error"]["code"] == "unauthorized"

    invalid = client.post_json(
        "/api/v1/auth/login",
        {"email": "admin@example.com", "password": "not-it"},
        status=401,
    )
    assert invalid.json["error"]["code"] == "invalid_credentials"

    response = login(client)
    assert response.json["data"]["user"]["email"] == "admin@example.com"
    assert "password_hash" not in response.text
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert "SameSite=Lax" in response.headers["Set-Cookie"]

    me = client.get("/api/v1/auth/me")
    assert "palms.delete" in me.json["data"]["permissions"]

    bad_change = client.post_json(
        "/api/v1/auth/change-password",
        {"current_password": PASSWORD, "new_password": "short"},
        status=422,
    )
    assert bad_change.json["error"]["code"] == "validation_error"

    logout = client.post("/api/v1/auth/logout")
    assert logout.json == {"data": {"logged_out": True}}
    client.get("/api/v1/auth/me", status=401)


def test_viewer_is_forbidden_from_mutating_domain_data(app, client: TestApp) -> None:
    create_user(app, role_name="Viewer", email="viewer@example.com")
    login(client, email="viewer@example.com")

    assert client.get("/api/v1/admin/donors").json["data"]["items"] == []
    forbidden = client.post_json(
        "/api/v1/admin/donors",
        {"full_name": "Blocked Donor"},
        status=403,
    )
    assert forbidden.json["error"]["code"] == "forbidden"

    also_forbidden = client.get("/api/v1/admin/users", status=403)
    assert also_forbidden.json["error"]["code"] == "forbidden"


def test_super_admin_manages_users_without_exposing_invitation_secret(app, client: TestApp) -> None:
    create_user(app)
    login(client)
    session = app.registry.palms_database.session_factory()
    try:
        editor = session.scalar(select(Role).where(Role.name == "Editor"))
        assert editor is not None
        role_id = str(editor.id)
    finally:
        session.close()

    invite = client.post_json(
        "/api/v1/admin/users/invite",
        {
            "email": "new-editor@example.com",
            "full_name": "New Editor",
            "role_id": role_id,
        },
    )
    assert invite.status_code == 201
    assert invite.json["data"]["email"] == "new-editor@example.com"
    assert "token" not in invite.text
    assert "hash" not in invite.text

    duplicate = client.post_json(
        "/api/v1/admin/users/invite",
        {
            "email": "new-editor@example.com",
            "full_name": "New Editor",
            "role_id": role_id,
        },
        status=409,
    )
    assert duplicate.json["error"]["code"] == "conflict"


def test_core_crud_histories_reassignment_and_bulk_delete(app, client: TestApp) -> None:
    create_user(app)
    login(client)

    invalid_palm = client.post_json(
        "/api/v1/admin/palms",
        {
            "code": "BAD-001",
            "donor_id": "b2ec3073-60ea-4cc2-a7b1-6fd41b55ca79",
            "section_id": "b2ec3073-60ea-4cc2-a7b1-6fd41b55ca79",
        },
        status=404,
    )
    assert invalid_palm.json["error"]["code"] == "not_found"

    donor = client.post_json(
        "/api/v1/admin/donors",
        {
            "full_name": "Aisha Donor",
            "phone": "+155500000",
            "email": "aisha@example.com",
        },
    ).json["data"]
    section = client.post_json(
        "/api/v1/admin/sections",
        {"name": "North Grove", "location_name": "North"},
    ).json["data"]
    replacement_section = client.post_json(
        "/api/v1/admin/sections",
        {"name": "South Grove", "location_name": "South"},
    ).json["data"]

    palm = client.post_json(
        "/api/v1/admin/palms",
        {
            "code": "PALM-001",
            "donor_id": donor["id"],
            "section_id": section["id"],
            "plantation_date": "2020-01-01",
            "status": "active",
        },
    ).json["data"]
    child = client.post_json(
        "/api/v1/admin/palms",
        {
            "code": "PALM-002",
            "donor_id": donor["id"],
            "section_id": section["id"],
        },
    ).json["data"]

    palms = client.get("/api/v1/admin/palms?query=Aisha&sort=code&order=asc").json["data"]
    assert [item["code"] for item in palms["items"]] == ["PALM-001", "PALM-002"]
    assert palms["pagination"]["total"] == 2
    assert client.get(f"/api/v1/admin/donors/{donor['id']}/palms").json["data"]["pagination"]["total"] == 2

    harvest = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/harvests",
        {"harvest_date": "2025-01-01", "amount": "12.50", "unit": "kg", "revenue": "100.00"},
    ).json["data"]
    client.patch_json(
        f"/api/v1/admin/palms/{palm['id']}/harvests/{harvest['id']}",
        {"amount": "14.00"},
    )
    disease = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/diseases",
        {"disease_name": "Leaf spot", "detected_at": "2025-01-02"},
    ).json["data"]
    treatment = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/diseases/{disease['id']}/treatments",
        {"treatment_name": "Organic spray", "treatment_date": "2025-01-03"},
    ).json["data"]
    assert treatment["treatment_name"] == "Organic spray"
    note = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/notes",
        {"body": "Inspect again next week."},
    ).json["data"]
    relationship = client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/relationships",
        {"child_palm_id": child["id"]},
    ).json["data"]

    detail = client.get(f"/api/v1/admin/palms/{palm['id']}").json["data"]
    assert detail["harvests"][0]["amount"] == "14.00"
    assert detail["diseases"][0]["treatments"][0]["id"] == treatment["id"]
    assert detail["notes"][0]["id"] == note["id"]
    assert detail["children"][0]["id"] == relationship["id"]

    blocked_delete = client.delete(f"/api/v1/admin/sections/{section['id']}", status=409)
    assert blocked_delete.json["error"]["code"] == "conflict"
    reassigned = client.delete(
        f"/api/v1/admin/sections/{section['id']}?reassign_to_section_id={replacement_section['id']}"
    ).json["data"]
    assert reassigned["reassigned_palm_count"] == 2
    patched_palm = client.get(f"/api/v1/admin/palms/{palm['id']}").json["data"]
    assert patched_palm["section_id"] == replacement_section["id"]

    deleted = client.post_json(
        "/api/v1/admin/palms/bulk-delete",
        {"palm_ids": [palm["id"], child["id"]]},
    )
    assert deleted.json["data"]["deleted_count"] == 2
    client.get(f"/api/v1/admin/palms/{palm['id']}", status=404)

    session = app.registry.palms_database.session_factory()
    try:
        audits = session.scalars(select(AuditLog)).all()
        assert audits
        assert all("password" not in str(entry.new_values_json).lower() for entry in audits)
    finally:
        session.close()

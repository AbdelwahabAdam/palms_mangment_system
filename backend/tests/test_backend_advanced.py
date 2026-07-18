"""Focused integration coverage for advanced media, public, reports, and email flows."""

from __future__ import annotations

from io import BytesIO

from PIL import Image
from sqlalchemy import select
from webtest import TestApp

from palms_api.config import Settings
from palms_api.database import Database
from palms_api.email_service import MemoryEmailTransport
from palms_api.models import Base, EmailLog, ReportRun, Role, User
from palms_api.security import hash_password
from palms_api.worker import generate_report_job


PASSWORD = "StrongPassword123"


def create_admin(app) -> None:
    session = app.registry.palms_database.session_factory()
    try:
        role = session.scalar(select(Role).where(Role.name == "Super Admin"))
        assert role is not None
        session.add(
            User(
                email="advanced-admin@example.com",
                full_name="Advanced Admin",
                password_hash=hash_password(PASSWORD),
                role_id=role.id,
            )
        )
        session.commit()
    finally:
        session.close()


def login(client: TestApp) -> None:
    client.post_json(
        "/api/v1/auth/login",
        {"email": "advanced-admin@example.com", "password": PASSWORD},
    )


def setup_palm(client: TestApp) -> tuple[dict, dict]:
    donor = client.post_json(
        "/api/v1/admin/donors",
        {"full_name": "Amina Al Palm", "phone": "+1 (555) 909-0100", "email": "private@example.com"},
    ).json["data"]
    section = client.post_json("/api/v1/admin/sections", {"name": "Image Grove"}).json["data"]
    palm = client.post_json(
        "/api/v1/admin/palms",
        {
            "code": "PUBLIC-IMAGE-001",
            "donor_id": donor["id"],
            "section_id": section["id"],
            "plantation_date": "2020-02-15",
        },
    ).json["data"]
    return palm, section


def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGBA", (1200, 800), (20, 120, 60, 128)).save(output, format="PNG")
    return output.getvalue()


def test_image_variants_public_profile_and_dashboard(app, client: TestApp) -> None:
    create_admin(app)
    login(client)
    palm, section = setup_palm(client)
    upload = client.post(
        f"/api/v1/admin/palms/{palm['id']}/images",
        upload_files=[("file", "palm.png", image_bytes())],
    )
    image = upload.json["data"]
    assert image["thumbnail_url"].startswith("memory://")
    assert image["webp_url"].endswith(".webp")
    section_image = client.post(
        f"/api/v1/admin/sections/{section['id']}/image",
        upload_files=[("file", "section.png", image_bytes())],
    )
    assert section_image.json["data"]["image_url"].endswith("full.jpg")
    avatar = client.post(
        "/api/v1/admin/profile/avatar",
        upload_files=[("file", "avatar.png", image_bytes())],
    )
    assert avatar.json["data"]["avatar_url"].endswith("medium.jpg")
    client.post_json(
        f"/api/v1/admin/palms/{palm['id']}/harvests",
        {"harvest_date": "2025-01-01", "amount": "10.00", "unit": "kg", "revenue": "45.00"},
    )

    search = client.get("/api/v1/public/search?query=15559090100").json["data"]
    assert search["items"][0]["palm_code"] == "PUBLIC-IMAGE-001"
    profile = client.get("/api/v1/public/palms/public-image-001").json["data"]
    assert profile["donor"] == {"full_name": "Amina Al Palm"}
    assert "phone" not in str(profile["donor"])
    assert profile["images"][0]["medium_url"] == image["medium_url"]
    assert profile["harvest_summary"]["total_revenue"] == "45.00"
    overview = client.get("/api/v1/admin/dashboard/overview").json["data"]
    assert overview["totals"]["palms"] == 1
    assert overview["totals"]["revenue"] == "45.00"
    assert client.get("/api/v1/admin/dashboard/activity").json["data"]["pagination"]["total"] >= 2

    client.delete(f"/api/v1/admin/palms/{palm['id']}/images/{image['id']}")
    assert not any(
        key.startswith(f"images/palms/{palm['id']}/")
        for key in app.registry.palms_storage.objects
    )


def test_reports_schedules_and_injected_email_transport(app, client: TestApp) -> None:
    create_admin(app)
    login(client)
    setup_palm(client)
    app.registry.palms_settings.email_enabled = True
    transport = MemoryEmailTransport()
    app.registry.palms_email_service.transport = transport

    client.post_json("/api/v1/auth/forgot-password", {"email": "advanced-admin@example.com"})
    assert len(transport.messages) == 1
    assert "Reset your password" in transport.messages[0]["Subject"]

    template = client.post_json(
        "/api/v1/admin/reports/templates",
        {"name": "Palm CSV", "report_type": "palms", "fields": ["code", "donor_name"]},
    ).json["data"]
    generated = client.post_json(
        "/api/v1/admin/reports/generate",
        {"report_type": "palms", "fields": ["code", "donor_name"], "format": "csv"},
    ).json["data"]
    assert generated["status"] == "succeeded"
    assert generated["files"][0]["filename"].endswith(".csv")
    downloaded = client.get(f"/api/v1/admin/report-runs/{generated['id']}/download").json["data"]
    assert downloaded["files"][0]["download_url"].startswith("memory://")

    schedule = client.post_json(
        "/api/v1/admin/report-schedules",
        {
            "name": "Daily Palm Report",
            "report_type": "palms",
            "template_id": template["id"],
            "frequency": "daily",
            "run_time": "09:30",
            "timezone": "UTC",
            "format": "csv",
            "recipients": ["reports@example.com"],
        },
    ).json["data"]
    assert schedule["next_run_at"]
    paused = client.post(f"/api/v1/admin/report-schedules/{schedule['id']}/pause").json["data"]
    assert paused["enabled"] is False and paused["next_run_at"] is None
    resumed = client.post(f"/api/v1/admin/report-schedules/{schedule['id']}/resume").json["data"]
    assert resumed["enabled"] is True and resumed["next_run_at"]

    session = app.registry.palms_database.session_factory()
    try:
        logs = list(session.scalars(select(EmailLog)))
        assert logs and logs[0].status == "sent"
    finally:
        session.close()


def test_worker_executes_a_durable_queued_report(tmp_path) -> None:
    """The worker only marks the persisted run complete after creating its file."""
    settings = Settings(
        app_environment="testing",
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'reports-worker.db').as_posix()}",
    )
    database = Database(settings)
    Base.metadata.create_all(database.engine)
    session = database.session_factory()
    try:
        run = ReportRun(
            report_type="sections",
            format="csv",
            fields_json=["name"],
            filters_json={},
            status="queued",
        )
        session.add(run)
        session.commit()
        run_id = str(run.id)
        generate_report_job(settings.model_dump(mode="json"), run_id)
        session.expire_all()
        persisted = session.get(ReportRun, run.id)
        assert persisted is not None
        assert persisted.status == "succeeded"
        assert persisted.files and persisted.files[0].filename.endswith(".csv")
    finally:
        session.close()
        database.dispose()

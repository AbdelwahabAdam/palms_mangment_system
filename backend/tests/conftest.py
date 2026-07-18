"""Shared integration-test application fixtures."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from pyramid.router import Router
from sqlalchemy import select
from webtest import TestApp

from palms_api import main
from palms_api.email_service import MemoryEmailTransport
from palms_api.models import Base, Role, User
from palms_api.seeding import seed_system_rbac
from palms_api.security import hash_password

PASSWORD = "StrongPassword123"


@pytest.fixture
def app() -> Iterator[Router]:
    application = main(
        {},
        app_environment="testing",
        database_url="sqlite+pysqlite:///:memory:",
        log_level="WARNING",
    )
    Base.metadata.create_all(application.registry.palms_database.engine)
    session = application.registry.palms_database.session_factory()
    try:
        seed_system_rbac(session)
        session.commit()
    finally:
        session.close()
    yield application
    application.registry.palms_database.dispose()


@pytest.fixture
def client(app: Router) -> TestApp:
    return TestApp(app)


@pytest.fixture
def make_user(app: Router) -> Callable[..., dict[str, str]]:
    """Create a durable user for any seeded role without leaking ORM sessions."""

    def factory(
        *,
        role_name: str = "Super Admin",
        email: str = "admin@example.com",
        password: str = PASSWORD,
    ) -> dict[str, str]:
        session = app.registry.palms_database.session_factory()
        try:
            role = session.scalar(select(Role).where(Role.name == role_name))
            assert role is not None, f"Missing seeded role: {role_name}"
            user = User(
                email=email,
                full_name=f"{role_name} Test User",
                password_hash=hash_password(password),
                role_id=role.id,
            )
            session.add(user)
            session.flush()
            result = {"id": str(user.id), "email": user.email, "password": password}
            session.commit()
            return result
        finally:
            session.close()

    return factory


@pytest.fixture
def login() -> Callable[..., object]:
    """Authenticate through the real endpoint and retain the session cookie."""

    def factory(client: TestApp, *, email: str = "admin@example.com", password: str = PASSWORD):
        return client.post_json("/api/v1/auth/login", {"email": email, "password": password})

    return factory


@pytest.fixture
def domain_builder() -> Callable[..., dict[str, dict]]:
    """Create the donor, sections, and palms used by endpoint integration tests."""

    def factory(client: TestApp, *, suffix: str = "001") -> dict[str, dict]:
        donor = client.post_json(
            "/api/v1/admin/donors",
            {
                "full_name": f"Donor {suffix}",
                "phone": f"+1 (555) 010-{suffix[-4:].zfill(4)}",
                "email": f"donor-{suffix}@example.com",
                "donation_date": "2024-01-15",
            },
        ).json["data"]
        section = client.post_json(
            "/api/v1/admin/sections",
            {
                "name": f"Section {suffix}",
                "location_name": "North Field",
                "soil_type": "Loam",
                "irrigation_type": "Drip",
            },
        ).json["data"]
        alternate_section = client.post_json(
            "/api/v1/admin/sections",
            {"name": f"Section Alternate {suffix}", "location_name": "South Field"},
        ).json["data"]
        palm = client.post_json(
            "/api/v1/admin/palms",
            {
                "code": f"PALM-{suffix}",
                "donor_id": donor["id"],
                "section_id": section["id"],
                "plantation_date": "2020-01-15",
                "status": "active",
                "current_health_status": "healthy",
            },
        ).json["data"]
        return {
            "donor": donor,
            "section": section,
            "alternate_section": alternate_section,
            "palm": palm,
        }

    return factory


@pytest.fixture
def memory_email(app: Router) -> MemoryEmailTransport:
    """Inject a no-network mail transport and enable deterministic delivery."""
    transport = MemoryEmailTransport()
    app.registry.palms_settings.email_enabled = True
    app.registry.palms_email_service.transport = transport
    return transport

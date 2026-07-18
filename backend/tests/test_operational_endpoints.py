"""Integration coverage for the operational API contract."""

from __future__ import annotations

from uuid import UUID

from pyramid.router import Router
from webtest import TestApp


def test_health_reports_service_and_database_status(client: TestApp) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.json == {
        "status": "ok",
        "database": "ok",
        "version": "0.1.0",
    }
    UUID(response.headers["X-Request-ID"])


def test_health_hides_database_connection_failures(
    app: Router,
    client: TestApp,
    monkeypatch,
) -> None:
    def unavailable_connection() -> None:
        raise RuntimeError("database credentials must not reach the client")

    monkeypatch.setattr(
        app.registry.palms_database.engine,
        "connect",
        unavailable_connection,
    )

    response = client.get("/health", status=503)

    assert response.content_type == "application/json"
    assert response.json == {
        "status": "degraded",
        "database": "unavailable",
        "version": "0.1.0",
    }
    assert "credentials" not in response.text


def test_meta_exposes_versioned_service_metadata(client: TestApp) -> None:
    response = client.get("/api/v1/meta")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.json == {
        "data": {
            "service": "palms-api",
            "version": "0.1.0",
            "api_version": "v1",
        }
    }

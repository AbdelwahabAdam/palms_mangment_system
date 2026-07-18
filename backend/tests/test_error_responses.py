"""Integration coverage for globally formatted API errors."""

from __future__ import annotations

from webtest import TestApp


def test_unknown_route_returns_standard_json_not_found(client: TestApp) -> None:
    response = client.get("/api/v1/does-not-exist", status=404)

    assert response.content_type == "application/json"
    assert response.json == {
        "error": {
            "code": "not_found",
            "message": "The requested resource was not found.",
        }
    }
    assert "<html" not in response.text.lower()


def test_unsupported_endpoint_method_returns_json_error(client: TestApp) -> None:
    response = client.post("/api/v1/meta", status=404)

    assert response.content_type == "application/json"
    assert response.json["error"]["code"] == "not_found"

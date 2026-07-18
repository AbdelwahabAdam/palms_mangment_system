"""Operational API endpoints."""

from __future__ import annotations

import logging

from pyramid.request import Request
from pyramid.response import Response

from palms_api.config import Settings
from palms_api.database import Database
from palms_api.responses import json_response, success_response

LOGGER = logging.getLogger("palms_api.views")


def health_view(request: Request) -> Response:
    """Report service and database availability without exposing DB failures."""
    settings: Settings = request.registry.palms_settings
    database: Database = request.registry.palms_database
    database_is_available = database.check_connection()

    if not database_is_available:
        LOGGER.warning(
            "database_health_check_failed",
            extra={
                "event": "database_health_check_failed",
                "request_id": getattr(request, "request_id", None),
            },
        )
        return json_response(
            {
                "status": "degraded",
                "database": "unavailable",
                "version": settings.app_version,
            },
            status=503,
        )

    return json_response(
        {
            "status": "ok",
            "database": "ok",
            "version": settings.app_version,
        }
    )


def meta_view(request: Request) -> Response:
    """Expose non-sensitive, versioned service metadata."""
    settings: Settings = request.registry.palms_settings
    return success_response(
        {
            "service": settings.app_name,
            "version": settings.app_version,
            "api_version": "v1",
        }
    )

"""Centralized JSON API error types and Pyramid exception views."""

from __future__ import annotations

import logging
from typing import Any

from pyramid.httpexceptions import HTTPException
from pyramid.request import Request
from pyramid.response import Response

from palms_api.responses import json_response

LOGGER = logging.getLogger("palms_api.errors")


class APIError(Exception):
    """An expected client-facing API failure with a safe public message."""

    def __init__(
        self,
        *,
        status: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def error_response(
    *,
    status: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> Response:
    """Return the standard JSON error envelope."""
    error: dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return json_response({"error": error}, status=status)


def api_error_view(context: APIError, request: Request) -> Response:
    """Render expected errors without Pyramid's HTML exception body."""
    return error_response(
        status=context.status,
        code=context.code,
        message=context.message,
        details=context.details,
    )


def http_exception_view(context: HTTPException, request: Request) -> Response:
    """Render HTTP exceptions with safe, consistent API messages."""
    responses = {
        400: ("bad_request", "The request could not be processed."),
        401: ("unauthorized", "Authentication is required."),
        403: ("forbidden", "You do not have permission to access this resource."),
        404: ("not_found", "The requested resource was not found."),
        405: ("method_not_allowed", "The HTTP method is not allowed for this resource."),
        415: ("unsupported_media_type", "The request content type is not supported."),
    }
    code, message = responses.get(
        context.status_code,
        ("http_error", "The request could not be processed."),
    )
    return error_response(status=context.status_code, code=code, message=message)


def unexpected_error_view(context: Exception, request: Request) -> Response:
    """Log unhandled exceptions internally and never return their details."""
    LOGGER.exception(
        "unhandled_request_exception",
        extra={
            "event": "unhandled_request_exception",
            "request_id": getattr(request, "request_id", None),
        },
    )
    return error_response(
        status=500,
        code="internal_server_error",
        message="An unexpected error occurred.",
    )


def not_found_view(request: Request) -> Response:
    """Ensure unmatched routes are JSON-only as well."""
    return error_response(
        status=404,
        code="not_found",
        message="The requested resource was not found.",
    )


def forbidden_view(request: Request) -> Response:
    """Ensure Pyramid's forbidden response follows the standard envelope."""
    return error_response(
        status=403,
        code="forbidden",
        message="You do not have permission to access this resource.",
    )

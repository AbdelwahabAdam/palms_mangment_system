"""Pydantic helpers for validating JSON request bodies."""

from __future__ import annotations

from json import JSONDecodeError
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel, ValidationError

from palms_api.errors import APIError

if TYPE_CHECKING:
    from pyramid.request import Request

ModelT = TypeVar("ModelT", bound=BaseModel)


def validate_json_body(request: Request, model: type[ModelT]) -> ModelT:
    """Parse and validate one JSON request body without exposing raw inputs."""
    if request.content_type.lower() != "application/json":
        raise APIError(
            status=415,
            code="unsupported_media_type",
            message="Content-Type must be application/json.",
        )

    try:
        payload = request.json_body
    except (JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        raise APIError(
            status=400,
            code="invalid_json",
            message="Request body must contain valid JSON.",
        ) from error

    try:
        return model.model_validate(payload)
    except ValidationError as error:
        details = [
            {
                "field": ".".join(str(part) for part in issue["loc"]) or "body",
                "code": issue["type"],
                "message": issue["msg"],
            }
            for issue in error.errors(include_url=False, include_input=False)
        ]
        raise APIError(
            status=422,
            code="validation_error",
            message="Request validation failed.",
            details=details,
        ) from error

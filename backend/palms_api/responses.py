"""JSON serialization and the API's response envelope helpers."""

from __future__ import annotations

import json
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pyramid.response import Response


def json_default(value: Any) -> Any:
    """Serialize common API values, including UUIDs, consistently."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def json_dumps(value: Any, **_: Any) -> str:
    """Encode JSON with deterministic, UUID-safe defaults."""
    return json.dumps(
        value,
        default=json_default,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def json_response(payload: Any, *, status: int = 200) -> Response:
    """Create a JSON-only Pyramid response."""
    return Response(
        body=json_dumps(payload).encode("utf-8"),
        status=status,
        content_type="application/json",
        charset="UTF-8",
    )


def success_response(data: Any, *, status: int = 200) -> Response:
    """Return the standard successful API envelope."""
    return json_response({"data": data}, status=status)

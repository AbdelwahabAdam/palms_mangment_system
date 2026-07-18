"""Structured application logging and request correlation."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from pyramid.request import Request
    from pyramid.response import Response

LOGGER = logging.getLogger("palms_api.requests")
_HANDLER_NAME = "palms_api_json_handler"


class JsonFormatter(logging.Formatter):
    """Emit application logs as one JSON object per line."""

    _fields = (
        "event",
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "environment",
        "version",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in self._fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_structured_logging(level: str) -> None:
    """Configure the application logger once without changing host logging."""
    logger = logging.getLogger("palms_api")
    logger.setLevel(level)
    logger.propagate = False

    handler = next(
        (
            candidate
            for candidate in logger.handlers
            if candidate.get_name() == _HANDLER_NAME
        ),
        None,
    )
    if handler is None:
        handler = logging.StreamHandler(sys.stdout)
        handler.set_name(_HANDLER_NAME)
        logger.addHandler(handler)

    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())


def request_logging_tween_factory(
    handler: Any,
    registry: Any,
) -> Any:
    """Attach a request ID and emit structured completion logs."""

    def request_logging_tween(request: Request) -> Response:
        request.request_id = str(uuid4())
        started_at = perf_counter()
        try:
            response = handler(request)
        except Exception:
            LOGGER.exception(
                "request_failed",
                extra={
                    "event": "request_failed",
                    "request_id": request.request_id,
                    "method": request.method,
                    "path": request.path,
                },
            )
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request.request_id
        LOGGER.info(
            "request_completed",
            extra={
                "event": "request_completed",
                "request_id": request.request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    return request_logging_tween

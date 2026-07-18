"""WSGI entrypoint for container and production Waitress hosting."""

from __future__ import annotations

from palms_api import main

application = main({})

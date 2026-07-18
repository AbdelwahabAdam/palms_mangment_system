"""RQ worker functions for durable report-run execution."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from palms_api.config import Settings
from palms_api.database import Database
from palms_api.email_service import EmailService
from palms_api.models import ReportRun, ReportSchedule
from palms_api.reporting import execute_report_run
from palms_api.storage import build_storage_client


def generate_report_job(settings_payload: dict[str, Any], report_run_id: str) -> None:
    """Load a persisted queued run and generate it in the worker process."""
    settings = Settings(**settings_payload)
    database = Database(settings)
    session = database.session_factory()
    try:
        run = session.scalar(
            select(ReportRun)
            .options(
                selectinload(ReportRun.files),
                joinedload(ReportRun.schedule)
                .selectinload(ReportSchedule.recipients),
            )
            .where(ReportRun.id == UUID(report_run_id))
        )
        if run is None or run.status != "queued":
            return
        execute_report_run(
            session,
            run=run,
            storage=build_storage_client(settings),
            email_service=EmailService(settings),
        )
        session.commit()
    finally:
        session.close()
        database.dispose()

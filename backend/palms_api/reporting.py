"""Safe report queries, CSV/PDF generation, and execution abstractions."""

from __future__ import annotations

import csv
from datetime import date
from io import BytesIO, StringIO
from typing import Any, Protocol
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from palms_api.email_service import EmailService
from palms_api.models import (
    ActivityFeed,
    Donor,
    Palm,
    ReportFile,
    ReportRun,
    ReportSchedule,
    Section,
    utcnow,
)
from palms_api.storage import StorageClient


REPORT_FIELDS: dict[str, tuple[str, ...]] = {
    "palms": (
        "code",
        "donor_name",
        "section_name",
        "plantation_date",
        "status",
        "current_health_status",
    ),
    "donors": ("full_name", "phone", "email", "donation_date"),
    "sections": ("name", "location_name", "soil_type", "irrigation_type"),
}
REPORT_FORMATS = {"csv", "pdf"}


def validate_report_request(
    report_type: str, fields: list[str] | None, filters: dict[str, Any] | None, report_format: str
) -> tuple[list[str], dict[str, Any]]:
    """Allow only known report types, display fields, formats, and filter keys."""
    if report_type not in REPORT_FIELDS:
        raise ValueError("Unsupported report type.")
    if report_format.lower() not in REPORT_FORMATS:
        raise ValueError("Report format must be csv or pdf.")
    chosen_fields = fields or list(REPORT_FIELDS[report_type])
    if not chosen_fields or len(chosen_fields) > len(REPORT_FIELDS[report_type]):
        raise ValueError("At least one allowed report field is required.")
    invalid = set(chosen_fields) - set(REPORT_FIELDS[report_type])
    if invalid or len(chosen_fields) != len(set(chosen_fields)):
        raise ValueError("Report fields must be unique and supported for this report type.")
    safe_filters = filters or {}
    allowed = {
        "palms": {"status", "section_id", "donor_id", "plantation_from", "plantation_to"},
        "donors": {"donation_from", "donation_to"},
        "sections": set(),
    }[report_type]
    if set(safe_filters) - allowed:
        raise ValueError("Unsupported report filter.")
    for key, value in safe_filters.items():
        if key.endswith("_from") or key.endswith("_to"):
            if not isinstance(value, str):
                raise ValueError(f"{key} must be an ISO date.")
            date.fromisoformat(value)
        elif key in {"section_id", "donor_id"}:
            if not isinstance(value, str):
                raise ValueError(f"{key} must be a UUID.")
            UUID(value)
        elif key == "status" and (not isinstance(value, str) or not value.strip() or len(value) > 80):
            raise ValueError("status must be a non-empty value no longer than 80 characters.")
    return list(chosen_fields), safe_filters


def report_rows(
    db: Session, *, report_type: str, fields: list[str], filters: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build reports from explicit query mappings rather than client SQL or column names."""
    if report_type == "palms":
        statement = (
            select(Palm, Donor.full_name.label("donor_name"), Section.name.label("section_name"))
            .join(Donor, Palm.donor_id == Donor.id)
            .join(Section, Palm.section_id == Section.id)
            .where(Palm.deleted_at.is_(None))
        )
        if filters.get("status"):
            statement = statement.where(Palm.status == filters["status"])
        if filters.get("section_id"):
            statement = statement.where(Palm.section_id == filters["section_id"])
        if filters.get("donor_id"):
            statement = statement.where(Palm.donor_id == filters["donor_id"])
        if filters.get("plantation_from"):
            statement = statement.where(Palm.plantation_date >= date.fromisoformat(filters["plantation_from"]))
        if filters.get("plantation_to"):
            statement = statement.where(Palm.plantation_date <= date.fromisoformat(filters["plantation_to"]))
        rows = [
            {
                "code": palm.code,
                "donor_name": donor_name,
                "section_name": section_name,
                "plantation_date": palm.plantation_date,
                "status": palm.status,
                "current_health_status": palm.current_health_status,
            }
            for palm, donor_name, section_name in db.execute(statement.order_by(Palm.code))
        ]
        return [{field: row[field] for field in fields} for row in rows]
    if report_type == "donors":
        statement = select(Donor).where(Donor.deleted_at.is_(None))
        if filters.get("donation_from"):
            statement = statement.where(Donor.donation_date >= date.fromisoformat(filters["donation_from"]))
        if filters.get("donation_to"):
            statement = statement.where(Donor.donation_date <= date.fromisoformat(filters["donation_to"]))
        rows = [
            {
                "full_name": donor.full_name,
                "phone": donor.phone,
                "email": donor.email,
                "donation_date": donor.donation_date,
            }
            for donor in db.scalars(statement.order_by(Donor.full_name))
        ]
        return [{field: row[field] for field in fields} for row in rows]
    rows = [
        {
            "name": section.name,
            "location_name": section.location_name,
            "soil_type": section.soil_type,
            "irrigation_type": section.irrigation_type,
        }
        for section in db.scalars(
            select(Section).where(Section.deleted_at.is_(None)).order_by(Section.name)
        )
    ]
    return [{field: row[field] for field in fields} for row in rows]


def render_report(*, rows: list[dict[str, Any]], fields: list[str], report_format: str) -> tuple[bytes, str]:
    """Render a report using only materialized, safe field values."""
    headings = [field.replace("_", " ").title() for field in fields]
    values = [[_report_value(row.get(field)) for field in fields] for row in rows]
    if report_format == "csv":
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(headings)
        writer.writerows(values)
        return output.getvalue().encode("utf-8"), "text/csv"
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=20, rightMargin=20)
    table = Table([headings, *values], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4d3d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    document.build([table])
    return output.getvalue(), "application/pdf"


def _report_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def report_file_data(file: ReportFile) -> dict[str, Any]:
    return {
        "id": file.id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": file.size_bytes,
        "created_at": file.created_at,
    }


def report_run_data(run: ReportRun, *, storage: StorageClient | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": run.id,
        "schedule_id": run.schedule_id,
        "report_type": run.report_type,
        "format": run.format,
        "fields": run.fields_json,
        "filters": run.filters_json,
        "status": run.status,
        "error_message": run.error_message,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "created_at": run.created_at,
        "files": [report_file_data(file) for file in run.files],
    }
    if storage and run.status == "succeeded":
        data["download_urls"] = [
            storage.get_signed_url(file.storage_key) for file in run.files
        ]
    return data


def execute_report_run(
    db: Session,
    *,
    run: ReportRun,
    storage: StorageClient,
    email_service: EmailService | None = None,
) -> ReportRun:
    """Generate a run in the current transaction; completion occurs after storage upload."""
    run.status = "running"
    run.started_at = utcnow()
    db.flush()
    try:
        rows = report_rows(
            db, report_type=run.report_type, fields=run.fields_json, filters=run.filters_json or {}
        )
        content, content_type = render_report(
            rows=rows, fields=run.fields_json, report_format=run.format
        )
        suffix = "csv" if run.format == "csv" else "pdf"
        filename = f"{run.report_type}-{run.created_at.date().isoformat()}-{str(run.id)[:8]}.{suffix}"
        key = f"reports/{run.id}/{filename}"
        storage.upload_bytes(key, content, content_type=content_type)
        report_file = ReportFile(
            report_run_id=run.id,
            storage_key=key,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
        )
        db.add(report_file)
        run.status = "succeeded"
        run.finished_at = utcnow()
        db.add(
            ActivityFeed(
                actor_user_id=run.requested_by_user_id,
                action="reports.generated",
                entity_type="report_run",
                entity_id=run.id,
                message=f"Generated {run.report_type} report.",
            )
        )
        db.flush()
        if run.schedule and email_service:
            attachment = (
                (filename, content, content_type)
                if run.schedule.attach_file
                else None
            )
            download_url = storage.get_signed_url(key)
            subject = run.schedule.email_subject or f"{run.schedule.name} report"
            for recipient in run.schedule.recipients:
                email_service.send_report_result(
                    db,
                    recipient=recipient.email,
                    subject=subject,
                    succeeded=True,
                    report_name=run.schedule.name,
                    download_url=download_url,
                    attachment=attachment,
                )
        return run
    except Exception as error:
        run.status = "failed"
        run.error_message = str(error)[:2_000]
        run.finished_at = utcnow()
        db.add(
            ActivityFeed(
                actor_user_id=run.requested_by_user_id,
                action="reports.failed",
                entity_type="report_run",
                entity_id=run.id,
                message=f"Report generation failed: {run.report_type}.",
            )
        )
        if run.schedule and email_service:
            subject = run.schedule.email_subject or f"{run.schedule.name} report"
            for recipient in run.schedule.recipients:
                email_service.send_report_result(
                    db,
                    recipient=recipient.email,
                    subject=subject,
                    succeeded=False,
                    report_name=run.schedule.name,
                    error_message=run.error_message,
                )
        return run


class ReportExecutor(Protocol):
    def submit(self, db: Session, run: ReportRun) -> ReportRun: ...


class SynchronousReportExecutor:
    """Deterministic executor for tests and local development."""

    def __init__(self, storage: StorageClient, email_service: EmailService) -> None:
        self.storage = storage
        self.email_service = email_service

    def submit(self, db: Session, run: ReportRun) -> ReportRun:
        return execute_report_run(db, run=run, storage=self.storage, email_service=self.email_service)


class RQReportExecutor:
    """Queue report work only after a queued run is already persisted."""

    def __init__(self, redis_url: str, queue_name: str, settings_payload: dict[str, Any]) -> None:
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.settings_payload = settings_payload

    def submit(self, db: Session, run: ReportRun) -> ReportRun:
        from redis import Redis
        from rq import Queue

        queue = Queue(self.queue_name, connection=Redis.from_url(self.redis_url))
        queue.enqueue("palms_api.worker.generate_report_job", self.settings_payload, str(run.id))
        return run

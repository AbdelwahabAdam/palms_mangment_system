"""Schedule validation, due-time calculation, and executable scheduler entrypoint."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from palms_api.config import Settings
from palms_api.database import Database
from palms_api.email_service import EmailService
from palms_api.models import ReportRun, ReportSchedule, utcnow
from palms_api.reporting import RQReportExecutor, SynchronousReportExecutor
from palms_api.storage import build_storage_client


FREQUENCIES = {"daily", "weekly", "monthly", "cron"}


def validate_schedule_definition(values: dict[str, Any]) -> None:
    """Validate all stored scheduling controls before computing timestamps."""
    frequency = values.get("frequency")
    if frequency not in FREQUENCIES:
        raise ValueError("Frequency must be daily, weekly, monthly, or cron.")
    try:
        ZoneInfo(values.get("timezone", ""))
    except ZoneInfoNotFoundError as error:
        raise ValueError("Timezone must be an IANA timezone.") from error
    if values.get("format") not in {"csv", "pdf"}:
        raise ValueError("Format must be csv or pdf.")
    if frequency == "cron":
        expression = values.get("cron_expression")
        if not expression or not croniter.is_valid(expression):
            raise ValueError("A valid five-field cron expression is required.")
        return
    try:
        time.fromisoformat(values.get("run_time") or "")
    except ValueError as error:
        raise ValueError("run_time must use HH:MM format.") from error
    if frequency == "weekly" and values.get("weekday") not in range(0, 7):
        raise ValueError("weekday must be between 0 (Monday) and 6 (Sunday).")
    if frequency == "monthly" and values.get("day_of_month") not in range(1, 29):
        raise ValueError("day_of_month must be between 1 and 28.")


def next_run_at(values: dict[str, Any], *, after: datetime | None = None) -> datetime:
    """Calculate a portable naive UTC next occurrence from timezone-aware local rules."""
    validate_schedule_definition(values)
    now_utc = (after or utcnow()).replace(tzinfo=UTC)
    zone = ZoneInfo(values["timezone"])
    local_now = now_utc.astimezone(zone)
    frequency = values["frequency"]
    if frequency == "cron":
        candidate = croniter(values["cron_expression"], local_now).get_next(datetime)
        return candidate.astimezone(UTC).replace(tzinfo=None)
    run_at = time.fromisoformat(values["run_time"])
    candidate = local_now.replace(hour=run_at.hour, minute=run_at.minute, second=0, microsecond=0)
    if frequency == "daily":
        if candidate <= local_now:
            candidate += timedelta(days=1)
    elif frequency == "weekly":
        days = (values["weekday"] - candidate.weekday()) % 7
        candidate += timedelta(days=days)
        if candidate <= local_now:
            candidate += timedelta(days=7)
    else:
        day = values["day_of_month"]
        candidate = candidate.replace(day=day)
        if candidate <= local_now:
            month = candidate.month % 12 + 1
            year = candidate.year + (candidate.month == 12)
            candidate = candidate.replace(year=year, month=month, day=day)
    return candidate.astimezone(UTC).replace(tzinfo=None)


def schedule_data(schedule: ReportSchedule) -> dict[str, Any]:
    """Serialize a schedule with recipients but not user or storage internals."""
    return {
        "id": schedule.id,
        "name": schedule.name,
        "report_type": schedule.report_type,
        "template_id": schedule.template_id,
        "frequency": schedule.frequency,
        "cron_expression": schedule.cron_expression,
        "day_of_month": schedule.day_of_month,
        "weekday": schedule.weekday,
        "run_time": schedule.run_time,
        "timezone": schedule.timezone,
        "format": schedule.format,
        "fields": schedule.fields_json,
        "filters": schedule.filters_json,
        "email_subject": schedule.email_subject,
        "include_summary": schedule.include_summary,
        "attach_file": schedule.attach_file,
        "enabled": schedule.enabled,
        "recipients": [recipient.email for recipient in schedule.recipients],
        "last_run_at": schedule.last_run_at,
        "next_run_at": schedule.next_run_at,
        "created_at": schedule.created_at,
        "updated_at": schedule.updated_at,
    }


def report_executor(settings: Settings, storage=None, email_service=None):
    """Select RQ only when explicitly configured and a Redis URL exists."""
    storage = storage or build_storage_client(settings)
    email_service = email_service or EmailService(settings)
    if settings.report_execution_mode == "rq" and settings.redis_url:
        return RQReportExecutor(
            settings.redis_url, settings.rq_queue_name, settings.model_dump(mode="json")
        )
    return SynchronousReportExecutor(storage, email_service)


def run_due_schedules(settings: Settings, *, now: datetime | None = None) -> int:
    """Create durable queued runs for due schedules then submit them to the selected executor."""
    database = Database(settings)
    storage = build_storage_client(settings)
    email_service = EmailService(settings)
    executor = report_executor(settings, storage, email_service)
    session = database.session_factory()
    count = 0
    try:
        due_at = now or utcnow()
        schedules = list(
            session.scalars(
                select(ReportSchedule)
                .options(selectinload(ReportSchedule.recipients), joinedload(ReportSchedule.template))
                .where(
                    ReportSchedule.enabled.is_(True),
                    ReportSchedule.next_run_at.is_not(None),
                    ReportSchedule.next_run_at <= due_at,
                )
            )
        )
        for schedule in schedules:
            fields = schedule.fields_json or (
                schedule.template.fields_json if schedule.template else None
            )
            if not fields:
                schedule.enabled = False
                # Persist the safety disable before continuing; otherwise closing
                # the session rolls it back and the invalid schedule is retried.
                session.commit()
                continue
            run = ReportRun(
                schedule_id=schedule.id,
                report_type=schedule.report_type,
                format=schedule.format,
                fields_json=fields,
                filters_json=schedule.filters_json
                or (schedule.template.filters_json if schedule.template else None),
                requested_by_user_id=schedule.created_by_user_id,
                status="queued",
            )
            session.add(run)
            schedule.last_run_at = due_at
            schedule.next_run_at = next_run_at(
                {
                    "frequency": schedule.frequency,
                    "cron_expression": schedule.cron_expression,
                    "day_of_month": schedule.day_of_month,
                    "weekday": schedule.weekday,
                    "run_time": schedule.run_time,
                    "timezone": schedule.timezone,
                    "format": schedule.format,
                },
                after=due_at,
            )
            session.flush()
            # A queued status is committed before an external RQ job can observe it.
            session.commit()
            executor.submit(session, run)
            session.commit()
            count += 1
    finally:
        session.close()
        database.dispose()
    return count


def main() -> None:
    """Console-friendly scheduler process entrypoint."""
    from palms_api.config import get_settings

    run_due_schedules(get_settings())


if __name__ == "__main__":
    main()

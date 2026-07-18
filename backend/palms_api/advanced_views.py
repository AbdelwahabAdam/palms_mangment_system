"""Media, public, dashboard, reporting, and scheduled-report API endpoints."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from palms_api.errors import APIError
from palms_api.images import ImageVariants, delete_image_variants, process_and_store_image
from palms_api.models import (
    ActivityFeed,
    AuditLog,
    DiseaseRecord,
    Donor,
    HarvestRecord,
    Palm,
    PalmImage,
    PalmRelationship,
    ReportRun,
    ReportSchedule,
    ReportScheduleRecipient,
    ReportTemplate,
    Section,
    User,
    utcnow,
)
from palms_api.reporting import (
    REPORT_FIELDS,
    report_rows,
    report_run_data,
    validate_report_request,
)
from palms_api.responses import success_response
from palms_api.scheduler import next_run_at, report_executor, schedule_data, validate_schedule_definition
from palms_api.schemas import (
    ReportGenerateRequest,
    ReportPreviewRequest,
    ReportScheduleCreateRequest,
    ReportSchedulePatchRequest,
    ReportTemplateCreateRequest,
)
from palms_api.services import (
    audit,
    commit,
    get_active,
    not_found,
    page_payload,
    parse_page,
    parse_uuid,
    request_actor,
    require_permission,
)
from palms_api.validation import validate_json_body


def _validation_error(field: str, message: str) -> APIError:
    return APIError(
        status=422,
        code="validation_error",
        message="Request validation failed.",
        details=[{"field": field, "code": "value_error", "message": message}],
    )


def _activity(request, *, actor: User | None, action: str, entity_type: str, entity_id: UUID | None, message: str) -> None:
    request.dbsession.add(
        ActivityFeed(
            actor_user_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            message=message[:500],
        )
    )


def _storage(request):
    return request.registry.palms_storage


def _image_upload(request) -> tuple[bytes, str | None]:
    """Read only a multipart file field and leave validation to Pillow content checks."""
    if not request.content_type.lower().startswith("multipart/form-data"):
        raise APIError(
            status=415,
            code="unsupported_media_type",
            message="Content-Type must be multipart/form-data.",
        )
    upload = request.POST.get("file")
    if upload is None:
        upload = request.POST.get("image")
    stream = getattr(upload, "file", None)
    if stream is None:
        raise _validation_error("file", "A file upload is required.")
    max_bytes = request.registry.palms_settings.image_max_upload_mb * 1024 * 1024
    content = stream.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise _validation_error(
            "file",
            f"Image files may not exceed {request.registry.palms_settings.image_max_upload_mb} MB.",
        )
    return content, getattr(upload, "filename", None)


def _variants_from_palm_image(image: PalmImage) -> ImageVariants:
    return ImageVariants(
        storage_key=image.storage_key,
        thumbnail_key=image.thumbnail_key,
        medium_key=image.medium_key,
        webp_key=image.webp_key,
        thumbnail_url=image.thumbnail_url,
        medium_url=image.medium_url,
        full_url=image.full_url,
        webp_url=image.webp_url,
        metadata=image.metadata_json or {},
    )


def _derived_variants_from_full_key(key: str) -> ImageVariants:
    base = key.rsplit("/", 1)[0]
    return ImageVariants(
        storage_key=key,
        thumbnail_key=f"{base}/thumbnail.jpg",
        medium_key=f"{base}/medium.jpg",
        webp_key=f"{base}/full.webp",
        thumbnail_url="",
        medium_url="",
        full_url="",
        webp_url="",
        metadata={},
    )


def palm_image_data(image: PalmImage) -> dict[str, Any]:
    return {
        "id": image.id,
        "thumbnail_url": image.thumbnail_url,
        "medium_url": image.medium_url,
        "full_url": image.full_url,
        "webp_url": image.webp_url,
        "captured_at": image.captured_at,
        "uploaded_at": image.uploaded_at,
        "metadata": image.metadata_json,
    }


def palm_image_create_view(request):
    """Process and persist image variants for one active palm."""
    actor = require_permission(request, "palms.update")
    palm = get_active(request.dbsession, Palm, parse_uuid(request.matchdict["palm_id"], field="palm_id"))
    content, filename = _image_upload(request)
    variants = process_and_store_image(
        content=content,
        original_filename=filename,
        prefix=f"images/palms/{palm.id}",
        storage=_storage(request),
        settings=request.registry.palms_settings,
    )
    image = PalmImage(
        palm_id=palm.id,
        uploaded_by_user_id=actor.id,
        storage_key=variants.storage_key,
        thumbnail_key=variants.thumbnail_key,
        medium_key=variants.medium_key,
        webp_key=variants.webp_key,
        thumbnail_url=variants.thumbnail_url,
        medium_url=variants.medium_url,
        full_url=variants.full_url,
        webp_url=variants.webp_url,
        metadata_json=variants.metadata,
    )
    request.dbsession.add(image)
    request.dbsession.flush()
    audit(
        request, actor=actor, action="palm_images.created", entity_type="palm_image",
        entity_id=image.id, new_values={"palm_id": palm.id, "storage_key": image.storage_key},
    )
    _activity(request, actor=actor, action="palm_images.created", entity_type="palm_image", entity_id=image.id, message=f"Uploaded image for palm {palm.code}.")
    commit(request)
    return success_response(palm_image_data(image), status=201)


def palm_image_delete_view(request):
    """Delete all persisted variants before removing the image row."""
    actor = require_permission(request, "palms.update")
    palm = get_active(request.dbsession, Palm, parse_uuid(request.matchdict["palm_id"], field="palm_id"))
    image = request.dbsession.scalar(
        select(PalmImage).where(
            PalmImage.id == parse_uuid(request.matchdict["image_id"], field="image_id"),
            PalmImage.palm_id == palm.id,
        )
    )
    if image is None:
        raise not_found()
    try:
        delete_image_variants(_storage(request), _variants_from_palm_image(image))
    except RuntimeError as error:
        raise APIError(status=503, code="storage_error", message="Unable to delete all image variants.") from error
    request.dbsession.delete(image)
    audit(request, actor=actor, action="palm_images.deleted", entity_type="palm_image", entity_id=image.id)
    _activity(request, actor=actor, action="palm_images.deleted", entity_type="palm_image", entity_id=image.id, message=f"Deleted image for palm {palm.code}.")
    commit(request)
    return success_response({"deleted": True, "id": image.id})


def section_image_create_view(request):
    """Set a processed section cover image, cleaning a prior generated asset."""
    actor = require_permission(request, "sections.update")
    section = get_active(request.dbsession, Section, parse_uuid(request.matchdict["section_id"], field="section_id"))
    content, filename = _image_upload(request)
    previous_key = section.image_storage_key
    variants = process_and_store_image(
        content=content, original_filename=filename, prefix=f"images/sections/{section.id}",
        storage=_storage(request), settings=request.registry.palms_settings,
    )
    section.image_storage_key = variants.storage_key
    section.image_url = variants.full_url
    if previous_key:
        try:
            delete_image_variants(_storage(request), _derived_variants_from_full_key(previous_key))
        except RuntimeError:
            pass
    audit(request, actor=actor, action="sections.image_updated", entity_type="section", entity_id=section.id, new_values={"image_storage_key": variants.storage_key})
    _activity(request, actor=actor, action="sections.image_updated", entity_type="section", entity_id=section.id, message=f"Updated image for section {section.name}.")
    commit(request)
    return success_response({"image_url": variants.full_url, "thumbnail_url": variants.thumbnail_url})


def profile_avatar_create_view(request):
    """Set the authenticated user's processed avatar without returning storage internals."""
    user = request_actor(request)
    content, filename = _image_upload(request)
    previous_key = user.avatar_storage_key
    variants = process_and_store_image(
        content=content, original_filename=filename, prefix=f"avatars/{user.id}",
        storage=_storage(request), settings=request.registry.palms_settings,
    )
    user.avatar_storage_key = variants.storage_key
    user.avatar_url = variants.medium_url
    if previous_key:
        try:
            delete_image_variants(_storage(request), _derived_variants_from_full_key(previous_key))
        except RuntimeError:
            pass
    audit(request, actor=user, action="profile.avatar_updated", entity_type="user", entity_id=user.id)
    commit(request)
    return success_response({"avatar_url": user.avatar_url})


def _normalized_query(raw_query: str) -> tuple[str, str]:
    query = " ".join(raw_query.strip().split())
    if not query or len(query) > 120:
        raise _validation_error("query", "query must contain between 1 and 120 characters.")
    return query.casefold(), "".join(character for character in query if character.isdigit())


def _public_palm_query():
    return (
        select(Palm)
        .options(
            joinedload(Palm.donor),
            joinedload(Palm.section),
            selectinload(Palm.images),
        )
        .join(Palm.donor)
        .join(Palm.section)
        .where(Palm.deleted_at.is_(None), Donor.deleted_at.is_(None), Section.deleted_at.is_(None))
    )


def _age(plantation_date: date | None) -> dict[str, int] | None:
    if plantation_date is None:
        return None
    months = (date.today().year - plantation_date.year) * 12 + date.today().month - plantation_date.month
    if date.today().day < plantation_date.day:
        months -= 1
    return {"years": max(months, 0) // 12, "months": max(months, 0) % 12}


def _public_palm_summary(palm: Palm) -> dict[str, Any]:
    image = palm.images[0] if palm.images else None
    return {
        "palm_id": palm.id,
        "palm_code": palm.code,
        "donor_name": palm.donor.full_name,
        "section_name": palm.section.name,
        "plantation_date": palm.plantation_date,
        "current_age": _age(palm.plantation_date),
        "thumbnail_url": image.thumbnail_url if image else None,
    }


def public_search_view(request):
    """Find public palm summaries by normalized name, phone, or palm code."""
    normalized, digits = _normalized_query(request.params.get("query", ""))
    page, page_size, _, _ = parse_page(request, {"created_at", "code"})
    statement = _public_palm_query()
    phone_value = func.replace(
        func.replace(
            func.replace(
                func.replace(func.replace(Donor.phone, "+", ""), "-", ""), " ", ""
            ),
            "(",
            "",
        ),
        ")",
        "",
    )
    if digits:
        criteria = or_(
            func.lower(Palm.code).like(f"%{normalized}%"),
            func.lower(Donor.full_name).like(f"%{normalized}%"),
            phone_value.like(f"%{digits}%"),
        )
    else:
        criteria = or_(func.lower(Palm.code).like(f"%{normalized}%"), func.lower(Donor.full_name).like(f"%{normalized}%"))
    statement = statement.where(criteria)
    total = request.dbsession.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    palms = list(request.dbsession.scalars(statement.order_by(Palm.code).offset((page - 1) * page_size).limit(page_size)))
    return success_response(page_payload([_public_palm_summary(palm) for palm in palms], page=page, page_size=page_size, total=total))


def public_donor_suggestions_view(request):
    """Return bounded public name-only suggestions without donor contact details."""
    normalized, _ = _normalized_query(request.params.get("query", ""))
    raw_limit = request.params.get("limit", "10")
    try:
        limit = min(max(int(raw_limit), 1), 20)
    except ValueError as error:
        raise _validation_error("limit", "limit must be an integer.") from error
    donors = list(
        request.dbsession.scalars(
            select(Donor)
            .where(Donor.deleted_at.is_(None), func.lower(Donor.full_name).like(f"%{normalized}%"))
            .order_by(Donor.full_name)
            .limit(limit)
        )
    )
    return success_response({"items": [{"id": donor.id, "full_name": donor.full_name} for donor in donors]})


def public_palm_profile_view(request):
    """Return a complete but donor-contact-safe public palm profile."""
    palm = request.dbsession.scalar(
        _public_palm_query()
        .options(
            selectinload(Palm.harvests),
            selectinload(Palm.diseases).selectinload(DiseaseRecord.treatments),
            selectinload(Palm.parent_relationships).joinedload(PalmRelationship.child),
        )
        .where(func.lower(Palm.code) == request.matchdict["palm_code"].strip().casefold())
    )
    if palm is None:
        raise not_found()
    total_harvest = sum((record.amount for record in palm.harvests), start=0)
    total_revenue = sum((record.revenue or 0 for record in palm.harvests), start=0)
    return success_response(
        {
            "id": palm.id, "code": palm.code, "plantation_date": palm.plantation_date,
            "status": palm.status, "current_health_status": palm.current_health_status,
            "description": palm.description, "current_age": _age(palm.plantation_date),
            "donor": {"full_name": palm.donor.full_name},
            "section": {"name": palm.section.name, "location_name": palm.section.location_name, "image_url": palm.section.image_url},
            "images": [palm_image_data(image) for image in palm.images],
            "harvest_summary": {"total_amount": total_harvest, "total_revenue": total_revenue, "records_count": len(palm.harvests)},
            "diseases": [
                {"disease_name": record.disease_name, "detected_at": record.detected_at, "status": record.status, "notes": record.notes,
                 "treatments": [{"treatment_name": item.treatment_name, "treatment_date": item.treatment_date, "notes": item.notes} for item in record.treatments]}
                for record in palm.diseases
            ],
            "children": [
                {"id": relationship.child.id, "code": relationship.child.code, "relationship_type": relationship.relationship_type}
                for relationship in palm.parent_relationships if relationship.child.deleted_at is None
            ],
        }
    )


def activity_data(entry: ActivityFeed) -> dict[str, Any]:
    return {
        "id": entry.id, "action": entry.action, "entity_type": entry.entity_type,
        "entity_id": entry.entity_id, "message": entry.message, "actor_user_id": entry.actor_user_id,
        "created_at": entry.created_at,
    }


def dashboard_overview_view(request):
    """Return accurate aggregates and bounded recent operational data."""
    require_permission(request, "palms.read")
    db = request.dbsession
    active_palms = db.scalar(select(func.count(Palm.id)).where(Palm.deleted_at.is_(None), Palm.status == "active")) or 0
    inactive_palms = db.scalar(select(func.count(Palm.id)).where(Palm.deleted_at.is_(None), Palm.status != "active")) or 0
    recent_harvests = list(
        db.scalars(
            select(HarvestRecord).join(Palm).where(Palm.deleted_at.is_(None)).order_by(HarvestRecord.harvest_date.desc()).limit(10)
        )
    )
    activity = list(db.scalars(select(ActivityFeed).order_by(ActivityFeed.created_at.desc()).limit(10)))
    upcoming = list(db.scalars(
        select(ReportSchedule).where(ReportSchedule.enabled.is_(True), ReportSchedule.next_run_at.is_not(None)).order_by(ReportSchedule.next_run_at).limit(10)
    ))
    return success_response(
        {
            "totals": {
                "palms": db.scalar(select(func.count(Palm.id)).where(Palm.deleted_at.is_(None))) or 0,
                "donors": db.scalar(select(func.count(Donor.id)).where(Donor.deleted_at.is_(None))) or 0,
                "sections": db.scalar(select(func.count(Section.id)).where(Section.deleted_at.is_(None))) or 0,
                "revenue": db.scalar(select(func.coalesce(func.sum(HarvestRecord.revenue), 0)).join(Palm).where(Palm.deleted_at.is_(None))) or 0,
                "active_palms": active_palms,
                "inactive_palms": inactive_palms,
            },
            "recent_harvests": [
                {"id": record.id, "palm_id": record.palm_id, "harvest_date": record.harvest_date, "amount": record.amount, "unit": record.unit, "revenue": record.revenue}
                for record in recent_harvests
            ],
            "activity": [activity_data(entry) for entry in activity],
            "upcoming_reports": [{"id": item.id, "name": item.name, "next_run_at": item.next_run_at, "format": item.format} for item in upcoming],
        }
    )


def dashboard_activity_view(request):
    require_permission(request, "palms.read")
    page, page_size, _, _ = parse_page(request, {"created_at"})
    total = request.dbsession.scalar(select(func.count(ActivityFeed.id))) or 0
    entries = list(request.dbsession.scalars(select(ActivityFeed).order_by(ActivityFeed.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
    return success_response(page_payload([activity_data(entry) for entry in entries], page=page, page_size=page_size, total=total))


def _validated_report_payload(report_type: str, fields, filters, report_format: str):
    try:
        return validate_report_request(report_type, fields, filters, report_format)
    except (TypeError, ValueError) as error:
        raise _validation_error("report", str(error)) from error


def report_types_view(request):
    require_permission(request, "reports.read")
    return success_response({"items": [{"code": key, "fields": list(fields), "formats": ["csv", "pdf"]} for key, fields in REPORT_FIELDS.items()]})


def report_preview_view(request):
    require_permission(request, "reports.read")
    data = validate_json_body(request, ReportPreviewRequest)
    fields, filters = _validated_report_payload(data.report_type, data.fields, data.filters, "csv")
    try:
        rows = report_rows(request.dbsession, report_type=data.report_type, fields=fields, filters=filters)
    except ValueError as error:
        raise _validation_error("filters", str(error)) from error
    return success_response({"fields": fields, "items": rows[:100], "total": len(rows), "truncated": len(rows) > 100})


def report_generate_view(request):
    actor = require_permission(request, "reports.generate")
    data = validate_json_body(request, ReportGenerateRequest)
    fields, filters = _validated_report_payload(data.report_type, data.fields, data.filters, data.format)
    run = ReportRun(report_type=data.report_type, format=data.format, fields_json=fields, filters_json=filters, requested_by_user_id=actor.id, status="queued")
    request.dbsession.add(run)
    request.dbsession.flush()
    audit(request, actor=actor, action="reports.queued", entity_type="report_run", entity_id=run.id, new_values={"report_type": run.report_type, "format": run.format})
    _activity(request, actor=actor, action="reports.queued", entity_type="report_run", entity_id=run.id, message=f"Queued {run.report_type} report.")
    commit(request)
    run = request.registry.palms_report_executor.submit(request.dbsession, run)
    commit(request)
    return success_response(report_run_data(run, storage=_storage(request)))


def template_data(template: ReportTemplate) -> dict[str, Any]:
    return {"id": template.id, "name": template.name, "report_type": template.report_type, "fields": template.fields_json, "filters": template.filters_json, "created_at": template.created_at}


def report_templates_list_view(request):
    require_permission(request, "reports.read")
    templates = list(request.dbsession.scalars(select(ReportTemplate).order_by(ReportTemplate.name)))
    return success_response({"items": [template_data(template) for template in templates]})


def report_template_create_view(request):
    actor = require_permission(request, "reports.generate")
    data = validate_json_body(request, ReportTemplateCreateRequest)
    fields, filters = _validated_report_payload(data.report_type, data.fields, data.filters, "csv")
    template = ReportTemplate(name=data.name, report_type=data.report_type, fields_json=fields, filters_json=filters, created_by_user_id=actor.id)
    request.dbsession.add(template)
    request.dbsession.flush()
    audit(request, actor=actor, action="report_templates.created", entity_type="report_template", entity_id=template.id, new_values={"name": template.name, "report_type": template.report_type})
    _activity(request, actor=actor, action="report_templates.created", entity_type="report_template", entity_id=template.id, message=f"Created report template {template.name}.")
    commit(request)
    return success_response(template_data(template), status=201)


def _schedule(request, raw_id: str) -> ReportSchedule:
    return get_active(
        request.dbsession, ReportSchedule, parse_uuid(raw_id, field="schedule_id"),
        options=[selectinload(ReportSchedule.recipients), joinedload(ReportSchedule.template)],
    )


def _schedule_values(schedule: ReportSchedule, changes: dict[str, Any]) -> dict[str, Any]:
    return {
        "frequency": changes.get("frequency", schedule.frequency),
        "cron_expression": changes.get("cron_expression", schedule.cron_expression),
        "day_of_month": changes.get("day_of_month", schedule.day_of_month),
        "weekday": changes.get("weekday", schedule.weekday),
        "run_time": changes.get("run_time", schedule.run_time),
        "timezone": changes.get("timezone", schedule.timezone),
        "format": changes.get("format", schedule.format),
    }


def _validate_schedule_report(request, *, report_type: str, fields, filters, report_format: str, template_id: UUID | None) -> tuple[list[str] | None, dict[str, Any]]:
    template = None
    if template_id:
        template = request.dbsession.get(ReportTemplate, template_id)
        if template is None:
            raise not_found()
        if template.report_type != report_type:
            raise _validation_error("template_id", "Template report type must match the schedule.")
    if fields is None and template:
        fields = template.fields_json
        filters = filters if filters is not None else template.filters_json
    if fields is None:
        raise _validation_error("fields", "fields are required unless a template provides them.")
    chosen_fields, safe_filters = _validated_report_payload(report_type, fields, filters, report_format)
    return chosen_fields, safe_filters


def report_schedules_list_view(request):
    require_permission(request, "reports.read")
    schedules = list(request.dbsession.scalars(select(ReportSchedule).options(selectinload(ReportSchedule.recipients)).order_by(ReportSchedule.created_at.desc())))
    return success_response({"items": [schedule_data(schedule) for schedule in schedules]})


def report_schedule_create_view(request):
    actor = require_permission(request, "reports.schedule")
    data = validate_json_body(request, ReportScheduleCreateRequest)
    fields, filters = _validate_schedule_report(request, report_type=data.report_type, fields=data.fields, filters=data.filters, report_format=data.format, template_id=data.template_id)
    values = data.model_dump(exclude={"recipients", "fields", "filters"})
    values["fields_json"] = fields
    values["filters_json"] = filters
    try:
        validate_schedule_definition(values)
        values["next_run_at"] = next_run_at(values)
    except ValueError as error:
        raise _validation_error("schedule", str(error)) from error
    schedule = ReportSchedule(**values, created_by_user_id=actor.id)
    schedule.recipients = [ReportScheduleRecipient(email=email) for email in data.recipients]
    request.dbsession.add(schedule)
    request.dbsession.flush()
    audit(request, actor=actor, action="report_schedules.created", entity_type="report_schedule", entity_id=schedule.id, new_values={"name": schedule.name, "frequency": schedule.frequency})
    _activity(request, actor=actor, action="report_schedules.created", entity_type="report_schedule", entity_id=schedule.id, message=f"Created report schedule {schedule.name}.")
    commit(request)
    return success_response(schedule_data(schedule), status=201)


def report_schedule_get_view(request):
    require_permission(request, "reports.read")
    return success_response(schedule_data(_schedule(request, request.matchdict["schedule_id"])))


def report_schedule_patch_view(request):
    actor = require_permission(request, "reports.schedule")
    schedule = _schedule(request, request.matchdict["schedule_id"])
    data = validate_json_body(request, ReportSchedulePatchRequest)
    changes = data.model_dump(exclude_unset=True)
    fields, filters = _validate_schedule_report(
        request, report_type=changes.get("report_type", schedule.report_type),
        fields=changes.get("fields", schedule.fields_json), filters=changes.get("filters", schedule.filters_json),
        report_format=changes.get("format", schedule.format), template_id=changes.get("template_id", schedule.template_id),
    )
    changes["fields_json"] = fields
    changes["filters_json"] = filters
    changes.pop("fields", None)
    changes.pop("filters", None)
    recipients = changes.pop("recipients", None)
    values = _schedule_values(schedule, changes)
    try:
        validate_schedule_definition(values)
        if any(key in changes for key in {"frequency", "cron_expression", "day_of_month", "weekday", "run_time", "timezone", "enabled"}):
            changes["next_run_at"] = next_run_at(values) if changes.get("enabled", schedule.enabled) else None
    except ValueError as error:
        raise _validation_error("schedule", str(error)) from error
    for field, value in changes.items():
        setattr(schedule, field, value)
    if recipients is not None:
        schedule.recipients[:] = [ReportScheduleRecipient(email=email) for email in recipients]
    audit(request, actor=actor, action="report_schedules.updated", entity_type="report_schedule", entity_id=schedule.id, new_values={"name": schedule.name, "enabled": schedule.enabled})
    _activity(request, actor=actor, action="report_schedules.updated", entity_type="report_schedule", entity_id=schedule.id, message=f"Updated report schedule {schedule.name}.")
    commit(request)
    return success_response(schedule_data(schedule))


def report_schedule_delete_view(request):
    actor = require_permission(request, "reports.schedule")
    schedule = _schedule(request, request.matchdict["schedule_id"])
    identifier = schedule.id
    name = schedule.name
    request.dbsession.delete(schedule)
    audit(request, actor=actor, action="report_schedules.deleted", entity_type="report_schedule", entity_id=identifier, old_values={"name": name})
    _activity(request, actor=actor, action="report_schedules.deleted", entity_type="report_schedule", entity_id=identifier, message=f"Deleted report schedule {name}.")
    commit(request)
    return success_response({"deleted": True, "id": identifier})


def _schedule_state_view(request, *, enabled: bool):
    actor = require_permission(request, "reports.schedule")
    schedule = _schedule(request, request.matchdict["schedule_id"])
    schedule.enabled = enabled
    schedule.next_run_at = next_run_at(_schedule_values(schedule, {})) if enabled else None
    audit(request, actor=actor, action="report_schedules.resumed" if enabled else "report_schedules.paused", entity_type="report_schedule", entity_id=schedule.id, new_values={"enabled": enabled})
    _activity(request, actor=actor, action="report_schedules.resumed" if enabled else "report_schedules.paused", entity_type="report_schedule", entity_id=schedule.id, message=f"{'Resumed' if enabled else 'Paused'} report schedule {schedule.name}.")
    commit(request)
    return success_response(schedule_data(schedule))


def report_schedule_pause_view(request):
    return _schedule_state_view(request, enabled=False)


def report_schedule_resume_view(request):
    return _schedule_state_view(request, enabled=True)


def report_schedule_runs_view(request):
    require_permission(request, "reports.read")
    schedule = _schedule(request, request.matchdict["schedule_id"])
    page, page_size, _, _ = parse_page(request, {"created_at"})
    statement = select(ReportRun).options(selectinload(ReportRun.files)).where(ReportRun.schedule_id == schedule.id)
    total = request.dbsession.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    runs = list(request.dbsession.scalars(statement.order_by(ReportRun.created_at.desc()).offset((page - 1) * page_size).limit(page_size)))
    return success_response(page_payload([report_run_data(run) for run in runs], page=page, page_size=page_size, total=total))


def report_run_download_view(request):
    require_permission(request, "reports.read")
    run = request.dbsession.scalar(
        select(ReportRun).options(selectinload(ReportRun.files)).where(ReportRun.id == parse_uuid(request.matchdict["run_id"], field="run_id"))
    )
    if run is None:
        raise not_found()
    if run.status != "succeeded" or not run.files:
        raise APIError(status=409, code="report_not_ready", message="The report has no completed file yet.")
    return success_response({"run_id": run.id, "files": [{"filename": file.filename, "download_url": _storage(request).get_signed_url(file.storage_key)} for file in run.files]})

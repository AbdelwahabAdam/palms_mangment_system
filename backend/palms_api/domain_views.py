"""Donor, section, palm, and palm-history administration API endpoints."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import joinedload, selectinload

from palms_api.errors import APIError
from palms_api.models import (
    DiseaseRecord,
    Donor,
    HarvestRecord,
    Palm,
    PalmImage,
    PalmNote,
    PalmRelationship,
    Section,
    TreatmentRecord,
)
from palms_api.responses import success_response
from palms_api.schemas import (
    BulkPalmIdsRequest,
    BulkPalmSectionRequest,
    DiseaseCreateRequest,
    DiseasePatchRequest,
    DonorCreateRequest,
    DonorPatchRequest,
    HarvestCreateRequest,
    HarvestPatchRequest,
    PalmCreateRequest,
    PalmNoteCreateRequest,
    PalmPatchRequest,
    PalmRelationshipCreateRequest,
    SectionCreateRequest,
    SectionPatchRequest,
    TreatmentCreateRequest,
    TreatmentPatchRequest,
)
from palms_api.services import (
    audit,
    commit,
    conflict,
    disease_data,
    donor_data,
    get_active,
    harvest_data,
    not_found,
    note_data,
    page_payload,
    palm_data,
    parse_page,
    parse_uuid,
    require_permission,
    section_data,
    treatment_data,
    utcnow,
)
from palms_api.validation import validate_json_body


def _record_snapshot(record: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: getattr(record, field) for field in fields}


def _donor(request, raw_id: str) -> Donor:
    return get_active(request.dbsession, Donor, parse_uuid(raw_id, field="donor_id"))


def _section(request, raw_id: str) -> Section:
    return get_active(request.dbsession, Section, parse_uuid(raw_id, field="section_id"))


def _palm(request, raw_id: str, *, detail: bool = False) -> Palm:
    options: list[Any] = [joinedload(Palm.donor), joinedload(Palm.section)]
    if detail:
        options.extend(
            [
                selectinload(Palm.harvests),
                selectinload(Palm.diseases).selectinload(DiseaseRecord.treatments),
                selectinload(Palm.notes),
                selectinload(Palm.images),
                selectinload(Palm.parent_relationships).joinedload(PalmRelationship.child),
                selectinload(Palm.child_relationships).joinedload(PalmRelationship.parent),
            ]
        )
    return get_active(
        request.dbsession, Palm, parse_uuid(raw_id, field="palm_id"), options=options
    )


def _ensure_palm_owners(request, *, donor_id, section_id) -> tuple[Donor, Section]:
    donor = get_active(request.dbsession, Donor, donor_id)
    section = get_active(request.dbsession, Section, section_id)
    return donor, section


def _palm_query(request, *, donor_id=None, section_id=None):
    statement = (
        select(Palm)
        .options(joinedload(Palm.donor), joinedload(Palm.section))
        .join(Palm.donor)
        .join(Palm.section)
        .where(Palm.deleted_at.is_(None))
    )
    if donor_id is not None:
        statement = statement.where(Palm.donor_id == donor_id)
    if section_id is not None:
        statement = statement.where(Palm.section_id == section_id)
    return statement


def donors_list_view(request):
    """List donors with portable filtering, sorting, pagination, and palm counts."""
    require_permission(request, "donors.read")
    page, page_size, sort, descending = parse_page(
        request, {"created_at", "updated_at", "full_name", "donation_date"}
    )
    count_subquery = (
        select(func.count(Palm.id))
        .where(Palm.donor_id == Donor.id, Palm.deleted_at.is_(None))
        .correlate(Donor)
        .scalar_subquery()
        .label("palm_count")
    )
    filters = [Donor.deleted_at.is_(None)]
    query = request.params.get("query", "").strip()
    if query:
        pattern = f"%{query}%"
        filters.append(
            or_(
                Donor.full_name.ilike(pattern),
                Donor.phone.ilike(pattern),
                Donor.email.ilike(pattern),
            )
        )
    total = request.dbsession.scalar(select(func.count(Donor.id)).where(*filters)) or 0
    column = getattr(Donor, sort)
    statement = (
        select(Donor, count_subquery)
        .where(*filters)
        .order_by(column.desc() if descending else column.asc(), Donor.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = request.dbsession.execute(statement)
    return success_response(
        page_payload(
            [donor_data(donor, palm_count=palm_count) for donor, palm_count in rows],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


def donor_create_view(request):
    """Create a donor."""
    actor = require_permission(request, "donors.create")
    data = validate_json_body(request, DonorCreateRequest)
    donor = Donor(**data.model_dump())
    request.dbsession.add(donor)
    request.dbsession.flush()
    audit(
        request,
        actor=actor,
        action="donors.created",
        entity_type="donor",
        entity_id=donor.id,
        new_values=donor_data(donor),
    )
    commit(request)
    return success_response(donor_data(donor), status=201)


def donor_get_view(request):
    """Return one active donor."""
    require_permission(request, "donors.read")
    return success_response(donor_data(_donor(request, request.matchdict["donor_id"])))


def donor_patch_view(request):
    """Patch a donor and record its before/after values."""
    actor = require_permission(request, "donors.update")
    donor = _donor(request, request.matchdict["donor_id"])
    data = validate_json_body(request, DonorPatchRequest)
    old_values = donor_data(donor)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(donor, field, value)
    audit(
        request,
        actor=actor,
        action="donors.updated",
        entity_type="donor",
        entity_id=donor.id,
        old_values=old_values,
        new_values=donor_data(donor),
    )
    commit(request)
    return success_response(donor_data(donor))


def donor_delete_view(request):
    """Soft-delete a donor while preserving historic ownership records."""
    actor = require_permission(request, "donors.delete")
    donor = _donor(request, request.matchdict["donor_id"])
    donor.deleted_at = utcnow()
    audit(
        request,
        actor=actor,
        action="donors.deleted",
        entity_type="donor",
        entity_id=donor.id,
        old_values={"deleted_at": None},
        new_values={"deleted_at": donor.deleted_at},
    )
    commit(request)
    return success_response({"deleted": True, "id": donor.id})


def donor_palms_view(request):
    """List an active donor's active palms without per-row relationship queries."""
    require_permission(request, "palms.read")
    donor = _donor(request, request.matchdict["donor_id"])
    page, page_size, sort, descending = parse_page(
        request, {"created_at", "updated_at", "code", "plantation_date", "status"}
    )
    statement = _palm_query(request, donor_id=donor.id)
    total = request.dbsession.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    column = getattr(Palm, sort)
    palms = list(
        request.dbsession.scalars(
            statement.order_by(column.desc() if descending else column.asc(), Palm.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return success_response(
        page_payload([palm_data(palm) for palm in palms], page=page, page_size=page_size, total=total)
    )


def sections_list_view(request):
    """List sections with portable filtering, sorting, pagination, and palm counts."""
    require_permission(request, "sections.read")
    page, page_size, sort, descending = parse_page(
        request, {"created_at", "updated_at", "name", "location_name"}
    )
    count_subquery = (
        select(func.count(Palm.id))
        .where(Palm.section_id == Section.id, Palm.deleted_at.is_(None))
        .correlate(Section)
        .scalar_subquery()
        .label("palm_count")
    )
    filters = [Section.deleted_at.is_(None)]
    query = request.params.get("query", "").strip()
    if query:
        pattern = f"%{query}%"
        filters.append(or_(Section.name.ilike(pattern), Section.location_name.ilike(pattern)))
    total = request.dbsession.scalar(select(func.count(Section.id)).where(*filters)) or 0
    column = getattr(Section, sort)
    rows = request.dbsession.execute(
        select(Section, count_subquery)
        .where(*filters)
        .order_by(column.desc() if descending else column.asc(), Section.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return success_response(
        page_payload(
            [section_data(section, palm_count=palm_count) for section, palm_count in rows],
            page=page,
            page_size=page_size,
            total=total,
        )
    )


def section_create_view(request):
    """Create a section."""
    actor = require_permission(request, "sections.create")
    data = validate_json_body(request, SectionCreateRequest)
    section = Section(**data.model_dump())
    request.dbsession.add(section)
    request.dbsession.flush()
    audit(
        request,
        actor=actor,
        action="sections.created",
        entity_type="section",
        entity_id=section.id,
        new_values=section_data(section),
    )
    commit(request)
    return success_response(section_data(section), status=201)


def section_get_view(request):
    """Return one active section."""
    require_permission(request, "sections.read")
    return success_response(section_data(_section(request, request.matchdict["section_id"])))


def section_patch_view(request):
    """Patch a section excluding later storage-backed image operations."""
    actor = require_permission(request, "sections.update")
    section = _section(request, request.matchdict["section_id"])
    data = validate_json_body(request, SectionPatchRequest)
    old_values = section_data(section)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(section, field, value)
    audit(
        request,
        actor=actor,
        action="sections.updated",
        entity_type="section",
        entity_id=section.id,
        old_values=old_values,
        new_values=section_data(section),
    )
    commit(request)
    return success_response(section_data(section))


def section_delete_view(request):
    """Soft-delete a section after atomically reassigning all active palms."""
    actor = require_permission(request, "sections.delete")
    section = _section(request, request.matchdict["section_id"])
    existing_palm_count = request.dbsession.scalar(
        select(func.count(Palm.id)).where(
            Palm.section_id == section.id, Palm.deleted_at.is_(None)
        )
    ) or 0
    replacement_id = request.params.get("reassign_to_section_id")
    replacement = None
    if existing_palm_count:
        if not replacement_id:
            raise conflict("Palms must be reassigned before this section can be deleted.")
        replacement = _section(request, replacement_id)
        if replacement.id == section.id:
            raise APIError(
                status=422,
                code="validation_error",
                message="Request validation failed.",
                details=[
                    {
                        "field": "reassign_to_section_id",
                        "code": "value_error",
                        "message": "A section cannot be reassigned to itself.",
                    }
                ],
            )
        request.dbsession.execute(
            update(Palm)
            .where(Palm.section_id == section.id, Palm.deleted_at.is_(None))
            .values(section_id=replacement.id, updated_at=utcnow())
        )
    section.deleted_at = utcnow()
    audit(
        request,
        actor=actor,
        action="sections.deleted",
        entity_type="section",
        entity_id=section.id,
        old_values={"deleted_at": None, "active_palm_count": existing_palm_count},
        new_values={
            "deleted_at": section.deleted_at,
            "reassigned_to_section_id": replacement.id if replacement else None,
        },
    )
    commit(request)
    return success_response(
        {
            "deleted": True,
            "id": section.id,
            "reassigned_palm_count": existing_palm_count,
            "reassigned_to_section_id": replacement.id if replacement else None,
        }
    )


def palms_list_view(request):
    """List active palms with filters, search, sorting, and eager owner loading."""
    require_permission(request, "palms.read")
    page, page_size, sort, descending = parse_page(
        request, {"created_at", "updated_at", "code", "plantation_date", "status"}
    )
    statement = _palm_query(request)
    query = request.params.get("query", "").strip()
    if query:
        pattern = f"%{query}%"
        statement = statement.where(
            or_(
                Palm.code.ilike(pattern),
                Donor.full_name.ilike(pattern),
                Donor.phone.ilike(pattern),
            )
        )
    if raw_donor_id := request.params.get("donor_id"):
        statement = statement.where(Palm.donor_id == parse_uuid(raw_donor_id, field="donor_id"))
    if raw_section_id := request.params.get("section_id"):
        statement = statement.where(
            Palm.section_id == parse_uuid(raw_section_id, field="section_id")
        )
    if status := request.params.get("status"):
        statement = statement.where(Palm.status == status)
    if health := request.params.get("health_status"):
        statement = statement.where(Palm.current_health_status == health)
    total = request.dbsession.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    column = getattr(Palm, sort)
    palms = list(
        request.dbsession.scalars(
            statement.order_by(column.desc() if descending else column.asc(), Palm.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return success_response(
        page_payload([palm_data(palm) for palm in palms], page=page, page_size=page_size, total=total)
    )


def palm_create_view(request):
    """Create a palm only for active donor and section owners."""
    actor = require_permission(request, "palms.create")
    data = validate_json_body(request, PalmCreateRequest)
    _ensure_palm_owners(request, donor_id=data.donor_id, section_id=data.section_id)
    existing = request.dbsession.scalar(select(Palm.id).where(Palm.code == data.code))
    if existing is not None:
        raise conflict("A palm with that code already exists.")
    palm = Palm(**data.model_dump())
    request.dbsession.add(palm)
    request.dbsession.flush()
    palm = request.dbsession.scalar(
        select(Palm)
        .options(joinedload(Palm.donor), joinedload(Palm.section))
        .where(Palm.id == palm.id)
    )
    audit(
        request,
        actor=actor,
        action="palms.created",
        entity_type="palm",
        entity_id=palm.id,
        new_values=palm_data(palm),
    )
    commit(request)
    return success_response(palm_data(palm), status=201)


def palm_get_view(request):
    """Return one palm with its history and hierarchy relationships preloaded."""
    require_permission(request, "palms.read")
    return success_response(palm_data(_palm(request, request.matchdict["palm_id"], detail=True), detail=True))


def palm_patch_view(request):
    """Patch a palm while checking changed donor/section ownership."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    data = validate_json_body(request, PalmPatchRequest)
    fields = data.model_dump(exclude_unset=True)
    if "code" in fields and fields["code"] != palm.code:
        existing = request.dbsession.scalar(select(Palm.id).where(Palm.code == fields["code"]))
        if existing is not None:
            raise conflict("A palm with that code already exists.")
    donor_id = fields.get("donor_id", palm.donor_id)
    section_id = fields.get("section_id", palm.section_id)
    _ensure_palm_owners(request, donor_id=donor_id, section_id=section_id)
    old_values = palm_data(palm)
    for field, value in fields.items():
        setattr(palm, field, value)
    audit(
        request,
        actor=actor,
        action="palms.updated",
        entity_type="palm",
        entity_id=palm.id,
        old_values=old_values,
        new_values={
            "code": palm.code,
            "donor_id": palm.donor_id,
            "section_id": palm.section_id,
            "status": palm.status,
            "current_health_status": palm.current_health_status,
        },
    )
    commit(request)
    return success_response(palm_data(palm))


def palm_delete_view(request):
    """Soft-delete one palm."""
    actor = require_permission(request, "palms.delete")
    palm = _palm(request, request.matchdict["palm_id"])
    palm.deleted_at = utcnow()
    audit(
        request,
        actor=actor,
        action="palms.deleted",
        entity_type="palm",
        entity_id=palm.id,
        old_values={"deleted_at": None},
        new_values={"deleted_at": palm.deleted_at},
    )
    commit(request)
    return success_response({"deleted": True, "id": palm.id})


def _bulk_active_palms(request, palm_ids):
    palms = list(
        request.dbsession.scalars(
            select(Palm).where(Palm.id.in_(palm_ids), Palm.deleted_at.is_(None))
        )
    )
    if len(palms) != len(palm_ids):
        raise not_found()
    return palms


def palm_bulk_delete_view(request):
    """Soft-delete a validated set of palms in one transaction."""
    actor = require_permission(request, "palms.delete")
    data = validate_json_body(request, BulkPalmIdsRequest)
    palms = _bulk_active_palms(request, data.palm_ids)
    deleted_at = utcnow()
    for palm in palms:
        palm.deleted_at = deleted_at
        audit(
            request,
            actor=actor,
            action="palms.deleted",
            entity_type="palm",
            entity_id=palm.id,
            old_values={"deleted_at": None, "bulk": True},
            new_values={"deleted_at": deleted_at, "bulk": True},
        )
    commit(request)
    return success_response({"deleted_count": len(palms)})


def palm_bulk_update_section_view(request):
    """Reassign an explicitly validated set of palms to an active section."""
    actor = require_permission(request, "palms.bulk_update")
    data = validate_json_body(request, BulkPalmSectionRequest)
    section = get_active(request.dbsession, Section, data.section_id)
    palms = _bulk_active_palms(request, data.palm_ids)
    for palm in palms:
        old_section_id = palm.section_id
        palm.section_id = section.id
        audit(
            request,
            actor=actor,
            action="palms.section_reassigned",
            entity_type="palm",
            entity_id=palm.id,
            old_values={"section_id": old_section_id, "bulk": True},
            new_values={"section_id": section.id, "bulk": True},
        )
    commit(request)
    return success_response({"updated_count": len(palms), "section_id": section.id})


def _harvest(request, palm: Palm, raw_id: str) -> HarvestRecord:
    record = request.dbsession.scalar(
        select(HarvestRecord).where(
            HarvestRecord.id == parse_uuid(raw_id, field="harvest_id"),
            HarvestRecord.palm_id == palm.id,
        )
    )
    if record is None:
        raise not_found()
    return record


def harvest_create_view(request):
    """Create a harvest record for one palm."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    data = validate_json_body(request, HarvestCreateRequest)
    record = HarvestRecord(
        palm_id=palm.id, created_by_user_id=actor.id, **data.model_dump()
    )
    request.dbsession.add(record)
    request.dbsession.flush()
    audit(
        request,
        actor=actor,
        action="harvests.created",
        entity_type="harvest_record",
        entity_id=record.id,
        new_values=harvest_data(record),
    )
    commit(request)
    return success_response(harvest_data(record), status=201)


def harvest_patch_view(request):
    """Update a harvest record that belongs to the requested palm."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    record = _harvest(request, palm, request.matchdict["harvest_id"])
    data = validate_json_body(request, HarvestPatchRequest)
    old_values = harvest_data(record)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    audit(
        request,
        actor=actor,
        action="harvests.updated",
        entity_type="harvest_record",
        entity_id=record.id,
        old_values=old_values,
        new_values=harvest_data(record),
    )
    commit(request)
    return success_response(harvest_data(record))


def harvest_delete_view(request):
    """Hard-delete a mutable harvest record and retain its audit event."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    record = _harvest(request, palm, request.matchdict["harvest_id"])
    snapshot = harvest_data(record)
    request.dbsession.delete(record)
    audit(
        request,
        actor=actor,
        action="harvests.deleted",
        entity_type="harvest_record",
        entity_id=record.id,
        old_values=snapshot,
    )
    commit(request)
    return success_response({"deleted": True, "id": record.id})


def _disease(request, palm: Palm, raw_id: str, *, with_treatments: bool = False) -> DiseaseRecord:
    statement = select(DiseaseRecord).where(
        DiseaseRecord.id == parse_uuid(raw_id, field="disease_id"),
        DiseaseRecord.palm_id == palm.id,
    )
    if with_treatments:
        statement = statement.options(selectinload(DiseaseRecord.treatments))
    record = request.dbsession.scalar(statement)
    if record is None:
        raise not_found()
    return record


def disease_create_view(request):
    """Create a disease record for one palm."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    data = validate_json_body(request, DiseaseCreateRequest)
    record = DiseaseRecord(
        palm_id=palm.id, created_by_user_id=actor.id, **data.model_dump()
    )
    request.dbsession.add(record)
    request.dbsession.flush()
    audit(
        request,
        actor=actor,
        action="diseases.created",
        entity_type="disease_record",
        entity_id=record.id,
        new_values=disease_data(record),
    )
    commit(request)
    return success_response(disease_data(record), status=201)


def disease_patch_view(request):
    """Update a disease record owned by the requested palm."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    record = _disease(request, palm, request.matchdict["disease_id"])
    data = validate_json_body(request, DiseasePatchRequest)
    old_values = disease_data(record)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    audit(
        request,
        actor=actor,
        action="diseases.updated",
        entity_type="disease_record",
        entity_id=record.id,
        old_values=old_values,
        new_values=disease_data(record),
    )
    commit(request)
    return success_response(disease_data(record))


def disease_delete_view(request):
    """Hard-delete a disease and cascading treatment records, with audit history."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    record = _disease(request, palm, request.matchdict["disease_id"], with_treatments=True)
    snapshot = disease_data(record, include_treatments=True)
    request.dbsession.delete(record)
    audit(
        request,
        actor=actor,
        action="diseases.deleted",
        entity_type="disease_record",
        entity_id=record.id,
        old_values=snapshot,
    )
    commit(request)
    return success_response({"deleted": True, "id": record.id})


def _treatment(request, disease: DiseaseRecord, raw_id: str) -> TreatmentRecord:
    record = request.dbsession.scalar(
        select(TreatmentRecord).where(
            TreatmentRecord.id == parse_uuid(raw_id, field="treatment_id"),
            TreatmentRecord.disease_record_id == disease.id,
        )
    )
    if record is None:
        raise not_found()
    return record


def treatment_create_view(request):
    """Create treatment history under a disease record owned by the palm."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    disease = _disease(request, palm, request.matchdict["disease_id"])
    data = validate_json_body(request, TreatmentCreateRequest)
    record = TreatmentRecord(
        disease_record_id=disease.id, created_by_user_id=actor.id, **data.model_dump()
    )
    request.dbsession.add(record)
    request.dbsession.flush()
    audit(
        request,
        actor=actor,
        action="treatments.created",
        entity_type="treatment_record",
        entity_id=record.id,
        new_values=treatment_data(record),
    )
    commit(request)
    return success_response(treatment_data(record), status=201)


def treatment_patch_view(request):
    """Update treatment history under the requested disease and palm."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    disease = _disease(request, palm, request.matchdict["disease_id"])
    record = _treatment(request, disease, request.matchdict["treatment_id"])
    data = validate_json_body(request, TreatmentPatchRequest)
    old_values = treatment_data(record)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    audit(
        request,
        actor=actor,
        action="treatments.updated",
        entity_type="treatment_record",
        entity_id=record.id,
        old_values=old_values,
        new_values=treatment_data(record),
    )
    commit(request)
    return success_response(treatment_data(record))


def treatment_delete_view(request):
    """Delete one treatment record within the requested disease hierarchy."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    disease = _disease(request, palm, request.matchdict["disease_id"])
    record = _treatment(request, disease, request.matchdict["treatment_id"])
    snapshot = treatment_data(record)
    request.dbsession.delete(record)
    audit(
        request,
        actor=actor,
        action="treatments.deleted",
        entity_type="treatment_record",
        entity_id=record.id,
        old_values=snapshot,
    )
    commit(request)
    return success_response({"deleted": True, "id": record.id})


def _note(request, palm: Palm, raw_id: str) -> PalmNote:
    record = request.dbsession.scalar(
        select(PalmNote).where(
            PalmNote.id == parse_uuid(raw_id, field="note_id"), PalmNote.palm_id == palm.id
        )
    )
    if record is None:
        raise not_found()
    return record


def note_create_view(request):
    """Create a palm note."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    data = validate_json_body(request, PalmNoteCreateRequest)
    record = PalmNote(palm_id=palm.id, created_by_user_id=actor.id, **data.model_dump())
    request.dbsession.add(record)
    request.dbsession.flush()
    audit(
        request,
        actor=actor,
        action="palm_notes.created",
        entity_type="palm_note",
        entity_id=record.id,
        new_values=note_data(record),
    )
    commit(request)
    return success_response(note_data(record), status=201)


def note_delete_view(request):
    """Delete a palm note while retaining the historical audit entry."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    record = _note(request, palm, request.matchdict["note_id"])
    snapshot = note_data(record)
    request.dbsession.delete(record)
    audit(
        request,
        actor=actor,
        action="palm_notes.deleted",
        entity_type="palm_note",
        entity_id=record.id,
        old_values=snapshot,
    )
    commit(request)
    return success_response({"deleted": True, "id": record.id})


def relationship_create_view(request):
    """Link a palm to a distinct active child palm."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    data = validate_json_body(request, PalmRelationshipCreateRequest)
    child = get_active(request.dbsession, Palm, data.child_palm_id)
    if child.id == palm.id:
        raise APIError(
            status=422,
            code="validation_error",
            message="Request validation failed.",
            details=[
                {
                    "field": "child_palm_id",
                    "code": "value_error",
                    "message": "A palm cannot be its own child.",
                }
            ],
        )
    existing = request.dbsession.scalar(
        select(PalmRelationship.id).where(
            PalmRelationship.parent_palm_id == palm.id,
            PalmRelationship.child_palm_id == child.id,
        )
    )
    if existing is not None:
        raise conflict("This palm relationship already exists.")
    record = PalmRelationship(
        parent_palm_id=palm.id,
        child_palm_id=child.id,
        relationship_type=data.relationship_type,
    )
    request.dbsession.add(record)
    request.dbsession.flush()
    audit(
        request,
        actor=actor,
        action="palm_relationships.created",
        entity_type="palm_relationship",
        entity_id=record.id,
        new_values={
            "parent_palm_id": palm.id,
            "child_palm_id": child.id,
            "relationship_type": record.relationship_type,
        },
    )
    commit(request)
    return success_response(
        {
            "id": record.id,
            "parent_palm_id": palm.id,
            "child_palm_id": child.id,
            "relationship_type": record.relationship_type,
            "created_at": record.created_at,
        },
        status=201,
    )


def relationship_delete_view(request):
    """Delete a parent/child relationship attached to the requested parent palm."""
    actor = require_permission(request, "palms.update")
    palm = _palm(request, request.matchdict["palm_id"])
    relationship_id = parse_uuid(request.matchdict["relationship_id"], field="relationship_id")
    record = request.dbsession.scalar(
        select(PalmRelationship).where(
            PalmRelationship.id == relationship_id,
            PalmRelationship.parent_palm_id == palm.id,
        )
    )
    if record is None:
        raise not_found()
    snapshot = {
        "parent_palm_id": record.parent_palm_id,
        "child_palm_id": record.child_palm_id,
        "relationship_type": record.relationship_type,
    }
    request.dbsession.delete(record)
    audit(
        request,
        actor=actor,
        action="palm_relationships.deleted",
        entity_type="palm_relationship",
        entity_id=record.id,
        old_values=snapshot,
    )
    commit(request)
    return success_response({"deleted": True, "id": record.id})

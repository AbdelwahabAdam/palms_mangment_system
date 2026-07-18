"""Shared authentication, authorization, audit, query, and serialization helpers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
import json
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from palms_api.config import Settings
from palms_api.errors import APIError
from palms_api.models import (
    AuditLog,
    DiseaseRecord,
    Donor,
    HarvestRecord,
    Palm,
    PalmImage,
    PalmNote,
    PalmRelationship,
    Permission,
    RolePermission,
    Section,
    TreatmentRecord,
    TwoFactorSetting,
    User,
    UserPermissionOverride,
    UserSession,
    utcnow,
)
from palms_api.security import new_opaque_token, token_digest
from palms_api.responses import json_default

ModelT = TypeVar("ModelT")


def not_found(resource: str = "The requested resource was not found.") -> APIError:
    """Create a standard, non-enumerating missing-resource response."""
    return APIError(status=404, code="not_found", message=resource)


def conflict(message: str) -> APIError:
    """Create a standard conflict response."""
    return APIError(status=409, code="conflict", message=message)


def parse_uuid(value: str, *, field: str = "id") -> UUID:
    """Parse route/query UUIDs into a safely reported validation failure."""
    try:
        return UUID(value)
    except (TypeError, ValueError) as error:
        raise APIError(
            status=422,
            code="validation_error",
            message="Request validation failed.",
            details=[{"field": field, "code": "uuid_parsing", "message": "Must be a UUID."}],
        ) from error


def request_actor(request: Any) -> User:
    """Load the active user represented by the server-side opaque session cookie."""
    cached = getattr(request, "_palms_current_user", None)
    if cached is not None:
        return cached

    settings: Settings = request.registry.palms_settings
    cookie = request.cookies.get(settings.session_cookie_name)
    if not cookie:
        raise APIError(status=401, code="unauthorized", message="Authentication is required.")

    db: Session = request.dbsession
    now = utcnow()
    session = db.scalar(
        select(UserSession)
        .options(joinedload(UserSession.user).joinedload(User.role))
        .where(
            UserSession.token_hash == token_digest(cookie),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )
    if session is None or not session.user.is_active or session.user.deleted_at is not None:
        raise APIError(status=401, code="unauthorized", message="Authentication is required.")

    request._palms_current_user = session.user
    request._palms_current_session = session
    return session.user


def permissions_for_user(db: Session, user: User) -> set[str]:
    """Resolve role permissions and per-user allow/deny overrides."""
    role_permissions = set(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == user.role_id)
        )
    )
    overrides = db.execute(
        select(Permission.code, UserPermissionOverride.is_allowed)
        .join(Permission, Permission.id == UserPermissionOverride.permission_id)
        .where(UserPermissionOverride.user_id == user.id)
    )
    for code, allowed in overrides:
        if allowed:
            role_permissions.add(code)
        else:
            role_permissions.discard(code)
    return role_permissions


def require_permission(request: Any, permission: str) -> User:
    """Authenticate a user and enforce one granular permission."""
    user = request_actor(request)
    if permission not in permissions_for_user(request.dbsession, user):
        raise APIError(
            status=403,
            code="forbidden",
            message="You do not have permission to access this resource.",
        )
    return user


def require_super_admin(request: Any) -> User:
    """Restrict sensitive user administration to the system Super Admin role."""
    user = request_actor(request)
    if user.role.name != "Super Admin":
        raise APIError(
            status=403,
            code="forbidden",
            message="You do not have permission to access this resource.",
        )
    return user


def create_user_session(request: Any, user: User) -> str:
    """Persist an opaque durable session and return its cookie value."""
    settings: Settings = request.registry.palms_settings
    raw_token = new_opaque_token()
    request.dbsession.add(
        UserSession(
            user_id=user.id,
            token_hash=token_digest(raw_token),
            expires_at=utcnow() + timedelta(minutes=settings.session_timeout_minutes),
            ip_address=request.client_addr,
            user_agent=request.headers.get("User-Agent", "")[:512] or None,
        )
    )
    return raw_token


def revoke_user_sessions(db: Session, user_id: UUID, *, except_session_id: UUID | None = None) -> None:
    """Revoke all active sessions, optionally preserving the current one."""
    statement = (
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    if except_session_id is not None:
        statement = statement.where(UserSession.id != except_session_id)
    db.execute(statement)


def set_session_cookie(response: Any, request: Any, token: str) -> None:
    """Issue a restrictive session cookie that contains no user data."""
    settings: Settings = request.registry.palms_settings
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_timeout_minutes * 60,
        path="/",
        secure=settings.use_secure_session_cookie,
        httponly=True,
        samesite="Lax",
    )


def clear_session_cookie(response: Any, request: Any) -> None:
    """Expire the browser cookie after server-side session revocation."""
    response.delete_cookie(
        request.registry.palms_settings.session_cookie_name,
        path="/",
    )


def audit(
    request: Any,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
) -> None:
    """Append a mutation audit record; callers must not pass secret fields."""
    request.dbsession.add(
        AuditLog(
            actor_user_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values_json=_json_safe(old_values),
            new_values_json=_json_safe(new_values),
            ip_address=request.client_addr,
            user_agent=request.headers.get("User-Agent", "")[:512] or None,
        )
    )


def _json_safe(value: dict[str, Any] | None) -> dict[str, Any] | None:
    """Normalize UUID, decimal, and temporal values before database JSON storage."""
    if value is None:
        return None
    return json.loads(json.dumps(value, default=json_default, allow_nan=False))


def commit(request: Any) -> None:
    """Commit an API transaction, mapping database uniqueness races to 409."""
    try:
        request.dbsession.commit()
    except IntegrityError as error:
        request.dbsession.rollback()
        raise conflict("The requested change conflicts with existing data.") from error


def get_active(
    db: Session,
    model: type[ModelT],
    identifier: UUID,
    *,
    options: Iterable[Any] = (),
) -> ModelT:
    """Return an entity that has not been soft-deleted."""
    statement: Select[tuple[ModelT]] = select(model).where(model.id == identifier)  # type: ignore[attr-defined]
    for option in options:
        statement = statement.options(option)
    if hasattr(model, "deleted_at"):
        statement = statement.where(model.deleted_at.is_(None))  # type: ignore[attr-defined]
    entity = db.scalar(statement)
    if entity is None:
        raise not_found()
    return entity


def parse_page(request: Any, allowed_sorts: set[str]) -> tuple[int, int, str, bool]:
    """Validate shared list pagination and sort controls."""
    raw_page = request.params.get("page", "1")
    raw_page_size = request.params.get("page_size", "25")
    try:
        page, page_size = int(raw_page), int(raw_page_size)
    except ValueError as error:
        raise APIError(
            status=422,
            code="validation_error",
            message="Request validation failed.",
            details=[{"field": "page", "code": "int_parsing", "message": "Must be an integer."}],
        ) from error
    if page < 1 or page_size < 1 or page_size > 100:
        raise APIError(
            status=422,
            code="validation_error",
            message="Request validation failed.",
            details=[
                {
                    "field": "page/page_size",
                    "code": "range",
                    "message": "page must be positive and page_size must be 1 through 100.",
                }
            ],
        )
    sort = request.params.get("sort", "created_at")
    if sort not in allowed_sorts:
        raise APIError(
            status=422,
            code="validation_error",
            message="Request validation failed.",
            details=[{"field": "sort", "code": "value_error", "message": "Unsupported sort field."}],
        )
    descending = request.params.get("order", "desc").lower() != "asc"
    if request.params.get("order", "desc").lower() not in {"asc", "desc"}:
        raise APIError(
            status=422,
            code="validation_error",
            message="Request validation failed.",
            details=[{"field": "order", "code": "value_error", "message": "Use asc or desc."}],
        )
    return page, page_size, sort, descending


def page_payload(items: list[dict[str, Any]], *, page: int, page_size: int, total: int) -> dict[str, Any]:
    """Wrap deterministic pagination metadata in the standard response data."""
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


def user_data(user: User, *, include_permissions: set[str] | None = None) -> dict[str, Any]:
    """Serialize a user without password hashes, reset tokens, or sessions."""
    payload: dict[str, Any] = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "role": {"id": user.role.id, "name": user.role.name},
        "last_login_at": user.last_login_at,
        "avatar_url": user.avatar_url,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
    if include_permissions is not None:
        payload["permissions"] = sorted(include_permissions)
    return payload


def donor_data(donor: Donor, *, palm_count: int | None = None) -> dict[str, Any]:
    """Serialize a donor and optional aggregated palm count."""
    payload: dict[str, Any] = {
        "id": donor.id,
        "full_name": donor.full_name,
        "phone": donor.phone,
        "email": donor.email,
        "address": donor.address,
        "donation_date": donor.donation_date,
        "notes": donor.notes,
        "created_at": donor.created_at,
        "updated_at": donor.updated_at,
    }
    if palm_count is not None:
        payload["palm_count"] = palm_count
    return payload


def section_data(section: Section, *, palm_count: int | None = None) -> dict[str, Any]:
    """Serialize a section without storage-backed image behaviour."""
    payload: dict[str, Any] = {
        "id": section.id,
        "name": section.name,
        "description": section.description,
        "location_name": section.location_name,
        "soil_type": section.soil_type,
        "irrigation_type": section.irrigation_type,
        "gps_latitude": section.gps_latitude,
        "gps_longitude": section.gps_longitude,
        "image_url": section.image_url,
        "created_at": section.created_at,
        "updated_at": section.updated_at,
    }
    if palm_count is not None:
        payload["palm_count"] = palm_count
    return payload


def harvest_data(record: HarvestRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "harvest_date": record.harvest_date,
        "amount": record.amount,
        "unit": record.unit,
        "revenue": record.revenue,
        "notes": record.notes,
        "created_by_user_id": record.created_by_user_id,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def treatment_data(record: TreatmentRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "treatment_name": record.treatment_name,
        "treatment_date": record.treatment_date,
        "notes": record.notes,
        "created_by_user_id": record.created_by_user_id,
        "created_at": record.created_at,
    }


def disease_data(record: DiseaseRecord, *, include_treatments: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": record.id,
        "disease_name": record.disease_name,
        "detected_at": record.detected_at,
        "status": record.status,
        "notes": record.notes,
        "created_by_user_id": record.created_by_user_id,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
    if include_treatments:
        payload["treatments"] = [treatment_data(item) for item in record.treatments]
    return payload


def note_data(note: PalmNote) -> dict[str, Any]:
    return {
        "id": note.id,
        "body": note.body,
        "created_by_user_id": note.created_by_user_id,
        "created_at": note.created_at,
    }


def relationship_data(relationship: PalmRelationship, *, direction: str) -> dict[str, Any]:
    related = relationship.child if direction == "child" else relationship.parent
    return {
        "id": relationship.id,
        "relationship_type": relationship.relationship_type,
        f"{direction}_palm": {"id": related.id, "code": related.code},
        "created_at": relationship.created_at,
    }


def palm_data(palm: Palm, *, detail: bool = False) -> dict[str, Any]:
    """Serialize a palm whose required relationships have been eagerly loaded."""
    payload: dict[str, Any] = {
        "id": palm.id,
        "code": palm.code,
        "donor_id": palm.donor_id,
        "section_id": palm.section_id,
        "plantation_date": palm.plantation_date,
        "status": palm.status,
        "current_health_status": palm.current_health_status,
        "description": palm.description,
        "created_at": palm.created_at,
        "updated_at": palm.updated_at,
        "donor": {"id": palm.donor.id, "full_name": palm.donor.full_name} if palm.donor else None,
        "section": {"id": palm.section.id, "name": palm.section.name} if palm.section else None,
    }
    if detail:
        payload.update(
            {
                "harvests": [harvest_data(item) for item in palm.harvests],
                "diseases": [disease_data(item, include_treatments=True) for item in palm.diseases],
                "notes": [note_data(item) for item in palm.notes],
                "children": [relationship_data(item, direction="child") for item in palm.parent_relationships],
                "parents": [relationship_data(item, direction="parent") for item in palm.child_relationships],
                "images": [
                    {
                        "id": image.id,
                        "thumbnail_url": image.thumbnail_url,
                        "medium_url": image.medium_url,
                        "full_url": image.full_url,
                        "webp_url": image.webp_url,
                        "uploaded_at": image.uploaded_at,
                    }
                    for image in palm.images
                ],
            }
        )
    return payload


def audit_data(log: AuditLog) -> dict[str, Any]:
    """Serialize audit events without reconstructing any sensitive source values."""
    return {
        "id": log.id,
        "actor_user_id": log.actor_user_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "old_values": log.old_values_json,
        "new_values": log.new_values_json,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "created_at": log.created_at,
    }


def two_factor_data(setting: TwoFactorSetting | None) -> dict[str, Any]:
    """Return only 2FA enablement state; no secrets are persisted or exposed."""
    return {"enabled": bool(setting and setting.is_enabled), "mode": "placeholder"}



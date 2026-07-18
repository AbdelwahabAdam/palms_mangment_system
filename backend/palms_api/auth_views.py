"""Authentication, profile, and Super Admin user-management API endpoints."""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from palms_api.errors import APIError
from palms_api.models import (
    AuditLog,
    PasswordResetToken,
    Permission,
    Role,
    TwoFactorSetting,
    User,
    UserInvitation,
    UserPermissionOverride,
    utcnow,
)
from palms_api.responses import success_response
from palms_api.schemas import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    InviteUserRequest,
    LoginRequest,
    ProfilePatchRequest,
    ResetPasswordRequest,
    UserPatchRequest,
)
from palms_api.security import hash_password, new_opaque_token, token_digest, verify_password
from palms_api.services import (
    audit,
    audit_data,
    clear_session_cookie,
    commit,
    conflict,
    create_user_session,
    get_active,
    not_found,
    page_payload,
    parse_page,
    parse_uuid,
    permissions_for_user,
    request_actor,
    require_super_admin,
    revoke_user_sessions,
    set_session_cookie,
    two_factor_data,
    user_data,
)
from palms_api.validation import validate_json_body


def _user_snapshot(user: User) -> dict[str, object]:
    """Audit only safe user attributes."""
    return {
        "email": user.email,
        "full_name": user.full_name,
        "role_id": user.role_id,
        "is_active": user.is_active,
    }


def _find_user_by_email(request, email: str) -> User | None:
    return request.dbsession.scalar(
        select(User)
        .options(joinedload(User.role))
        .where(User.email == email, User.deleted_at.is_(None))
    )


def _get_user(request, raw_id: str) -> User:
    return get_active(request.dbsession, User, parse_uuid(raw_id, field="user_id"), options=[joinedload(User.role)])


def login_view(request):
    """Authenticate credentials and create an opaque, durable server-side session."""
    data = validate_json_body(request, LoginRequest)
    user = _find_user_by_email(request, data.email)
    if user is None or not user.is_active or not verify_password(user.password_hash, data.password):
        raise APIError(
            status=401,
            code="invalid_credentials",
            message="Invalid email or password.",
        )

    user.last_login_at = utcnow()
    raw_token = create_user_session(request, user)
    audit(
        request,
        actor=user,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        new_values={"session_created": True},
    )
    commit(request)
    response = success_response({"user": user_data(user, include_permissions=permissions_for_user(request.dbsession, user))})
    set_session_cookie(response, request, raw_token)
    return response


def logout_view(request):
    """Revoke the current server-side session and clear the browser cookie."""
    user = request_actor(request)
    current_session = request._palms_current_session
    current_session.revoked_at = utcnow()
    audit(
        request,
        actor=user,
        action="auth.logout",
        entity_type="user_session",
        entity_id=current_session.id,
    )
    commit(request)
    response = success_response({"logged_out": True})
    clear_session_cookie(response, request)
    return response


def me_view(request):
    """Return the authenticated user's safe profile and effective permissions."""
    user = request_actor(request)
    setting = request.dbsession.scalar(
        select(TwoFactorSetting).where(TwoFactorSetting.user_id == user.id)
    )
    data = user_data(user, include_permissions=permissions_for_user(request.dbsession, user))
    data["two_factor"] = two_factor_data(setting)
    return success_response(data)


def forgot_password_view(request):
    """Create a one-time reset record while avoiding account enumeration."""
    data = validate_json_body(request, ForgotPasswordRequest)
    user = _find_user_by_email(request, data.email)
    if user is not None and user.is_active:
        raw_token = new_opaque_token()
        request.dbsession.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=token_digest(raw_token),
                expires_at=utcnow()
                + timedelta(minutes=request.registry.palms_settings.password_reset_token_minutes),
            )
        )
        request.registry.palms_email_service.send_password_reset(
            request.dbsession,
            email=user.email,
            full_name=user.full_name,
            token=raw_token,
        )
        audit(
            request,
            actor=None,
            action="auth.password_reset_requested",
            entity_type="user",
            entity_id=user.id,
        )
        commit(request)
    return success_response(
        {"message": "If the account exists, password reset instructions will be sent."}
    )


def reset_password_view(request):
    """Consume a reset token, update the password, and revoke old sessions."""
    data = validate_json_body(request, ResetPasswordRequest)
    record = request.dbsession.scalar(
        select(PasswordResetToken)
        .options(joinedload(PasswordResetToken.user))
        .where(
            PasswordResetToken.token_hash == token_digest(data.token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > utcnow(),
        )
    )
    if record is None or not record.user.is_active or record.user.deleted_at is not None:
        raise APIError(
            status=400,
            code="invalid_reset_token",
            message="The password reset token is invalid or expired.",
        )
    record.user.password_hash = hash_password(data.password)
    record.used_at = utcnow()
    revoke_user_sessions(request.dbsession, record.user_id)
    audit(
        request,
        actor=record.user,
        action="auth.password_reset",
        entity_type="user",
        entity_id=record.user_id,
    )
    commit(request)
    return success_response({"password_reset": True})


def change_password_view(request):
    """Change the current password after re-authentication and end active sessions."""
    user = request_actor(request)
    data = validate_json_body(request, ChangePasswordRequest)
    if not verify_password(user.password_hash, data.current_password):
        raise APIError(
            status=400,
            code="invalid_current_password",
            message="The current password is incorrect.",
        )
    user.password_hash = hash_password(data.new_password)
    revoke_user_sessions(request.dbsession, user.id)
    audit(
        request,
        actor=user,
        action="auth.password_changed",
        entity_type="user",
        entity_id=user.id,
    )
    commit(request)
    response = success_response({"password_changed": True, "reauthentication_required": True})
    clear_session_cookie(response, request)
    return response


def two_factor_enable_view(request):
    """Persist the requested 2FA placeholder state without issuing a secret."""
    user = request_actor(request)
    setting = request.dbsession.scalar(
        select(TwoFactorSetting).where(TwoFactorSetting.user_id == user.id)
    )
    if setting is None:
        setting = TwoFactorSetting(user_id=user.id, is_enabled=True)
        request.dbsession.add(setting)
    else:
        setting.is_enabled = True
    audit(
        request,
        actor=user,
        action="auth.two_factor_enabled",
        entity_type="two_factor_setting",
        entity_id=setting.id,
    )
    commit(request)
    return success_response(two_factor_data(setting))


def two_factor_disable_view(request):
    """Persist disabled placeholder state without retaining an OTP secret."""
    user = request_actor(request)
    setting = request.dbsession.scalar(
        select(TwoFactorSetting).where(TwoFactorSetting.user_id == user.id)
    )
    if setting is None:
        setting = TwoFactorSetting(user_id=user.id, is_enabled=False)
        request.dbsession.add(setting)
    else:
        setting.is_enabled = False
    audit(
        request,
        actor=user,
        action="auth.two_factor_disabled",
        entity_type="two_factor_setting",
        entity_id=setting.id,
    )
    commit(request)
    return success_response(two_factor_data(setting))


def profile_get_view(request):
    """Return the current administrator's profile."""
    return me_view(request)


def profile_patch_view(request):
    """Update the current administrator's safe profile fields."""
    user = request_actor(request)
    data = validate_json_body(request, ProfilePatchRequest)
    old_values = {"full_name": user.full_name}
    if "full_name" in data.model_fields_set:
        user.full_name = data.full_name
    audit(
        request,
        actor=user,
        action="profile.updated",
        entity_type="user",
        entity_id=user.id,
        old_values=old_values,
        new_values={"full_name": user.full_name},
    )
    commit(request)
    return success_response(user_data(user, include_permissions=permissions_for_user(request.dbsession, user)))


def profile_change_password_view(request):
    """Alias profile password changes to the primary authenticated flow."""
    return change_password_view(request)


def profile_change_email_view(request):
    """Change the current email only after verifying the current password."""
    user = request_actor(request)
    data = validate_json_body(request, ChangeEmailRequest)
    if not verify_password(user.password_hash, data.current_password):
        raise APIError(
            status=400,
            code="invalid_current_password",
            message="The current password is incorrect.",
        )
    existing = _find_user_by_email(request, data.new_email)
    if existing is not None and existing.id != user.id:
        raise conflict("An account with that email already exists.")
    old_email = user.email
    user.email = data.new_email
    audit(
        request,
        actor=user,
        action="profile.email_changed",
        entity_type="user",
        entity_id=user.id,
        old_values={"email": old_email},
        new_values={"email": user.email},
    )
    commit(request)
    return success_response(user_data(user, include_permissions=permissions_for_user(request.dbsession, user)))


def users_list_view(request):
    """List non-deleted users for Super Admins with search and pagination."""
    require_super_admin(request)
    page, page_size, sort, descending = parse_page(
        request, {"created_at", "updated_at", "email", "full_name", "last_login_at"}
    )
    statement = (
        select(User)
        .options(joinedload(User.role))
        .where(User.deleted_at.is_(None))
    )
    query = request.params.get("query", "").strip()
    if query:
        pattern = f"%{query}%"
        statement = statement.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
    total = request.dbsession.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    column = getattr(User, sort)
    statement = statement.order_by(column.desc() if descending else column.asc(), User.id)
    users = list(request.dbsession.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
    return success_response(
        page_payload([user_data(user) for user in users], page=page, page_size=page_size, total=total)
    )


def users_invite_view(request):
    """Record a user invitation without returning its one-time secret."""
    actor = require_super_admin(request)
    data = validate_json_body(request, InviteUserRequest)
    role = request.dbsession.get(Role, data.role_id)
    if role is None:
        raise not_found()
    if _find_user_by_email(request, data.email) is not None:
        raise conflict("An account with that email already exists.")
    existing_invite = request.dbsession.scalar(
        select(UserInvitation).where(
            UserInvitation.email == data.email,
            UserInvitation.accepted_at.is_(None),
            UserInvitation.revoked_at.is_(None),
            UserInvitation.expires_at > utcnow(),
        )
    )
    if existing_invite is not None:
        raise conflict("An active invitation for that email already exists.")
    raw_token = new_opaque_token()
    invitation = UserInvitation(
        email=data.email,
        full_name=data.full_name,
        role_id=role.id,
        token_hash=token_digest(raw_token),
        invited_by_user_id=actor.id,
        expires_at=utcnow()
        + timedelta(hours=request.registry.palms_settings.invitation_token_hours),
    )
    request.dbsession.add(invitation)
    request.registry.palms_email_service.send_invitation(
        request.dbsession,
        email=invitation.email,
        full_name=invitation.full_name,
        role_name=role.name,
        token=raw_token,
    )
    audit(
        request,
        actor=actor,
        action="users.invited",
        entity_type="user_invitation",
        entity_id=invitation.id,
        new_values={"email": invitation.email, "role_id": invitation.role_id},
    )
    commit(request)
    return success_response(
        {
            "id": invitation.id,
            "email": invitation.email,
            "full_name": invitation.full_name,
            "role": {"id": role.id, "name": role.name},
            "expires_at": invitation.expires_at,
        },
        status=201,
    )


def user_get_view(request):
    """Get one user for Super Admins."""
    require_super_admin(request)
    return success_response(user_data(_get_user(request, request.matchdict["user_id"])))


def user_patch_view(request):
    """Patch user metadata, role, and explicitly granted/denied permissions."""
    actor = require_super_admin(request)
    user = _get_user(request, request.matchdict["user_id"])
    data = validate_json_body(request, UserPatchRequest)
    old_values = _user_snapshot(user)
    if user.id == actor.id and ({"role_id", "permission_overrides"} & data.model_fields_set):
        raise conflict("You cannot change your own administrative access.")
    if "full_name" in data.model_fields_set:
        user.full_name = data.full_name
    if "role_id" in data.model_fields_set:
        role = request.dbsession.get(Role, data.role_id)
        if role is None:
            raise not_found()
        user.role_id = role.id
        user.role = role
    if data.permission_overrides is not None:
        requested_codes = set(data.permission_overrides)
        permissions = list(
            request.dbsession.scalars(select(Permission).where(Permission.code.in_(requested_codes)))
        )
        by_code = {permission.code: permission for permission in permissions}
        missing = requested_codes - set(by_code)
        if missing:
            raise APIError(
                status=422,
                code="validation_error",
                message="Request validation failed.",
                details=[
                    {
                        "field": "permission_overrides",
                        "code": "value_error",
                        "message": f"Unknown permission: {sorted(missing)[0]}.",
                    }
                ],
            )
        current = {
            override.permission_id: override
            for override in request.dbsession.scalars(
                select(UserPermissionOverride).where(UserPermissionOverride.user_id == user.id)
            )
        }
        for code, allowed in data.permission_overrides.items():
            permission = by_code[code]
            override = current.get(permission.id)
            if override is None:
                request.dbsession.add(
                    UserPermissionOverride(
                        user_id=user.id, permission_id=permission.id, is_allowed=allowed
                    )
                )
            else:
                override.is_allowed = allowed
    audit(
        request,
        actor=actor,
        action="users.updated",
        entity_type="user",
        entity_id=user.id,
        old_values=old_values,
        new_values=_user_snapshot(user),
    )
    commit(request)
    return success_response(user_data(user))


def _prevent_removing_last_super_admin(request, user: User) -> None:
    if user.role.name != "Super Admin":
        return
    remaining = request.dbsession.scalar(
        select(func.count(User.id))
        .join(Role)
        .where(
            Role.name == "Super Admin",
            User.is_active.is_(True),
            User.deleted_at.is_(None),
            User.id != user.id,
        )
    ) or 0
    if remaining == 0:
        raise conflict("The last active Super Admin cannot be disabled.")


def user_disable_view(request):
    """Disable an account and invalidate all of its durable sessions."""
    actor = require_super_admin(request)
    user = _get_user(request, request.matchdict["user_id"])
    if user.id == actor.id:
        raise conflict("You cannot disable your own account.")
    _prevent_removing_last_super_admin(request, user)
    if not user.is_active:
        return success_response(user_data(user))
    old_values = {"is_active": user.is_active}
    user.is_active = False
    revoke_user_sessions(request.dbsession, user.id)
    audit(
        request,
        actor=actor,
        action="users.disabled",
        entity_type="user",
        entity_id=user.id,
        old_values=old_values,
        new_values={"is_active": False},
    )
    commit(request)
    return success_response(user_data(user))


def user_enable_view(request):
    """Re-enable a disabled account without restoring revoked sessions."""
    actor = require_super_admin(request)
    user = _get_user(request, request.matchdict["user_id"])
    if user.is_active:
        return success_response(user_data(user))
    user.is_active = True
    audit(
        request,
        actor=actor,
        action="users.enabled",
        entity_type="user",
        entity_id=user.id,
        old_values={"is_active": False},
        new_values={"is_active": True},
    )
    commit(request)
    return success_response(user_data(user))


def user_reset_password_view(request):
    """Create a reset token record without exposing the secret in the API."""
    actor = require_super_admin(request)
    user = _get_user(request, request.matchdict["user_id"])
    if not user.is_active:
        raise conflict("A disabled user cannot receive a password reset.")
    raw_token = new_opaque_token()
    token = PasswordResetToken(
        user_id=user.id,
        token_hash=token_digest(raw_token),
        expires_at=utcnow()
        + timedelta(minutes=request.registry.palms_settings.password_reset_token_minutes),
    )
    request.dbsession.add(token)
    request.registry.palms_email_service.send_password_reset(
        request.dbsession,
        email=user.email,
        full_name=user.full_name,
        token=raw_token,
    )
    audit(
        request,
        actor=actor,
        action="users.password_reset_requested",
        entity_type="user",
        entity_id=user.id,
    )
    commit(request)
    return success_response({"password_reset_requested": True})


def user_audit_logs_view(request):
    """List the audit events performed by one user."""
    require_super_admin(request)
    user = _get_user(request, request.matchdict["user_id"])
    page, page_size, sort, descending = parse_page(request, {"created_at", "action"})
    statement = select(AuditLog).where(AuditLog.actor_user_id == user.id)
    total = request.dbsession.scalar(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ) or 0
    column = getattr(AuditLog, sort)
    statement = statement.order_by(column.desc() if descending else column.asc(), AuditLog.id)
    logs = list(request.dbsession.scalars(statement.offset((page - 1) * page_size).limit(page_size)))
    return success_response(
        page_payload([audit_data(log) for log in logs], page=page, page_size=page_size, total=total)
    )

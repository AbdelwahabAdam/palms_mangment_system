"""Idempotent system RBAC seed data for tests and local bootstrap scripts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from palms_api.models import Permission, Role, RolePermission

ROLE_DESCRIPTIONS = {
    "Super Admin": "Unrestricted system administrator.",
    "Admin": "Administrator for operational palm data.",
    "Editor": "Editor for operational palm data.",
    "Viewer": "Read-only operational user.",
}

PERMISSION_DESCRIPTIONS = {
    "users.read": "Read users.",
    "users.invite": "Invite users.",
    "users.update": "Update users and overrides.",
    "users.disable": "Enable or disable users.",
    "users.reset_password": "Request user password resets.",
    "donors.read": "Read donors.",
    "donors.create": "Create donors.",
    "donors.update": "Update donors.",
    "donors.delete": "Delete donors.",
    "sections.read": "Read sections.",
    "sections.create": "Create sections.",
    "sections.update": "Update sections.",
    "sections.delete": "Delete sections.",
    "palms.read": "Read palms.",
    "palms.create": "Create palms.",
    "palms.update": "Update palms and their histories.",
    "palms.delete": "Delete palms.",
    "palms.bulk_update": "Bulk reassign palms.",
    "palms.export": "Export palms.",
    "reports.read": "Read reports and report run history.",
    "reports.generate": "Preview and generate reports.",
    "reports.schedule": "Create and manage report schedules.",
    "audit_logs.read": "Read audit logs.",
}


def seed_system_rbac(session: Session) -> None:
    """Create the four system roles, permission catalog, and role grants once."""
    roles = {
        role.name: role
        for role in session.scalars(select(Role).where(Role.name.in_(ROLE_DESCRIPTIONS)))
    }
    for name, description in ROLE_DESCRIPTIONS.items():
        if name not in roles:
            roles[name] = Role(name=name, description=description, is_system=True)
            session.add(roles[name])

    permissions = {
        permission.code: permission
        for permission in session.scalars(
            select(Permission).where(Permission.code.in_(PERMISSION_DESCRIPTIONS))
        )
    }
    for code, description in PERMISSION_DESCRIPTIONS.items():
        if code not in permissions:
            permissions[code] = Permission(code=code, description=description)
            session.add(permissions[code])
    session.flush()

    all_permissions = set(PERMISSION_DESCRIPTIONS)
    grants = {
        "Super Admin": all_permissions,
        "Admin": all_permissions
        - {"users.read", "users.invite", "users.update", "users.disable", "users.reset_password"},
        "Editor": {
            "donors.read",
            "donors.create",
            "donors.update",
            "sections.read",
            "sections.create",
            "sections.update",
            "palms.read",
            "palms.create",
            "palms.update",
            "palms.bulk_update",
            "reports.read",
            "reports.generate",
        },
        "Viewer": {"donors.read", "sections.read", "palms.read"},
    }
    existing_grants = set(
        session.execute(select(RolePermission.role_id, RolePermission.permission_id)).all()
    )
    for role_name, codes in grants.items():
        for code in codes:
            pair = (roles[role_name].id, permissions[code].id)
            if pair not in existing_grants:
                session.add(RolePermission(role_id=pair[0], permission_id=pair[1]))

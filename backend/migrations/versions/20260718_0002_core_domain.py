"""Create the authenticated core donor, section, and palm domain."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260718_0002"
down_revision = "20260718_0001"
branch_labels = None
depends_on = None


def _uuid(name: str):
    return uuid5(NAMESPACE_URL, f"palms-api/{name}")


def upgrade() -> None:
    """Create portable PostgreSQL/SQLite tables and seed system RBAC data."""
    uuid = sa.Uuid(as_uuid=True)
    now = sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "roles",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=255)),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )
    op.create_table(
        "permissions",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", uuid, nullable=False),
        sa.Column("permission_id", uuid, nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_table(
        "users",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role_id", uuid, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("deleted_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_role_id", "users", ["role_id"])
    op.create_table(
        "user_permission_overrides",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("permission_id", uuid, nullable=False),
        sa.Column("is_allowed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "permission_id", name="uq_user_permission_override"),
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_table(
        "user_invitations",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("role_id", uuid, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("invited_by_user_id", uuid),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime()),
        sa.Column("revoked_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.UniqueConstraint("token_hash", name="uq_user_invitations_token_hash"),
    )
    op.create_index("ix_user_invitations_email", "user_invitations", ["email"])
    op.create_table(
        "user_sessions",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime()),
        sa.Column("ip_address", sa.String(length=64)),
        sa.Column("user_agent", sa.String(length=512)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("last_seen_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_table(
        "two_factor_settings",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("user_id", uuid, nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_two_factor_settings_user_id"),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("actor_user_id", uuid),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", uuid),
        sa.Column("old_values_json", sa.JSON()),
        sa.Column("new_values_json", sa.JSON()),
        sa.Column("ip_address", sa.String(length=64)),
        sa.Column("user_agent", sa.String(length=512)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index(
        "ix_audit_logs_actor_created", "audit_logs", ["actor_user_id", "created_at"]
    )

    op.create_table(
        "donors",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("full_name", sa.String(length=180), nullable=False),
        sa.Column("phone", sa.String(length=50)),
        sa.Column("email", sa.String(length=320)),
        sa.Column("address", sa.Text()),
        sa.Column("donation_date", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("deleted_at", sa.DateTime()),
    )
    op.create_index("ix_donors_full_name", "donors", ["full_name"])
    op.create_index("ix_donors_phone", "donors", ["phone"])
    op.create_index("ix_donors_email", "donors", ["email"])
    op.create_table(
        "sections",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("location_name", sa.String(length=255)),
        sa.Column("soil_type", sa.String(length=120)),
        sa.Column("irrigation_type", sa.String(length=120)),
        sa.Column("gps_latitude", sa.Numeric(precision=10, scale=7)),
        sa.Column("gps_longitude", sa.Numeric(precision=10, scale=7)),
        sa.Column("image_url", sa.String(length=2048)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("deleted_at", sa.DateTime()),
    )
    op.create_index("ix_sections_name", "sections", ["name"])
    op.create_table(
        "palms",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("donor_id", uuid, nullable=False),
        sa.Column("section_id", uuid, nullable=False),
        sa.Column("plantation_date", sa.Date()),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="active"),
        sa.Column("current_health_status", sa.String(length=120)),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("deleted_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["donor_id"], ["donors.id"]),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"]),
        sa.UniqueConstraint("code", name="uq_palms_code"),
    )
    op.create_index("ix_palms_code", "palms", ["code"])
    op.create_index("ix_palms_section_id", "palms", ["section_id"])
    op.create_table(
        "harvest_records",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("palm_id", uuid, nullable=False),
        sa.Column("harvest_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=14, scale=2)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by_user_id", uuid),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["palm_id"], ["palms.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_harvest_records_palm_id", "harvest_records", ["palm_id"])
    op.create_table(
        "disease_records",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("palm_id", uuid, nullable=False),
        sa.Column("disease_name", sa.String(length=180), nullable=False),
        sa.Column("detected_at", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by_user_id", uuid),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["palm_id"], ["palms.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_disease_records_palm_id", "disease_records", ["palm_id"])
    op.create_table(
        "treatment_records",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("disease_record_id", uuid, nullable=False),
        sa.Column("treatment_name", sa.String(length=180), nullable=False),
        sa.Column("treatment_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by_user_id", uuid),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["disease_record_id"], ["disease_records.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_treatment_records_disease_record_id", "treatment_records", ["disease_record_id"]
    )
    op.create_table(
        "palm_notes",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("palm_id", uuid, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", uuid),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["palm_id"], ["palms.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_palm_notes_palm_id", "palm_notes", ["palm_id"])
    op.create_table(
        "palm_relationships",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("parent_palm_id", uuid, nullable=False),
        sa.Column("child_palm_id", uuid, nullable=False),
        sa.Column(
            "relationship_type",
            sa.String(length=60),
            nullable=False,
            server_default="parent_child",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["child_palm_id"], ["palms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_palm_id"], ["palms.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "parent_palm_id", "child_palm_id", name="uq_palm_relationships_parent_child"
        ),
    )
    op.create_index(
        "ix_palm_relationships_parent_palm_id", "palm_relationships", ["parent_palm_id"]
    )
    op.create_index(
        "ix_palm_relationships_child_palm_id", "palm_relationships", ["child_palm_id"]
    )

    role_names = {
        "Super Admin": "Unrestricted system administrator.",
        "Admin": "Administrator for operational palm data.",
        "Editor": "Editor for operational palm data.",
        "Viewer": "Read-only operational user.",
    }
    permission_descriptions = {
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
        "audit_logs.read": "Read audit logs.",
    }
    roles = sa.table(
        "roles",
        sa.column("id", uuid),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_system", sa.Boolean()),
    )
    permissions = sa.table(
        "permissions",
        sa.column("id", uuid),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        roles,
        [
            {
                "id": _uuid(f"role/{name}"),
                "name": name,
                "description": description,
                "is_system": True,
            }
            for name, description in role_names.items()
        ],
    )
    op.bulk_insert(
        permissions,
        [
            {
                "id": _uuid(f"permission/{code}"),
                "code": code,
                "description": description,
            }
            for code, description in permission_descriptions.items()
        ],
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", uuid),
        sa.column("permission_id", uuid),
    )
    all_permissions = set(permission_descriptions)
    admin_permissions = all_permissions - {
        "users.read",
        "users.invite",
        "users.update",
        "users.disable",
        "users.reset_password",
    }
    editor_permissions = {
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
    }
    viewer_permissions = {"donors.read", "sections.read", "palms.read"}
    permissions_by_role = {
        "Super Admin": all_permissions,
        "Admin": admin_permissions,
        "Editor": editor_permissions,
        "Viewer": viewer_permissions,
    }
    op.bulk_insert(
        role_permissions,
        [
            {
                "role_id": _uuid(f"role/{role_name}"),
                "permission_id": _uuid(f"permission/{permission_code}"),
            }
            for role_name, role_codes in permissions_by_role.items()
            for permission_code in sorted(role_codes)
        ],
    )


def downgrade() -> None:
    """Drop only the domain introduced by this revision."""
    op.drop_index("ix_palm_relationships_child_palm_id", table_name="palm_relationships")
    op.drop_index("ix_palm_relationships_parent_palm_id", table_name="palm_relationships")
    op.drop_table("palm_relationships")
    op.drop_index("ix_palm_notes_palm_id", table_name="palm_notes")
    op.drop_table("palm_notes")
    op.drop_index("ix_treatment_records_disease_record_id", table_name="treatment_records")
    op.drop_table("treatment_records")
    op.drop_index("ix_disease_records_palm_id", table_name="disease_records")
    op.drop_table("disease_records")
    op.drop_index("ix_harvest_records_palm_id", table_name="harvest_records")
    op.drop_table("harvest_records")
    op.drop_index("ix_palms_section_id", table_name="palms")
    op.drop_index("ix_palms_code", table_name="palms")
    op.drop_table("palms")
    op.drop_index("ix_sections_name", table_name="sections")
    op.drop_table("sections")
    op.drop_index("ix_donors_email", table_name="donors")
    op.drop_index("ix_donors_phone", table_name="donors")
    op.drop_index("ix_donors_full_name", table_name="donors")
    op.drop_table("donors")
    op.drop_index("ix_audit_logs_actor_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("two_factor_settings")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index("ix_user_invitations_email", table_name="user_invitations")
    op.drop_table("user_invitations")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_table("user_permission_overrides")
    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_table("users")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")

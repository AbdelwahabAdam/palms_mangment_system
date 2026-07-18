"""Add media, reporting, email, settings, and activity persistence.

Revision ID: 20260718_0003
Revises: 20260718_0002
"""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa


revision = "20260718_0003"
down_revision = "20260718_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the advanced backend tables without changing earlier revisions."""
    uuid = sa.Uuid(as_uuid=True)
    now = sa.text("CURRENT_TIMESTAMP")

    op.add_column("users", sa.Column("avatar_storage_key", sa.String(length=1024)))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=2048)))
    op.add_column("sections", sa.Column("image_storage_key", sa.String(length=1024)))

    op.create_table(
        "palm_images",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("palm_id", uuid, nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("thumbnail_key", sa.String(length=1024), nullable=False),
        sa.Column("medium_key", sa.String(length=1024), nullable=False),
        sa.Column("webp_key", sa.String(length=1024), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=2048), nullable=False),
        sa.Column("medium_url", sa.String(length=2048), nullable=False),
        sa.Column("full_url", sa.String(length=2048), nullable=False),
        sa.Column("webp_url", sa.String(length=2048), nullable=False),
        sa.Column("uploaded_by_user_id", uuid),
        sa.Column("captured_at", sa.DateTime()),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("metadata_json", sa.JSON()),
        sa.ForeignKeyConstraint(["palm_id"], ["palms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("storage_key", name="uq_palm_images_storage_key"),
    )
    op.create_index("ix_palm_images_palm_id", "palm_images", ["palm_id"])

    op.create_table(
        "report_templates",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("report_type", sa.String(length=40), nullable=False),
        sa.Column("fields_json", sa.JSON(), nullable=False),
        sa.Column("filters_json", sa.JSON()),
        sa.Column("created_by_user_id", uuid),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("name", "created_by_user_id", name="uq_report_templates_name_user"),
    )
    op.create_index(
        "ix_report_templates_created_by_user_id", "report_templates", ["created_by_user_id"]
    )
    op.create_table(
        "report_schedules",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("report_type", sa.String(length=40), nullable=False),
        sa.Column("template_id", uuid),
        sa.Column("frequency", sa.String(length=16), nullable=False),
        sa.Column("cron_expression", sa.String(length=120)),
        sa.Column("day_of_month", sa.Integer()),
        sa.Column("weekday", sa.Integer()),
        sa.Column("run_time", sa.String(length=5)),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("fields_json", sa.JSON()),
        sa.Column("filters_json", sa.JSON()),
        sa.Column("email_subject", sa.String(length=255)),
        sa.Column("include_summary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("attach_file", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_run_at", sa.DateTime()),
        sa.Column("next_run_at", sa.DateTime()),
        sa.Column("created_by_user_id", uuid),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["report_templates.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_report_schedules_enabled", "report_schedules", ["enabled"])
    op.create_index("ix_report_schedules_next_run_at", "report_schedules", ["next_run_at"])
    op.create_table(
        "report_schedule_recipients",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("schedule_id", uuid, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["schedule_id"], ["report_schedules.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("schedule_id", "email", name="uq_report_schedule_recipient"),
    )
    op.create_index(
        "ix_report_schedule_recipients_schedule_id",
        "report_schedule_recipients",
        ["schedule_id"],
    )
    op.create_table(
        "report_runs",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("schedule_id", uuid),
        sa.Column("report_type", sa.String(length=40), nullable=False),
        sa.Column("format", sa.String(length=8), nullable=False),
        sa.Column("fields_json", sa.JSON(), nullable=False),
        sa.Column("filters_json", sa.JSON()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("requested_by_user_id", uuid),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["schedule_id"], ["report_schedules.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_report_runs_schedule_id", "report_runs", ["schedule_id"])
    op.create_index("ix_report_runs_status", "report_runs", ["status"])
    op.create_table(
        "report_files",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("report_run_id", uuid, nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["report_run_id"], ["report_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("storage_key", name="uq_report_files_storage_key"),
    )
    op.create_index("ix_report_files_report_run_id", "report_files", ["report_run_id"])

    op.create_table(
        "email_logs",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("template_name", sa.String(length=80), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
    )
    op.create_index("ix_email_logs_recipient", "email_logs", ["recipient"])
    op.create_index("ix_email_logs_status", "email_logs", ["status"])
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=160), primary_key=True, nullable=False),
        sa.Column("value_json", sa.JSON()),
        sa.Column("updated_by_user_id", uuid),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "activity_feed",
        sa.Column("id", uuid, primary_key=True, nullable=False),
        sa.Column("actor_user_id", uuid),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", uuid),
        sa.Column("message", sa.String(length=500)),
        sa.Column("metadata_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_activity_feed_actor_user_id", "activity_feed", ["actor_user_id"])
    op.create_index("ix_activity_feed_created_at", "activity_feed", ["created_at"])

    permissions = sa.table(
        "permissions",
        sa.column("id", uuid),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    report_permissions = {
        "reports.read": "Read reports and report run history.",
        "reports.generate": "Preview and generate reports.",
        "reports.schedule": "Create and manage report schedules.",
    }
    op.bulk_insert(
        permissions,
        [
            {
                "id": uuid5(NAMESPACE_URL, f"palms-api/permission/{code}"),
                "code": code,
                "description": description,
            }
            for code, description in report_permissions.items()
        ],
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", uuid),
        sa.column("permission_id", uuid),
    )
    role_codes = {
        "Super Admin": report_permissions,
        "Admin": report_permissions,
        "Editor": {"reports.read", "reports.generate"},
    }
    op.bulk_insert(
        role_permissions,
        [
            {
                "role_id": uuid5(NAMESPACE_URL, f"palms-api/role/{role_name}"),
                "permission_id": uuid5(NAMESPACE_URL, f"palms-api/permission/{code}"),
            }
            for role_name, codes in role_codes.items()
            for code in codes
        ],
    )


def downgrade() -> None:
    """Drop only tables and columns introduced by this revision."""
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code IN "
            "('reports.read', 'reports.generate', 'reports.schedule'))"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN "
            "('reports.read', 'reports.generate', 'reports.schedule')"
        )
    )
    op.drop_index("ix_activity_feed_created_at", table_name="activity_feed")
    op.drop_index("ix_activity_feed_actor_user_id", table_name="activity_feed")
    op.drop_table("activity_feed")
    op.drop_table("system_settings")
    op.drop_index("ix_email_logs_status", table_name="email_logs")
    op.drop_index("ix_email_logs_recipient", table_name="email_logs")
    op.drop_table("email_logs")
    op.drop_index("ix_report_files_report_run_id", table_name="report_files")
    op.drop_table("report_files")
    op.drop_index("ix_report_runs_status", table_name="report_runs")
    op.drop_index("ix_report_runs_schedule_id", table_name="report_runs")
    op.drop_table("report_runs")
    op.drop_index("ix_report_schedule_recipients_schedule_id", table_name="report_schedule_recipients")
    op.drop_table("report_schedule_recipients")
    op.drop_index("ix_report_schedules_next_run_at", table_name="report_schedules")
    op.drop_index("ix_report_schedules_enabled", table_name="report_schedules")
    op.drop_table("report_schedules")
    op.drop_index("ix_report_templates_created_by_user_id", table_name="report_templates")
    op.drop_table("report_templates")
    op.drop_index("ix_palm_images_palm_id", table_name="palm_images")
    op.drop_table("palm_images")
    op.drop_column("sections", "image_storage_key")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "avatar_storage_key")

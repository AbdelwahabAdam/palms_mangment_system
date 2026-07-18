"""SQLAlchemy models for the Palms administration domain."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base shared by runtime models and Alembic."""


def utcnow() -> datetime:
    """Provide a timezone-naive UTC timestamp portable to SQLite and PostgreSQL."""
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.current_timestamp(),
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    users: Mapped[list[User]] = relationship(back_populates="role")
    permissions: Mapped[list[RolePermission]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    roles: Mapped[list[RolePermission]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )
    overrides: Mapped[list[UserPermissionOverride]] = relationship(
        back_populates="permission", cascade="all, delete-orphan"
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship(back_populates="roles")


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    avatar_storage_key: Mapped[str | None] = mapped_column(String(1024))
    avatar_url: Mapped[str | None] = mapped_column(String(2048))

    role: Mapped[Role] = relationship(back_populates="users")
    permission_overrides: Mapped[list[UserPermissionOverride]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    two_factor_setting: Mapped[TwoFactorSetting | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    uploaded_palm_images: Mapped[list[PalmImage]] = relationship(
        back_populates="uploaded_by", foreign_keys="PalmImage.uploaded_by_user_id"
    )


class UserPermissionOverride(Base, TimestampMixin):
    __tablename__ = "user_permission_overrides"
    __table_args__ = (UniqueConstraint("user_id", "permission_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )
    is_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)

    user: Mapped[User] = relationship(back_populates="permission_overrides")
    permission: Mapped[Permission] = relationship(back_populates="overrides")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    user: Mapped[User] = relationship(back_populates="reset_tokens")


class UserInvitation(Base):
    __tablename__ = "user_invitations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    invited_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    role: Mapped[Role] = relationship()
    invited_by: Mapped[User | None] = relationship(foreign_keys=[invited_by_user_id])


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))

    user: Mapped[User] = relationship(back_populates="sessions")


class TwoFactorSetting(Base, TimestampMixin):
    __tablename__ = "two_factor_settings"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    user: Mapped[User] = relationship(back_populates="two_factor_setting")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_actor_created", "actor_user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    old_values_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    new_values_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    actor: Mapped[User | None] = relationship(foreign_keys=[actor_user_id])


class Donor(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "donors"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), index=True)
    email: Mapped[str | None] = mapped_column(String(320), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    donation_date: Mapped[datetime | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    palms: Mapped[list[Palm]] = relationship(back_populates="donor")


class Section(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sections"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    location_name: Mapped[str | None] = mapped_column(String(255))
    soil_type: Mapped[str | None] = mapped_column(String(120))
    irrigation_type: Mapped[str | None] = mapped_column(String(120))
    gps_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    gps_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    image_storage_key: Mapped[str | None] = mapped_column(String(1024))

    palms: Mapped[list[Palm]] = relationship(back_populates="section")


class Palm(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "palms"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    donor_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("donors.id"), nullable=False)
    section_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("sections.id"), nullable=False, index=True
    )
    plantation_date: Mapped[datetime | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(80), default="active", server_default="active")
    current_health_status: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)

    donor: Mapped[Donor] = relationship(back_populates="palms")
    section: Mapped[Section] = relationship(back_populates="palms")
    harvests: Mapped[list[HarvestRecord]] = relationship(
        back_populates="palm", cascade="all, delete-orphan"
    )
    diseases: Mapped[list[DiseaseRecord]] = relationship(
        back_populates="palm", cascade="all, delete-orphan"
    )
    notes: Mapped[list[PalmNote]] = relationship(
        back_populates="palm", cascade="all, delete-orphan"
    )
    parent_relationships: Mapped[list[PalmRelationship]] = relationship(
        back_populates="parent",
        foreign_keys="PalmRelationship.parent_palm_id",
        cascade="all, delete-orphan",
    )
    child_relationships: Mapped[list[PalmRelationship]] = relationship(
        back_populates="child",
        foreign_keys="PalmRelationship.child_palm_id",
        cascade="all, delete-orphan",
    )
    images: Mapped[list[PalmImage]] = relationship(
        back_populates="palm", cascade="all, delete-orphan", order_by="PalmImage.uploaded_at.desc()"
    )


class HarvestRecord(Base, TimestampMixin):
    __tablename__ = "harvest_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    palm_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("palms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    harvest_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    palm: Mapped[Palm] = relationship(back_populates="harvests")
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_user_id])


class DiseaseRecord(Base, TimestampMixin):
    __tablename__ = "disease_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    palm_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("palms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    disease_name: Mapped[str] = mapped_column(String(180), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="active", server_default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    palm: Mapped[Palm] = relationship(back_populates="diseases")
    treatments: Mapped[list[TreatmentRecord]] = relationship(
        back_populates="disease_record", cascade="all, delete-orphan"
    )
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_user_id])


class TreatmentRecord(Base):
    __tablename__ = "treatment_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    disease_record_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("disease_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    treatment_name: Mapped[str] = mapped_column(String(180), nullable=False)
    treatment_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    disease_record: Mapped[DiseaseRecord] = relationship(back_populates="treatments")
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_user_id])


class PalmNote(Base):
    __tablename__ = "palm_notes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    palm_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("palms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    palm: Mapped[Palm] = relationship(back_populates="notes")
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_user_id])


class PalmRelationship(Base):
    __tablename__ = "palm_relationships"
    __table_args__ = (UniqueConstraint("parent_palm_id", "child_palm_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    parent_palm_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("palms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_palm_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("palms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(
        String(60), default="parent_child", server_default="parent_child"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    parent: Mapped[Palm] = relationship(
        back_populates="parent_relationships", foreign_keys=[parent_palm_id]
    )
    child: Mapped[Palm] = relationship(
        back_populates="child_relationships", foreign_keys=[child_palm_id]
    )


class PalmImage(Base):
    """Storage-backed, derived palm-image variants."""

    __tablename__ = "palm_images"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    palm_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("palms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    thumbnail_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    medium_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    webp_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    medium_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    full_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    webp_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    uploaded_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    palm: Mapped[Palm] = relationship(back_populates="images")
    uploaded_by: Mapped[User | None] = relationship(
        back_populates="uploaded_palm_images", foreign_keys=[uploaded_by_user_id]
    )


class ReportTemplate(Base, TimestampMixin):
    __tablename__ = "report_templates"
    __table_args__ = (UniqueConstraint("name", "created_by_user_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    fields_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    filters_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_user_id])
    schedules: Mapped[list[ReportSchedule]] = relationship(back_populates="template")


class ReportSchedule(Base, TimestampMixin):
    __tablename__ = "report_schedules"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    template_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("report_templates.id", ondelete="SET NULL")
    )
    frequency: Mapped[str] = mapped_column(String(16), nullable=False)
    cron_expression: Mapped[str | None] = mapped_column(String(120))
    day_of_month: Mapped[int | None] = mapped_column()
    weekday: Mapped[int | None] = mapped_column()
    run_time: Mapped[str | None] = mapped_column(String(5))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    fields_json: Mapped[list[str] | None] = mapped_column(JSON)
    filters_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    email_subject: Mapped[str | None] = mapped_column(String(255))
    include_summary: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    attach_file: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1", index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), index=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    template: Mapped[ReportTemplate | None] = relationship(back_populates="schedules")
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_user_id])
    recipients: Mapped[list[ReportScheduleRecipient]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )
    runs: Mapped[list[ReportRun]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan", order_by="ReportRun.created_at.desc()"
    )


class ReportScheduleRecipient(Base):
    __tablename__ = "report_schedule_recipients"
    __table_args__ = (UniqueConstraint("schedule_id", "email"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    schedule_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("report_schedules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    schedule: Mapped[ReportSchedule] = relationship(back_populates="recipients")


class ReportRun(Base):
    __tablename__ = "report_runs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    schedule_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("report_schedules.id", ondelete="SET NULL"), index=True
    )
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    fields_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    filters_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    schedule: Mapped[ReportSchedule | None] = relationship(back_populates="runs")
    requested_by: Mapped[User | None] = relationship(foreign_keys=[requested_by_user_id])
    files: Mapped[list[ReportFile]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class ReportFile(Base):
    __tablename__ = "report_files"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    report_run_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("report_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    run: Mapped[ReportRun] = relationship(back_populates="files")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    template_name: Mapped[str] = mapped_column(String(80), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )


class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    value_json: Mapped[dict[str, Any] | list[Any] | str | int | bool | None] = mapped_column(JSON)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[User | None] = relationship(foreign_keys=[updated_by_user_id])


class ActivityFeed(Base):
    __tablename__ = "activity_feed"
    __table_args__ = (Index("ix_activity_feed_created_at", "created_at"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True))
    message: Mapped[str | None] = mapped_column(String(500))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=utcnow, server_default=func.current_timestamp()
    )

    actor: Mapped[User | None] = relationship(foreign_keys=[actor_user_id])

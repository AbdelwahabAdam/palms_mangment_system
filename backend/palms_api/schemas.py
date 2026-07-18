"""Pydantic request contracts for the authenticated administration API."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RequestModel(BaseModel):
    """Strict API input model with trimmed string values."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NonEmptyPatchModel(RequestModel):
    """Reject PATCH bodies that do not ask to change any field."""

    @model_validator(mode="after")
    def requires_a_change(self) -> NonEmptyPatchModel:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class PasswordValue(RequestModel):
    password: str = Field(min_length=12, max_length=256)

    @field_validator("password")
    @classmethod
    def password_has_non_space_content(cls, value: str) -> str:
        if value.isspace() or not any(character.isalpha() for character in value):
            raise ValueError("Password must contain at least one letter.")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must contain at least one number.")
        return value


def _validated_email(value: str) -> str:
    normalized = value.lower()
    local, separator, domain = normalized.partition("@")
    if not separator or not local or "." not in domain or len(normalized) > 320:
        raise ValueError("A valid email address is required.")
    return normalized


class LoginRequest(RequestModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

    _email = field_validator("email")(_validated_email)


class ForgotPasswordRequest(RequestModel):
    email: str = Field(min_length=3, max_length=320)

    _email = field_validator("email")(_validated_email)


class ResetPasswordRequest(PasswordValue):
    token: str = Field(min_length=32, max_length=512)


class ChangePasswordRequest(RequestModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return PasswordValue(password=value).password


class ProfilePatchRequest(NonEmptyPatchModel):
    full_name: str = Field(default=None, min_length=1, max_length=160)


class ChangeEmailRequest(RequestModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_email: str = Field(min_length=3, max_length=320)

    _email = field_validator("new_email")(_validated_email)


class InviteUserRequest(RequestModel):
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=1, max_length=160)
    role_id: UUID

    _email = field_validator("email")(_validated_email)


class UserPatchRequest(NonEmptyPatchModel):
    full_name: str = Field(default=None, min_length=1, max_length=160)
    role_id: UUID = None
    permission_overrides: dict[str, bool] = Field(default=None, max_length=100)


class DonorCreateRequest(RequestModel):
    full_name: str = Field(min_length=1, max_length=180)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = Field(default=None, max_length=5_000)
    donation_date: date | None = None
    notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, value: str | None) -> str | None:
        return _validated_email(value) if value else value


class DonorPatchRequest(NonEmptyPatchModel):
    full_name: str = Field(default=None, min_length=1, max_length=180)
    phone: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = Field(default=None, max_length=5_000)
    donation_date: date | None = None
    notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, value: str | None) -> str | None:
        return _validated_email(value) if value else value


class SectionCreateRequest(RequestModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10_000)
    location_name: str | None = Field(default=None, max_length=255)
    soil_type: str | None = Field(default=None, max_length=120)
    irrigation_type: str | None = Field(default=None, max_length=120)
    gps_latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    gps_longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))


class SectionPatchRequest(NonEmptyPatchModel):
    name: str = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=10_000)
    location_name: str | None = Field(default=None, max_length=255)
    soil_type: str | None = Field(default=None, max_length=120)
    irrigation_type: str | None = Field(default=None, max_length=120)
    gps_latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    gps_longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))


class PalmCreateRequest(RequestModel):
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    donor_id: UUID
    section_id: UUID
    plantation_date: date | None = None
    status: str = Field(default="active", min_length=1, max_length=80)
    current_health_status: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=10_000)


class PalmPatchRequest(NonEmptyPatchModel):
    code: str = Field(
        default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$"
    )
    donor_id: UUID = None
    section_id: UUID = None
    plantation_date: date | None = None
    status: str = Field(default=None, min_length=1, max_length=80)
    current_health_status: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=10_000)


class BulkPalmIdsRequest(RequestModel):
    palm_ids: list[UUID] = Field(min_length=1, max_length=200)

    @field_validator("palm_ids")
    @classmethod
    def no_duplicate_palm_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("palm_ids must not contain duplicates.")
        return value


class BulkPalmSectionRequest(BulkPalmIdsRequest):
    section_id: UUID


class HarvestCreateRequest(RequestModel):
    harvest_date: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    unit: str = Field(min_length=1, max_length=32)
    revenue: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=10_000)


class HarvestPatchRequest(NonEmptyPatchModel):
    harvest_date: date = None
    amount: Decimal = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    unit: str = Field(default=None, min_length=1, max_length=32)
    revenue: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=10_000)


class DiseaseCreateRequest(RequestModel):
    disease_name: str = Field(min_length=1, max_length=180)
    detected_at: date
    status: str = Field(default="active", min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=10_000)


class DiseasePatchRequest(NonEmptyPatchModel):
    disease_name: str = Field(default=None, min_length=1, max_length=180)
    detected_at: date = None
    status: str = Field(default=None, min_length=1, max_length=80)
    notes: str | None = Field(default=None, max_length=10_000)


class TreatmentCreateRequest(RequestModel):
    treatment_name: str = Field(min_length=1, max_length=180)
    treatment_date: date
    notes: str | None = Field(default=None, max_length=10_000)


class TreatmentPatchRequest(NonEmptyPatchModel):
    treatment_name: str = Field(default=None, min_length=1, max_length=180)
    treatment_date: date = None
    notes: str | None = Field(default=None, max_length=10_000)


class PalmNoteCreateRequest(RequestModel):
    body: str = Field(min_length=1, max_length=10_000)


class PalmRelationshipCreateRequest(RequestModel):
    child_palm_id: UUID
    relationship_type: str = Field(default="parent_child", min_length=1, max_length=60)


class ReportPreviewRequest(RequestModel):
    report_type: str = Field(min_length=1, max_length=40)
    fields: list[str] | None = Field(default=None, max_length=20)
    filters: dict[str, object] | None = None


class ReportGenerateRequest(ReportPreviewRequest):
    format: str = Field(default="csv", pattern=r"^(csv|pdf)$")


class ReportTemplateCreateRequest(RequestModel):
    name: str = Field(min_length=1, max_length=160)
    report_type: str = Field(min_length=1, max_length=40)
    fields: list[str] = Field(min_length=1, max_length=20)
    filters: dict[str, object] | None = None


class ReportScheduleCreateRequest(RequestModel):
    name: str = Field(min_length=1, max_length=160)
    report_type: str = Field(min_length=1, max_length=40)
    template_id: UUID | None = None
    frequency: str = Field(min_length=1, max_length=16)
    cron_expression: str | None = Field(default=None, max_length=120)
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    weekday: int | None = Field(default=None, ge=0, le=6)
    run_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    timezone: str = Field(min_length=1, max_length=64)
    format: str = Field(pattern=r"^(csv|pdf)$")
    fields: list[str] | None = Field(default=None, max_length=20)
    filters: dict[str, object] | None = None
    recipients: list[str] = Field(min_length=1, max_length=50)
    email_subject: str | None = Field(default=None, max_length=255)
    include_summary: bool = True
    attach_file: bool = True
    enabled: bool = True

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, value: list[str]) -> list[str]:
        normalized = [_validated_email(email) for email in value]
        if len(normalized) != len(set(normalized)):
            raise ValueError("recipients must not contain duplicates.")
        return normalized


class ReportSchedulePatchRequest(NonEmptyPatchModel):
    name: str = Field(default=None, min_length=1, max_length=160)
    report_type: str = Field(default=None, min_length=1, max_length=40)
    template_id: UUID | None = None
    frequency: str = Field(default=None, min_length=1, max_length=16)
    cron_expression: str | None = Field(default=None, max_length=120)
    day_of_month: int | None = Field(default=None, ge=1, le=28)
    weekday: int | None = Field(default=None, ge=0, le=6)
    run_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    timezone: str = Field(default=None, min_length=1, max_length=64)
    format: str = Field(default=None, pattern=r"^(csv|pdf)$")
    fields: list[str] | None = Field(default=None, max_length=20)
    filters: dict[str, object] | None = None
    recipients: list[str] | None = Field(default=None, min_length=1, max_length=50)
    email_subject: str | None = Field(default=None, max_length=255)
    include_summary: bool | None = None
    attach_file: bool | None = None
    enabled: bool | None = None

    @field_validator("recipients")
    @classmethod
    def validate_patch_recipients(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        normalized = [_validated_email(email) for email in value]
        if len(normalized) != len(set(normalized)):
            raise ValueError("recipients must not contain duplicates.")
        return normalized

"""Typed application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """Runtime configuration with safe defaults for local development."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "palms-api"
    app_version: str = "0.1.0"
    app_environment: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    database_url: str = "sqlite+pysqlite:///./palms.db"
    database_echo: bool = False
    database_pool_size: int = Field(default=5, ge=1, le=100)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    session_cookie_name: str = "palms_session"
    session_timeout_minutes: int = Field(default=60, ge=5, le=43_200)
    session_cookie_secure: bool | None = None
    password_reset_token_minutes: int = Field(default=30, ge=5, le=1_440)
    invitation_token_hours: int = Field(default=72, ge=1, le=720)
    public_app_url: str = "http://localhost:3000"
    admin_app_url: str = "http://localhost:3000/admin"
    image_max_upload_mb: int = Field(default=15, ge=1, le=100)
    storage_provider: Literal["memory", "s3"] = "memory"
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket_name: str = "palms-assets"
    s3_region: str = "us-east-1"
    s3_public_base_url: str | None = None
    s3_use_path_style: bool = True
    s3_create_bucket: bool = False
    s3_public_read: bool = False
    # Set to "AES256" for AWS SSE-S3. Leave unset for MinIO (SSE without KMS fails).
    s3_server_side_encryption: str | None = None
    redis_url: str | None = None
    rq_queue_name: str = "reports"
    report_execution_mode: Literal["sync", "rq"] = "sync"
    smtp_host: str = "localhost"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False
    smtp_from_email: str = "no-reply@palms.local"
    smtp_from_name: str = "Palms Management"
    email_enabled: bool = False

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Restrict runtime URLs to the supported database backends."""
        try:
            drivername = make_url(value).drivername
        except Exception as error:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL.") from error

        if not (
            drivername.startswith("sqlite")
            or drivername.startswith("postgresql")
        ):
            raise ValueError("DATABASE_URL must use SQLite or PostgreSQL.")
        return value

    def pyramid_settings(self) -> dict[str, Any]:
        """Provide serializable settings for Pyramid's application registry."""
        return self.model_dump(mode="json")

    @property
    def use_secure_session_cookie(self) -> bool:
        """Require HTTPS cookies outside explicitly local/test deployments."""
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.app_environment in {"staging", "production"}


@lru_cache
def get_settings() -> Settings:
    """Return environment-derived settings for scripts such as Alembic."""
    return Settings()

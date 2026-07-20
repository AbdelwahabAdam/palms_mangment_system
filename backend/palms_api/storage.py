"""S3-compatible storage behind a narrow, testable interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Protocol
from urllib.parse import quote, urljoin

import boto3
from botocore.client import Config

from palms_api.config import Settings


def safe_storage_key(key: str) -> str:
    """Reject traversal, empty segments, and untrusted absolute object keys."""
    normalized = key.replace("\\", "/").strip("/")
    parts = normalized.split("/")
    if not normalized or any(not part or part in {".", ".."} for part in parts):
        raise ValueError("Storage key must be a relative, non-traversing path.")
    return "/".join(parts)


class StorageClient(Protocol):
    """Minimum object-storage operations used by media and reports."""

    def upload_bytes(self, key: str, content: bytes, *, content_type: str) -> None: ...

    def delete_file(self, key: str) -> None: ...

    def get_bytes(self, key: str) -> bytes: ...

    def get_public_url(self, key: str) -> str: ...

    def get_signed_url(self, key: str, *, expires_in: int = 900) -> str: ...

    def ensure_bucket(self) -> None: ...


@dataclass
class MemoryStorageClient:
    """Memory-safe fake storage used by tests and local deterministic execution."""

    bucket_name: str = "palms-assets"
    objects: dict[str, tuple[bytes, str]] = field(default_factory=dict)

    def upload_bytes(self, key: str, content: bytes, *, content_type: str) -> None:
        key = safe_storage_key(key)
        self.objects[key] = (bytes(content), content_type)

    def delete_file(self, key: str) -> None:
        self.objects.pop(safe_storage_key(key), None)

    def get_bytes(self, key: str) -> bytes:
        return self.objects[safe_storage_key(key)][0]

    def get_public_url(self, key: str) -> str:
        return f"memory://{quote(self.bucket_name, safe='')}/{quote(safe_storage_key(key), safe='/')}"

    def get_signed_url(self, key: str, *, expires_in: int = 900) -> str:
        if expires_in < 1:
            raise ValueError("expires_in must be positive.")
        return f"{self.get_public_url(key)}?expires_in={expires_in}"

    def ensure_bucket(self) -> None:
        return None


class S3StorageClient:
    """AWS S3 or MinIO client with endpoint and URL safety controls."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bucket_name = settings.s3_bucket_name
        config = Config(s3={"addressing_style": "path" if settings.s3_use_path_style else "virtual"})
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
            config=config,
        )

    def upload_bytes(self, key: str, content: bytes, *, content_type: str) -> None:
        params: dict[str, object] = {
            "Bucket": self.bucket_name,
            "Key": safe_storage_key(key),
            "Body": content,
            "ContentType": content_type,
        }
        # AWS S3: default SSE-S3. MinIO/custom endpoints often reject SSE without KMS.
        if self.settings.s3_server_side_encryption:
            params["ServerSideEncryption"] = self.settings.s3_server_side_encryption
        elif not self.settings.s3_endpoint_url:
            params["ServerSideEncryption"] = "AES256"
        self.client.put_object(**params)

    def delete_file(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=safe_storage_key(key))

    def get_bytes(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket_name, Key=safe_storage_key(key))["Body"].read()

    def get_public_url(self, key: str) -> str:
        safe_key = quote(safe_storage_key(key), safe="/")
        if self.settings.s3_public_base_url:
            return urljoin(self.settings.s3_public_base_url.rstrip("/") + "/", safe_key)
        if self.settings.s3_endpoint_url:
            return f"{self.settings.s3_endpoint_url.rstrip('/')}/{quote(self.bucket_name, safe='')}/{safe_key}"
        return f"https://{self.bucket_name}.s3.{self.settings.s3_region}.amazonaws.com/{safe_key}"

    def get_signed_url(self, key: str, *, expires_in: int = 900) -> str:
        if expires_in < 1 or expires_in > int(timedelta(days=7).total_seconds()):
            raise ValueError("Signed URL expiry must be between one second and seven days.")
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": safe_storage_key(key)},
            ExpiresIn=expires_in,
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except Exception:
            if not self.settings.s3_create_bucket:
                raise
            params: dict[str, object] = {"Bucket": self.bucket_name}
            if self.settings.s3_region != "us-east-1":
                params["CreateBucketConfiguration"] = {
                    "LocationConstraint": self.settings.s3_region
                }
            self.client.create_bucket(**params)
        if self.settings.s3_public_read:
            self.configure_public_read()

    def configure_public_read(self) -> None:
        """Configure a deliberately narrow read-only policy when explicitly enabled."""
        policy = (
            '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",'
            '"Principal":"*","Action":["s3:GetObject"],"Resource":"arn:aws:s3:::'
            f"{self.bucket_name}/*" + '"}]}'
        )
        self.client.put_bucket_policy(Bucket=self.bucket_name, Policy=policy)


def build_storage_client(settings: Settings) -> StorageClient:
    """Build the configured backend, retaining an in-memory safe default."""
    if settings.storage_provider == "s3":
        return S3StorageClient(settings)
    return MemoryStorageClient(bucket_name=settings.s3_bucket_name)

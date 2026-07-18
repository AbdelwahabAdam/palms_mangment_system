"""Validated Pillow image processing and variant persistence helpers."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from palms_api.config import Settings
from palms_api.errors import APIError
from palms_api.storage import StorageClient


Image.MAX_IMAGE_PIXELS = 40_000_000
_FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}
_SIZES = {"thumbnail": 320, "medium": 960, "full": 1920, "webp": 1920}


@dataclass(frozen=True)
class ImageVariants:
    """Stored image keys, public URLs, and only safe derived metadata."""

    storage_key: str
    thumbnail_key: str
    medium_key: str
    webp_key: str
    thumbnail_url: str
    medium_url: str
    full_url: str
    webp_url: str
    metadata: dict[str, Any]

    @property
    def keys(self) -> tuple[str, str, str, str]:
        return (self.thumbnail_key, self.medium_key, self.storage_key, self.webp_key)


def _invalid_image(message: str) -> APIError:
    return APIError(status=422, code="invalid_image", message=message)


def _load_image(content: bytes, settings: Settings) -> tuple[Image.Image, str]:
    if not content:
        raise _invalid_image("An image file is required.")
    if len(content) > settings.image_max_upload_mb * 1024 * 1024:
        raise _invalid_image(f"Image files may not exceed {settings.image_max_upload_mb} MB.")
    try:
        with Image.open(BytesIO(content)) as probe:
            image_format = probe.format
            probe.verify()
        if image_format not in _FORMATS:
            raise _invalid_image("Only JPEG, PNG, and WebP images are accepted.")
        with Image.open(BytesIO(content)) as decoded:
            # Recreate pixels, deliberately removing EXIF, ICC, and ancillary metadata.
            decoded.load()
            orientation_fixed = ImageOps.exif_transpose(decoded)
            rgba = orientation_fixed.convert("RGBA")
            return rgba.copy(), image_format
    except Image.DecompressionBombError as error:
        raise _invalid_image("The image dimensions are too large.") from error
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise _invalid_image("The file content is not a valid supported image.") from error


def _encode(image: Image.Image, *, width: int, format_name: str) -> bytes:
    resized = ImageOps.contain(image, (width, width * 2), method=Image.Resampling.LANCZOS)
    output = BytesIO()
    if format_name == "WEBP":
        resized.save(output, format="WEBP", quality=82, method=6)
    else:
        # JPEG cannot retain alpha and the composited background avoids hidden pixels.
        flattened = Image.new("RGB", resized.size, "white")
        flattened.paste(resized, mask=resized.getchannel("A"))
        flattened.save(output, format="JPEG", quality=86, optimize=True, progressive=True)
    return output.getvalue()


def process_and_store_image(
    *,
    content: bytes,
    original_filename: str | None,
    prefix: str,
    storage: StorageClient,
    settings: Settings,
) -> ImageVariants:
    """Validate an upload, strip metadata, generate four variants, and store all."""
    image, source_format = _load_image(content, settings)
    token = uuid4().hex
    clean_prefix = prefix.strip("/")
    base = f"{clean_prefix}/{token}"
    thumbnail_key = f"{base}/thumbnail.jpg"
    medium_key = f"{base}/medium.jpg"
    storage_key = f"{base}/full.jpg"
    webp_key = f"{base}/full.webp"
    variants = (
        (thumbnail_key, _encode(image, width=_SIZES["thumbnail"], format_name="JPEG"), "image/jpeg"),
        (medium_key, _encode(image, width=_SIZES["medium"], format_name="JPEG"), "image/jpeg"),
        (storage_key, _encode(image, width=_SIZES["full"], format_name="JPEG"), "image/jpeg"),
        (webp_key, _encode(image, width=_SIZES["webp"], format_name="WEBP"), "image/webp"),
    )
    stored: list[str] = []
    try:
        for key, encoded, content_type in variants:
            storage.upload_bytes(key, encoded, content_type=content_type)
            stored.append(key)
    except Exception:
        for key in stored:
            try:
                storage.delete_file(key)
            except Exception:
                pass
        raise
    return ImageVariants(
        storage_key=storage_key,
        thumbnail_key=thumbnail_key,
        medium_key=medium_key,
        webp_key=webp_key,
        thumbnail_url=storage.get_public_url(thumbnail_key),
        medium_url=storage.get_public_url(medium_key),
        full_url=storage.get_public_url(storage_key),
        webp_url=storage.get_public_url(webp_key),
        metadata={
            "source_format": source_format,
            "original_filename": (original_filename or "")[:255] or None,
            "width": image.width,
            "height": image.height,
            "metadata_stripped": True,
        },
    )


def delete_image_variants(storage: StorageClient, variants: ImageVariants) -> None:
    """Best-effort deletion that continues after individual object failures."""
    failures: list[str] = []
    for key in variants.keys:
        try:
            storage.delete_file(key)
        except Exception:
            failures.append(key)
    if failures:
        raise RuntimeError("Failed to delete one or more image variants.")

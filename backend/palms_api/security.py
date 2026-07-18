"""Password and opaque-token primitives used by authentication workflows."""

from __future__ import annotations

from hashlib import sha256
from secrets import token_urlsafe

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_PASSWORD_HASHER = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a validated password with Argon2id."""
    return _PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return whether a plaintext password matches without leaking hash errors."""
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def new_opaque_token() -> str:
    """Create a high-entropy token suitable for a cookie or one-time link."""
    return token_urlsafe(48)


def token_digest(token: str) -> str:
    """Store and look up only the SHA-256 digest of opaque tokens."""
    return sha256(token.encode("utf-8")).hexdigest()

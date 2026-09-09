from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)


_password_hasher = PasswordHasher()


def hash_password(
    password: str,
) -> str:
    """Hash a plaintext password with Argon2id."""

    if not isinstance(
        password,
        str,
    ):
        raise TypeError(
            "Password must be text."
        )

    if len(password) < 12:
        raise ValueError(
            "Password must contain at least 12 characters."
        )

    if len(password) > 128:
        raise ValueError(
            "Password must contain at most 128 characters."
        )

    return _password_hasher.hash(
        password
    )


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    """Verify a plaintext password against an Argon2 hash."""

    if (
        not isinstance(password, str)
        or not isinstance(password_hash, str)
        or not password_hash
    ):
        return False

    try:
        return bool(
            _password_hasher.verify(
                password_hash,
                password,
            )
        )
    except (
        VerifyMismatchError,
        InvalidHashError,
        VerificationError,
    ):
        return False


def password_hash_needs_rehash(
    password_hash: str,
) -> bool:
    """Return whether an existing hash should be upgraded."""

    try:
        return bool(
            _password_hasher.check_needs_rehash(
                password_hash
            )
        )
    except (
        InvalidHashError,
        VerificationError,
    ):
        return True

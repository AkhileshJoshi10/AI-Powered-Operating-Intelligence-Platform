from __future__ import annotations

from typing import Any
import re

from sqlalchemy import text

from backend.app.core.security import (
    hash_password,
)
from backend.app.db.database import engine


ALLOWED_APP_USER_ROLES = {
    "Admin",
    "Manager",
    "Viewer",
}


def normalize_email(
    email: str,
) -> str:
    """Normalize one application-user email for storage and lookup."""

    normalized = str(
        email
    ).strip().casefold()

    if not normalized:
        raise ValueError(
            "Email is required."
        )

    if len(normalized) > 320:
        raise ValueError(
            "Email is too long."
        )

    if re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+",
        normalized,
    ) is None:
        raise ValueError(
            "Email format is invalid."
        )

    return normalized


def normalize_full_name(
    full_name: str,
) -> str:
    """Normalize a human display name without changing its casing."""

    normalized = " ".join(
        str(full_name).split()
    )

    if len(normalized) < 2:
        raise ValueError(
            "Full name must contain at least 2 characters."
        )

    if len(normalized) > 150:
        raise ValueError(
            "Full name must contain at most 150 characters."
        )

    return normalized


def serialize_app_user(
    row: Any,
) -> dict[str, Any]:
    """Return one public-safe application user without its password hash."""

    return {
        "user_id": int(
            row["user_id"]
        ),
        "email": str(
            row["email"]
        ),
        "full_name": str(
            row["full_name"]
        ),
        "role": str(
            row["role"]
        ),
        "is_active": bool(
            row["is_active"]
        ),
        "last_login_at": row[
            "last_login_at"
        ],
        "created_at": row[
            "created_at"
        ],
        "updated_at": row[
            "updated_at"
        ],
    }


def get_app_user_by_email(
    email: str,
    *,
    include_password_hash: bool = False,
) -> dict[str, Any] | None:
    """Return one normalized user identity by email."""

    normalized_email = normalize_email(
        email
    )

    query = text(
        """
        SELECT
            user_id,
            email,
            full_name,
            password_hash,
            role,
            is_active,
            last_login_at,
            created_at,
            updated_at
        FROM app_users
        WHERE email = :email;
        """
    )

    with engine.connect() as connection:
        row = (
            connection.execute(
                query,
                {
                    "email": normalized_email,
                },
            )
            .mappings()
            .one_or_none()
        )

    if row is None:
        return None

    result = serialize_app_user(
        row
    )

    if include_password_hash:
        result["password_hash"] = str(
            row["password_hash"]
        )

    return result


def get_app_user_by_id(
    user_id: int,
) -> dict[str, Any] | None:
    """Return one public-safe application user by identifier."""

    query = text(
        """
        SELECT
            user_id,
            email,
            full_name,
            role,
            is_active,
            last_login_at,
            created_at,
            updated_at
        FROM app_users
        WHERE user_id = :user_id;
        """
    )

    with engine.connect() as connection:
        row = (
            connection.execute(
                query,
                {
                    "user_id": user_id,
                },
            )
            .mappings()
            .one_or_none()
        )

    if row is None:
        return None

    return serialize_app_user(
        row
    )


def create_app_user(
    *,
    email: str,
    full_name: str,
    password: str,
    role: str,
) -> dict[str, Any]:
    """
    Create one human application identity.

    This service is intentionally not exposed as a public registration
    endpoint. Initial users are bootstrapped through a local admin script.
    """

    normalized_email = normalize_email(
        email
    )
    normalized_name = normalize_full_name(
        full_name
    )

    if role not in ALLOWED_APP_USER_ROLES:
        raise ValueError(
            "Role must be Admin, Manager, or Viewer."
        )

    password_hash = hash_password(
        password
    )

    insert_query = text(
        """
        INSERT INTO app_users (
            email,
            full_name,
            password_hash,
            role
        )
        VALUES (
            :email,
            :full_name,
            :password_hash,
            :role
        )
        ON CONFLICT (email)
        DO NOTHING
        RETURNING
            user_id,
            email,
            full_name,
            role,
            is_active,
            last_login_at,
            created_at,
            updated_at;
        """
    )

    with engine.begin() as connection:
        row = (
            connection.execute(
                insert_query,
                {
                    "email": normalized_email,
                    "full_name": normalized_name,
                    "password_hash": password_hash,
                    "role": role,
                },
            )
            .mappings()
            .one_or_none()
        )

    if row is None:
        existing_user = get_app_user_by_email(
            normalized_email
        )

        return {
            "outcome": "duplicate",
            "user": existing_user,
        }

    return {
        "outcome": "success",
        "user": serialize_app_user(
            row
        ),
    }

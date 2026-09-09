from __future__ import annotations

from typing import Any

from sqlalchemy import text

from backend.app.core.security import (
    hash_password,
    password_hash_needs_rehash,
    verify_password,
)
from backend.app.services.auth_service import (
    create_app_user,
    get_app_user_by_email,
    normalize_email,
)


def test_app_users_table_exists(
    test_engine: Any,
) -> None:
    """The test database must receive the Day 39A.1 migration."""

    with test_engine.connect() as connection:
        columns = (
            connection.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE
                        table_schema = 'public'
                        AND table_name = 'app_users';
                    """
                )
            )
            .scalars()
            .all()
        )

    assert {
        "user_id",
        "email",
        "full_name",
        "password_hash",
        "role",
        "is_active",
        "last_login_at",
        "created_at",
        "updated_at",
    }.issubset(
        set(columns)
    )


def test_password_hash_round_trip() -> None:
    password = "ExamplePassword!2026"

    password_hash = hash_password(
        password
    )

    assert password_hash != password
    assert password_hash.startswith(
        "$argon2"
    )
    assert verify_password(
        password,
        password_hash,
    )
    assert not verify_password(
        "WrongPassword!2026",
        password_hash,
    )
    assert isinstance(
        password_hash_needs_rehash(
            password_hash
        ),
        bool,
    )


def test_normalize_email() -> None:
    assert normalize_email(
        "  Manager@SmartMart.Demo "
    ) == "manager@smartmart.demo"


def test_create_app_user_is_case_insensitive_and_hides_hash(
    test_engine: Any,
) -> None:
    email = "pytest.manager@smartmart.demo"

    with test_engine.begin() as connection:
        connection.execute(
            text(
                """
                DELETE FROM app_users
                WHERE email = :email;
                """
            ),
            {
                "email": email,
            },
        )

    try:
        first = create_app_user(
            email=" PyTest.Manager@SmartMart.Demo ",
            full_name="Pytest Manager",
            password="ExamplePassword!2026",
            role="Manager",
        )

        assert first["outcome"] == "success"
        assert first["user"]["email"] == email
        assert first["user"]["role"] == "Manager"
        assert "password_hash" not in first["user"]

        duplicate = create_app_user(
            email="PYTEST.MANAGER@SMARTMART.DEMO",
            full_name="Different Name",
            password="AnotherPassword!2026",
            role="Viewer",
        )

        assert duplicate["outcome"] == "duplicate"
        assert duplicate["user"]["email"] == email
        assert duplicate["user"]["role"] == "Manager"
        assert "password_hash" not in duplicate["user"]

        stored = get_app_user_by_email(
            email,
            include_password_hash=True,
        )

        assert stored is not None
        assert stored["password_hash"].startswith(
            "$argon2"
        )
        assert verify_password(
            "ExamplePassword!2026",
            stored["password_hash"],
        )

    finally:
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM app_users
                    WHERE email = :email;
                    """
                ),
                {
                    "email": email,
                },
            )

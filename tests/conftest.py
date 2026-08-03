from __future__ import annotations

import os
import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine, make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_ENV_FILE = PROJECT_ROOT / ".env.test"


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


DATABASE_ENVIRONMENT_KEYS = {
    "DATABASE_URL",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
}


def load_test_environment() -> None:
    """
    Load test database settings before importing the FastAPI app.

    Existing database-related environment variables are removed first
    so pytest cannot accidentally inherit development database settings.
    """

    if not TEST_ENV_FILE.exists():
        raise RuntimeError(
            "Missing .env.test file. Copy .env.example to .env.test, "
            "change the database name to "
            "'ai_operating_intelligence_test', and enter your local "
            "PostgreSQL password."
        )

    test_values = dotenv_values(TEST_ENV_FILE)

    for environment_key in DATABASE_ENVIRONMENT_KEYS:
        os.environ.pop(
            environment_key,
            None,
        )

    for key, value in test_values.items():
        if value is not None:
            os.environ[key] = value

    database_url = test_values.get("DATABASE_URL")

    if database_url:
        return

    database_name = (
        test_values.get("POSTGRES_DB")
        or test_values.get("DB_NAME")
    )
    database_user = (
        test_values.get("POSTGRES_USER")
        or test_values.get("DB_USER")
    )
    database_password = (
        test_values.get("POSTGRES_PASSWORD")
        or test_values.get("DB_PASSWORD")
    )

    missing_settings = []

    if not database_name:
        missing_settings.append(
            "POSTGRES_DB"
        )

    if not database_user:
        missing_settings.append(
            "POSTGRES_USER"
        )

    if not database_password:
        missing_settings.append(
            "POSTGRES_PASSWORD"
        )

    if missing_settings:
        raise RuntimeError(
            "Missing required test database settings in .env.test: "
            + ", ".join(missing_settings)
        )

    postgres_host = (
        test_values.get("POSTGRES_HOST")
        or test_values.get("DB_HOST")
        or "localhost"
    )
    postgres_port = (
        test_values.get("POSTGRES_PORT")
        or test_values.get("DB_PORT")
        or "5432"
    )

    os.environ["DB_HOST"] = postgres_host
    os.environ["DB_PORT"] = postgres_port
    os.environ["DB_NAME"] = database_name
    os.environ["DB_USER"] = database_user
    os.environ["DB_PASSWORD"] = database_password


load_test_environment()


# These imports must remain below load_test_environment().
# The application creates its SQLAlchemy engine during import.
from backend.database import get_database_url  # noqa: E402


resolved_database_url = get_database_url()
parsed_database_url = make_url(
    resolved_database_url
)

configured_database_name = (
    parsed_database_url.database or ""
)


if not configured_database_name.endswith("_test"):
    raise RuntimeError(
        "Unsafe pytest database configuration. "
        "The configured database name must end with '_test'. "
        f"Received: {configured_database_name!r}"
    )


# These imports must remain below the database safety checks.
from backend.app.db.database import engine  # noqa: E402
from backend.app.main import app  # noqa: E402


with engine.connect() as connection:
    actual_database_name = str(
        connection.execute(
            text(
                """
                SELECT current_database();
                """
            )
        ).scalar_one()
    )


if actual_database_name != configured_database_name:
    raise RuntimeError(
        "The connected PostgreSQL database does not match the "
        "configured test database. "
        f"Configured: {configured_database_name!r}; "
        f"connected: {actual_database_name!r}."
    )


if not actual_database_name.endswith("_test"):
    raise RuntimeError(
        "Pytest refused to continue because the active database "
        "is not a test database. "
        f"Connected database: {actual_database_name!r}"
    )


@pytest.fixture(scope="session")
def test_engine() -> Generator[
    Engine,
    None,
    None,
]:
    """Provide the verified PostgreSQL test engine."""

    yield engine

    engine.dispose()


@pytest.fixture()
def client(
    test_engine: Engine,
) -> Generator[
    TestClient,
    None,
    None,
]:
    """Provide a FastAPI TestClient using the test database."""

    del test_engine

    with TestClient(app) as test_client:
        yield test_client
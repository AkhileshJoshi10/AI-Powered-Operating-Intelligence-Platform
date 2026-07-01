from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


def get_database_url() -> str:
    """Build the PostgreSQL connection URL from local environment values."""

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database_name = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB")
    username = os.getenv("DB_USER") or os.getenv("POSTGRES_USER")
    password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")

    missing_values = []

    if not database_name:
        missing_values.append("DB_NAME")

    if not username:
        missing_values.append("DB_USER")

    if not password:
        missing_values.append("DB_PASSWORD")

    if missing_values:
        raise ValueError(
            "Missing database settings in .env: "
            + ", ".join(missing_values)
        )

    encoded_password = quote_plus(password)

    return (
        f"postgresql+psycopg2://{username}:{encoded_password}"
        f"@{host}:{port}/{database_name}"
    )


def get_database_engine() -> Engine:
    """Create and return a reusable PostgreSQL SQLAlchemy engine."""

    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
    )


def read_query(
    engine: Engine,
    query: str,
    parameters: Mapping[str, object] | None = None,
) -> pd.DataFrame:
    """Run a SQL query and return the result as a pandas DataFrame."""

    with engine.connect() as connection:
        return pd.read_sql(
            text(query),
            connection,
            params=parameters,
        )
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, URL, make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_ENV_FILE = PROJECT_ROOT / ".env.test"

EXPECTED_TEST_DATABASE = "ai_operating_intelligence_test"

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


def get_first_value(
    values: dict[str, str | None],
    *keys: str,
) -> str | None:
    """Return the first non-empty environment value."""

    for key in keys:
        value = values.get(key)

        if value is not None and value.strip():
            return value.strip()

    return None


def load_test_environment() -> URL:
    """
    Load and validate the isolated PostgreSQL test configuration.

    Supported formats:
    - DATABASE_URL
    - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    - POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB,
      POSTGRES_USER, POSTGRES_PASSWORD
    """

    if not TEST_ENV_FILE.exists():
        raise RuntimeError(
            "The .env.test file was not found. Create it before "
            "running the test-database seeder."
        )

    raw_values = dotenv_values(
        TEST_ENV_FILE
    )

    test_values: dict[str, str | None] = {
        str(key): value
        for key, value in raw_values.items()
    }

    for environment_key in DATABASE_ENVIRONMENT_KEYS:
        os.environ.pop(
            environment_key,
            None,
        )

    database_url_value = get_first_value(
        test_values,
        "DATABASE_URL",
    )

    if database_url_value is not None:
        database_url = make_url(
            database_url_value
        )

    else:
        database_host = get_first_value(
            test_values,
            "POSTGRES_HOST",
            "DB_HOST",
        )

        database_port = get_first_value(
            test_values,
            "POSTGRES_PORT",
            "DB_PORT",
        )

        database_name = get_first_value(
            test_values,
            "POSTGRES_DB",
            "DB_NAME",
        )

        database_user = get_first_value(
            test_values,
            "POSTGRES_USER",
            "DB_USER",
        )

        database_password = get_first_value(
            test_values,
            "POSTGRES_PASSWORD",
            "DB_PASSWORD",
        )

        missing_settings = []

        if database_host is None:
            missing_settings.append(
                "POSTGRES_HOST or DB_HOST"
            )

        if database_port is None:
            missing_settings.append(
                "POSTGRES_PORT or DB_PORT"
            )

        if database_name is None:
            missing_settings.append(
                "POSTGRES_DB or DB_NAME"
            )

        if database_user is None:
            missing_settings.append(
                "POSTGRES_USER or DB_USER"
            )

        if database_password is None:
            missing_settings.append(
                "POSTGRES_PASSWORD or DB_PASSWORD"
            )

        if missing_settings:
            raise RuntimeError(
                "The following test database settings are "
                "missing from .env.test: "
                + ", ".join(missing_settings)
            )

        try:
            port_number = int(
                database_port
            )

        except ValueError as error:
            raise RuntimeError(
                "The database port in .env.test must be "
                "a valid integer."
            ) from error

        database_url = URL.create(
            drivername="postgresql+psycopg2",
            username=database_user,
            password=database_password,
            host=database_host,
            port=port_number,
            database=database_name,
        )

    configured_database = (
        database_url.database
        or ""
    ).strip()

    if configured_database != EXPECTED_TEST_DATABASE:
        raise RuntimeError(
            "Unsafe database configuration detected. "
            f"Expected database '{EXPECTED_TEST_DATABASE}', "
            f"but .env.test specifies "
            f"'{configured_database or 'no database'}'."
        )

    if not configured_database.endswith(
        "_test"
    ):
        raise RuntimeError(
            "Unsafe database configuration detected. "
            "The configured database name must end with '_test'."
        )

    rendered_database_url = (
        database_url.render_as_string(
            hide_password=False
        )
    )

    os.environ["DATABASE_URL"] = (
        rendered_database_url
    )

    if database_url.host is not None:
        os.environ["POSTGRES_HOST"] = (
            database_url.host
        )
        os.environ["DB_HOST"] = (
            database_url.host
        )

    if database_url.port is not None:
        port_text = str(
            database_url.port
        )

        os.environ["POSTGRES_PORT"] = port_text
        os.environ["DB_PORT"] = port_text

    os.environ["POSTGRES_DB"] = (
        configured_database
    )
    os.environ["DB_NAME"] = (
        configured_database
    )

    if database_url.username is not None:
        os.environ["POSTGRES_USER"] = (
            database_url.username
        )
        os.environ["DB_USER"] = (
            database_url.username
        )

    if database_url.password is not None:
        os.environ["POSTGRES_PASSWORD"] = (
            database_url.password
        )
        os.environ["DB_PASSWORD"] = (
            database_url.password
        )

    return database_url


TEST_DATABASE_URL = load_test_environment()


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from backend.load_processed_data import (  # noqa: E402
    DATASETS,
    clear_existing_business_data,
    insert_import_log,
    prepare_dataset,
)


def verify_test_database_connection(
    connection: Connection,
) -> str:
    """Verify the configured and actual PostgreSQL databases."""

    actual_database = str(
        connection.execute(
            text(
                "SELECT current_database();"
            )
        ).scalar_one()
    )

    configured_database = (
        TEST_DATABASE_URL.database
        or ""
    )

    if actual_database != configured_database:
        raise RuntimeError(
            "Database connection mismatch. "
            f"The test configuration specifies "
            f"'{configured_database}', but PostgreSQL connected "
            f"to '{actual_database}'."
        )

    if actual_database != EXPECTED_TEST_DATABASE:
        raise RuntimeError(
            "Unsafe database connection detected. "
            "Seeding is allowed only for "
            f"'{EXPECTED_TEST_DATABASE}', not "
            f"'{actual_database}'."
        )

    if not actual_database.endswith(
        "_test"
    ):
        raise RuntimeError(
            "Unsafe database connection detected. "
            "The actual database name must end with '_test'."
        )

    return actual_database


def clear_existing_test_outputs(
    connection: Connection,
) -> None:
    """Clear records generated by previous integration-test runs."""

    connection.execute(
        text(
            """
            TRUNCATE TABLE
                automation_logs,
                tasks,
                recommendations,
                root_cause_analyses,
                issue_evidence,
                issues,
                executive_briefs,
                agent_runs,
                audit_logs,
                data_import_logs
            RESTART IDENTITY CASCADE;
            """
        )
    )


def prepare_all_datasets() -> list[dict[str, Any]]:
    """Read and prepare all processed datasets before deletion."""

    prepared_datasets: list[
        dict[str, Any]
    ] = []

    print(
        "Preparing processed datasets..."
    )
    print("-" * 60)

    for config in DATASETS:
        dataframe = prepare_dataset(
            config
        )

        prepared_datasets.append(
            {
                "config": config,
                "dataframe": dataframe,
            }
        )

        print(
            f"Prepared: {config['file_name']} "
            f"({len(dataframe)} rows)"
        )

    return prepared_datasets


def load_prepared_datasets(
    *,
    connection: Connection,
    prepared_datasets: list[dict[str, Any]],
) -> None:
    """Load all prepared datasets and create import logs."""

    print(
        "\nLoading processed datasets..."
    )
    print("-" * 60)

    for item in prepared_datasets:
        config = item["config"]
        dataframe = item["dataframe"]

        row_count = len(
            dataframe
        )

        dataframe.to_sql(
            name=config["table_name"],
            con=connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        insert_import_log(
            connection=connection,
            dataset_name=config["table_name"],
            source_file_name=config["file_name"],
            total_rows=row_count,
            successful_rows=row_count,
            failed_rows=0,
            import_status="Success",
            error_message=None,
        )

        print(
            f"Loaded: {config['table_name']} "
            f"({row_count} rows)"
        )


def verify_loaded_data(
    *,
    connection: Connection,
    prepared_datasets: list[dict[str, Any]],
) -> None:
    """Confirm that every table has the expected row count."""

    total_expected_rows = 0
    total_actual_rows = 0

    print(
        "\nVERIFIED TEST-DATABASE ROW COUNTS"
    )
    print("-" * 60)

    for item in prepared_datasets:
        config = item["config"]
        dataframe = item["dataframe"]

        table_name = config[
            "table_name"
        ]

        expected_rows = len(
            dataframe
        )

        actual_rows = int(
            connection.execute(
                text(
                    f"SELECT COUNT(*) "
                    f"FROM {table_name};"
                )
            ).scalar_one()
        )

        if actual_rows != expected_rows:
            raise RuntimeError(
                f"Row-count mismatch for table "
                f"'{table_name}'. Expected "
                f"{expected_rows}, but found "
                f"{actual_rows}."
            )

        total_expected_rows += (
            expected_rows
        )
        total_actual_rows += (
            actual_rows
        )

        print(
            f"{table_name}: {actual_rows} rows"
        )

    import_log_count = int(
        connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM data_import_logs
                WHERE import_status = 'Success';
                """
            )
        ).scalar_one()
    )

    expected_import_logs = len(
        prepared_datasets
    )

    if (
        import_log_count
        != expected_import_logs
    ):
        raise RuntimeError(
            "Import-log count mismatch. "
            f"Expected {expected_import_logs}, "
            f"but found {import_log_count}."
        )

    if (
        total_actual_rows
        != total_expected_rows
    ):
        raise RuntimeError(
            "Total row-count verification failed."
        )

    print("-" * 60)
    print(
        f"Total business records: "
        f"{total_actual_rows}"
    )
    print(
        f"Successful import logs: "
        f"{import_log_count}"
    )


def main() -> None:
    """Safely seed the isolated PostgreSQL test database."""

    prepared_datasets = (
        prepare_all_datasets()
    )

    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    try:
        print(
            "\nConnecting to PostgreSQL "
            "test database..."
        )

        with engine.begin() as connection:
            actual_database = (
                verify_test_database_connection(
                    connection
                )
            )

            print(
                f"Verified test database: "
                f"{actual_database}"
            )

            clear_existing_test_outputs(
                connection
            )

            clear_existing_business_data(
                connection
            )

            print(
                "Existing test records cleared."
            )

            load_prepared_datasets(
                connection=connection,
                prepared_datasets=(
                    prepared_datasets
                ),
            )

            verify_loaded_data(
                connection=connection,
                prepared_datasets=(
                    prepared_datasets
                ),
            )

        print(
            "\nTest database seeded successfully."
        )

    except Exception as error:
        print(
            "\nTest-database seeding failed."
        )
        print(
            f"Reason: {error}"
        )
        print(
            "The active transaction was rolled back."
        )

        raise

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
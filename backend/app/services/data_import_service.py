from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd
from fastapi import UploadFile
from sqlalchemy import MetaData, Table, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from backend.app.db.database import engine
from backend.data_cleaning import (
    DATASETS as CLEANING_DATASETS,
    clean_expiry_date,
    clean_shelf_life_days,
    create_initial_stats,
    create_product_perishability_map,
    normalize_remaining_missing_values,
    normalize_text_columns,
    remove_unneeded_columns,
    standardize_categorical_columns,
    standardize_id_columns,
    standardize_month_column,
    standardize_regular_date_column,
    standardize_regular_numeric_columns,
    validate_product_structure,
)
from backend.data_validation import (
    RAW_DATASET_FILES,
    validate_raw_datasets,
)
from backend.load_processed_data import (
    DATASETS as DATABASE_DATASETS,
    convert_date_columns,
    convert_numeric_columns,
    insert_import_log,
    standardize_missing_values,
    validate_columns,
)


MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024
UPSERT_CHUNK_SIZE = 1000


class ImportValidationError(ValueError):
    """Raised when an uploaded dataset fails validation."""

    def __init__(
        self,
        message: str,
        *,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        super().__init__(message)

        self.errors = errors or []
        self.warnings = warnings or []


def get_database_config(dataset_name: str) -> dict[str, Any]:
    """Return the loader configuration for one database table."""

    for config in DATABASE_DATASETS:
        if config["table_name"] == dataset_name:
            return config

    raise ValueError(
        f"No database loading configuration exists for "
        f"dataset '{dataset_name}'."
    )


def read_uploaded_csv(
    *,
    uploaded_file: UploadFile,
) -> tuple[str, pd.DataFrame]:
    """Read an uploaded CSV into a string-based DataFrame."""

    source_file_name = (
        uploaded_file.filename
        or "uploaded_dataset.csv"
    )

    file_extension = Path(
        source_file_name
    ).suffix.lower()

    if file_extension != ".csv":
        raise ValueError(
            "Only CSV files can be imported."
        )

    raise RuntimeError(
        "read_uploaded_csv must be called through "
        "read_uploaded_csv_async."
    )


async def read_uploaded_csv_async(
    *,
    uploaded_file: UploadFile,
) -> tuple[str, pd.DataFrame]:
    """Read and parse an uploaded CSV file."""

    source_file_name = (
        uploaded_file.filename
        or "uploaded_dataset.csv"
    )

    file_extension = Path(
        source_file_name
    ).suffix.lower()

    if file_extension != ".csv":
        raise ValueError(
            "Only CSV files can be imported."
        )

    file_content = await uploaded_file.read()

    if not file_content:
        raise ValueError(
            "The uploaded CSV file is empty."
        )

    if len(file_content) > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError(
            "The uploaded CSV file exceeds the 25 MB limit."
        )

    try:
        dataframe = pd.read_csv(
            BytesIO(file_content),
            dtype="string",
            keep_default_na=False,
        )

    except UnicodeDecodeError as error:
        raise ValueError(
            "The uploaded CSV must use UTF-8 compatible encoding."
        ) from error

    except pd.errors.EmptyDataError as error:
        raise ValueError(
            "The uploaded CSV does not contain data."
        ) from error

    except pd.errors.ParserError as error:
        raise ValueError(
            "The uploaded file is not a valid CSV."
        ) from error

    return source_file_name, dataframe


def load_product_perishability_map() -> dict[str, str]:
    """
    Read product perishability information from PostgreSQL.

    Inventory cleaning needs this relationship but does not add
    is_perishable to the inventory dataset.
    """

    query = text(
        """
        SELECT
            product_id,
            is_perishable
        FROM products;
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(
            query
        ).mappings().all()

    if not rows:
        raise ValueError(
            "Inventory cannot be imported because the products "
            "table does not contain perishability information."
        )

    return {
        str(row["product_id"]).strip().upper():
        str(row["is_perishable"]).strip()
        for row in rows
    }


def clean_uploaded_dataframe(
    *,
    dataset_name: str,
    raw_dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply the existing cleaning rules to an uploaded DataFrame."""

    raw_filename = RAW_DATASET_FILES[
        dataset_name
    ]

    if raw_filename not in CLEANING_DATASETS:
        raise ValueError(
            f"No cleaning configuration exists for "
            f"{raw_filename}."
        )

    config = CLEANING_DATASETS[
        raw_filename
    ]

    dataframe = raw_dataframe.copy()

    dataframe.columns = (
        dataframe.columns
        .str.strip()
        .str.lower()
        .str.replace(
            r"\s+",
            "_",
            regex=True,
        )
    )

    stats = create_initial_stats(
        raw_filename,
        config,
        dataframe,
    )

    dataframe = normalize_text_columns(
        dataframe,
        stats,
    )

    dataframe = standardize_id_columns(
        dataframe,
        stats,
    )

    dataframe = standardize_categorical_columns(
        dataframe,
        config,
        stats,
    )

    for column in config["date_columns"]:
        dataframe = standardize_regular_date_column(
            dataframe,
            raw_filename,
            column,
            stats,
        )

    for column in config["month_columns"]:
        dataframe = standardize_month_column(
            dataframe,
            raw_filename,
            column,
            stats,
        )

    dataframe = standardize_regular_numeric_columns(
        dataframe,
        raw_filename,
        config,
        stats,
    )

    protected_columns: set[str] = set()

    if raw_filename == "products_data.csv":
        validate_product_structure(
            dataframe
        )

        dataframe = clean_shelf_life_days(
            dataframe,
            stats,
        )

        create_product_perishability_map(
            dataframe
        )

        protected_columns.add(
            "shelf_life_days"
        )

    if raw_filename == "inventory_data.csv":
        product_perishability_map = (
            load_product_perishability_map()
        )

        dataframe = clean_expiry_date(
            dataframe,
            product_perishability_map,
            stats,
        )

        protected_columns.add(
            "expiry_date"
        )

    dataframe = remove_unneeded_columns(
        dataframe,
        config,
        stats,
    )

    dataframe = normalize_remaining_missing_values(
        dataframe,
        protected_columns,
        stats,
    )

    stats["duplicates_removed"] = int(
        dataframe.duplicated().sum()
    )

    dataframe = (
        dataframe
        .drop_duplicates()
        .reset_index(drop=True)
    )

    stats["final_rows"] = len(
        dataframe
    )

    return dataframe, stats


def prepare_cleaned_dataframe(
    *,
    dataset_name: str,
    cleaned_dataframe: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Validate the cleaned dataset against its expected database shape.

    This reuses the column, date and numeric validation functions
    from load_processed_data.py.
    """

    config = get_database_config(
        dataset_name
    )

    prepared_dataframe = (
        cleaned_dataframe.copy()
    )

    prepared_dataframe = standardize_missing_values(
        prepared_dataframe
    )

    prepared_dataframe = validate_columns(
        prepared_dataframe,
        config,
    )

    prepared_dataframe = convert_date_columns(
        prepared_dataframe,
        config,
    )

    prepared_dataframe = convert_numeric_columns(
        prepared_dataframe,
        config,
    )

    return prepared_dataframe, config


def convert_database_value(
    value: object,
) -> object:
    """Convert pandas and NumPy scalar values for SQLAlchemy."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (
        TypeError,
        ValueError,
    ):
        pass

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, np.generic):
        return value.item()

    if isinstance(
        value,
        (
            datetime,
            date,
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    return value


def dataframe_to_records(
    dataframe: pd.DataFrame,
) -> list[dict[str, object]]:
    """Convert a prepared DataFrame into SQLAlchemy records."""

    records: list[dict[str, object]] = []

    for raw_record in dataframe.to_dict(
        orient="records"
    ):
        records.append(
            {
                column_name: convert_database_value(
                    value
                )
                for column_name, value
                in raw_record.items()
            }
        )

    return records


def chunk_records(
    records: list[dict[str, object]],
    chunk_size: int,
) -> Iterator[list[dict[str, object]]]:
    """Yield records in database-safe batches."""

    for start_index in range(
        0,
        len(records),
        chunk_size,
    ):
        yield records[
            start_index:
            start_index + chunk_size
        ]


def upsert_dataframe(
    *,
    connection: Connection,
    table_name: str,
    dataframe: pd.DataFrame,
) -> int:
    """
    Insert new rows and update existing rows by primary key.

    No existing rows are deleted.
    """

    metadata = MetaData()

    table = Table(
        table_name,
        metadata,
        autoload_with=connection,
    )

    primary_key_columns = list(
        table.primary_key.columns
    )

    if not primary_key_columns:
        raise ValueError(
            f"Table '{table_name}' does not have a primary key."
        )

    primary_key_names = {
        column.name
        for column in primary_key_columns
    }

    update_column_names = [
        column.name
        for column in table.columns
        if column.name not in primary_key_names
        and column.name in dataframe.columns
    ]

    records = dataframe_to_records(
        dataframe
    )

    if not records:
        return 0

    imported_rows = 0

    for record_batch in chunk_records(
        records,
        UPSERT_CHUNK_SIZE,
    ):
        insert_statement = (
            postgresql_insert(table)
            .values(record_batch)
        )

        update_values = {
            column_name:
            insert_statement.excluded[
                column_name
            ]
            for column_name
            in update_column_names
        }

        if update_values:
            statement = (
                insert_statement
                .on_conflict_do_update(
                    index_elements=[
                        column.name
                        for column
                        in primary_key_columns
                    ],
                    set_=update_values,
                )
            )

        else:
            statement = (
                insert_statement
                .on_conflict_do_nothing(
                    index_elements=[
                        column.name
                        for column
                        in primary_key_columns
                    ],
                )
            )

        connection.execute(
            statement
        )

        imported_rows += len(
            record_batch
        )

    return imported_rows


def record_failed_import(
    *,
    dataset_name: str,
    source_file_name: str,
    total_rows: int,
    import_status: str,
    error_message: str,
) -> None:
    """Attempt to save a failed or rejected import log."""

    try:
        with engine.begin() as connection:
            insert_import_log(
                connection=connection,
                dataset_name=dataset_name,
                source_file_name=source_file_name,
                total_rows=total_rows,
                successful_rows=0,
                failed_rows=total_rows,
                import_status=import_status,
                error_message=error_message[:1000],
            )

    except SQLAlchemyError:
        pass


async def import_uploaded_dataset(
    *,
    dataset_name: str,
    uploaded_file: UploadFile,
) -> dict[str, Any]:
    """Validate, clean and upsert one uploaded business dataset."""

    if dataset_name not in RAW_DATASET_FILES:
        raise ValueError(
            f"Unsupported dataset name: {dataset_name}"
        )

    source_file_name = (
        uploaded_file.filename
        or RAW_DATASET_FILES[dataset_name]
    )

    total_rows = 0

    try:
        (
            source_file_name,
            raw_dataframe,
        ) = await read_uploaded_csv_async(
            uploaded_file=uploaded_file
        )

        total_rows = len(
            raw_dataframe
        )

        if total_rows == 0:
            raise ValueError(
                "The uploaded CSV does not contain any rows."
            )

        expected_raw_filename = (
            RAW_DATASET_FILES[
                dataset_name
            ]
        )

        raw_validation = (
            validate_raw_datasets(
                dataset_overrides={
                    expected_raw_filename:
                    raw_dataframe,
                },
                write_report=False,
            )
        )

        if not raw_validation[
            "is_valid"
        ]:
            raise ImportValidationError(
                "The uploaded dataset failed raw-data validation.",
                errors=raw_validation[
                    "errors"
                ],
                warnings=raw_validation[
                    "warnings"
                ],
            )

        (
            cleaned_dataframe,
            cleaning_stats,
        ) = clean_uploaded_dataframe(
            dataset_name=dataset_name,
            raw_dataframe=raw_dataframe,
        )

        (
            prepared_dataframe,
            database_config,
        ) = prepare_cleaned_dataframe(
            dataset_name=dataset_name,
            cleaned_dataframe=cleaned_dataframe,
        )

        successful_rows = len(
            prepared_dataframe
        )

        with engine.begin() as connection:
            imported_rows = upsert_dataframe(
                connection=connection,
                table_name=database_config[
                    "table_name"
                ],
                dataframe=prepared_dataframe,
            )

            insert_import_log(
                connection=connection,
                dataset_name=dataset_name,
                source_file_name=source_file_name,
                total_rows=total_rows,
                successful_rows=successful_rows,
                failed_rows=(
                    total_rows
                    - successful_rows
                ),
                import_status="Success",
                error_message=None,
            )

        return {
            "status": "success",
            "imported_at": datetime.now(),
            "dataset_name": dataset_name,
            "source_file_name": source_file_name,
            "destination_table": (
                database_config[
                    "table_name"
                ]
            ),
            "import_mode": "upsert",
            "total_rows": total_rows,
            "successful_rows": imported_rows,
            "failed_rows": (
                total_rows
                - imported_rows
            ),
            "raw_validation_warnings": (
                raw_validation[
                    "warnings"
                ]
            ),
            "cleaning_summary": (
                cleaning_stats
            ),
            "message": (
                f"{imported_rows} rows were imported into "
                f"{database_config['table_name']} using upsert mode."
            ),
        }

    except ImportValidationError as error:
        record_failed_import(
            dataset_name=dataset_name,
            source_file_name=source_file_name,
            total_rows=total_rows,
            import_status="Rejected",
            error_message=str(error),
        )

        raise

    except Exception as error:
        if total_rows > 0:
            record_failed_import(
                dataset_name=dataset_name,
                source_file_name=source_file_name,
                total_rows=total_rows,
                import_status="Failed",
                error_message=str(error),
            )

        raise
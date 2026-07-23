from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
from fastapi import UploadFile

from backend.data_validation import (
    RAW_DATASET_FILES,
    validate_raw_datasets,
)


MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024


async def validate_uploaded_dataset(
    *,
    dataset_name: str,
    uploaded_file: UploadFile,
) -> dict:
    """
    Validate an uploaded raw CSV without saving or importing it.

    The uploaded dataset temporarily replaces the matching raw
    dataset while the other raw datasets provide relationship data.
    """

    if dataset_name not in RAW_DATASET_FILES:
        raise ValueError(
            f"Unsupported dataset name: {dataset_name}"
        )

    source_file_name = (
        uploaded_file.filename
        or RAW_DATASET_FILES[dataset_name]
    )

    file_extension = Path(
        source_file_name
    ).suffix.lower()

    if file_extension != ".csv":
        raise ValueError(
            "Only CSV files can be validated."
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
        uploaded_dataframe = pd.read_csv(
            BytesIO(file_content)
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

    expected_filename = RAW_DATASET_FILES[
        dataset_name
    ]

    validation_result = validate_raw_datasets(
        dataset_overrides={
            expected_filename: uploaded_dataframe,
        },
        write_report=False,
    )

    return {
        "status": (
            "valid"
            if validation_result["is_valid"]
            else "invalid"
        ),
        "validated_at": datetime.now(),
        "dataset_name": dataset_name,
        "source_file_name": source_file_name,
        "validation_scope": (
            "Uploaded dataset with existing reference datasets"
        ),
        "total_rows": len(uploaded_dataframe),
        "total_columns": len(
            uploaded_dataframe.columns
        ),
        "is_valid": validation_result["is_valid"],
        "error_count": validation_result["error_count"],
        "warning_count": validation_result["warning_count"],
        "errors": validation_result["errors"],
        "warnings": validation_result["warnings"],
        "dataset_summary": validation_result["summary"],
    }
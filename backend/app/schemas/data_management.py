from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DatasetName = Literal[
    "products",
    "stores",
    "vendors",
    "employees",
    "sales",
    "inventory",
    "complaints",
    "finance",
    "vendor_deliveries",
]


class DataValidationResponse(BaseModel):
    """Result of validating one uploaded raw CSV dataset."""

    status: Literal[
        "valid",
        "invalid",
    ]

    validated_at: datetime

    dataset_name: DatasetName
    source_file_name: str

    validation_scope: str = Field(
        default="Uploaded dataset with existing reference datasets"
    )

    total_rows: int
    total_columns: int

    is_valid: bool
    error_count: int
    warning_count: int

    errors: list[str]
    warnings: list[str]
    dataset_summary: list[str]


class DataImportResponse(BaseModel):
    """Result of a controlled dataset import."""

    status: Literal["success"]
    imported_at: datetime

    dataset_name: DatasetName
    source_file_name: str
    destination_table: str

    import_mode: Literal["upsert"] = "upsert"

    total_rows: int
    successful_rows: int
    failed_rows: int

    raw_validation_warnings: list[str]
    cleaning_summary: dict[str, Any]

    message: str


class DataImportHistoryItem(BaseModel):
    """One historical dataset-import record."""

    import_id: int
    dataset_name: str
    source_file_name: str

    total_rows: int
    successful_rows: int
    failed_rows: int

    import_status: str
    error_message: str | None = None

    imported_at: datetime


class DataImportHistoryResponse(BaseModel):
    """Paginated dataset-import history."""

    status: Literal["success"] = "success"
    generated_at: datetime

    total_records: int
    matching_records: int

    limit: int
    offset: int

    imports: list[DataImportHistoryItem]
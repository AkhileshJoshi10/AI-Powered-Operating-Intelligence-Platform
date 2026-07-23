from __future__ import annotations

from datetime import datetime
from typing import Literal

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
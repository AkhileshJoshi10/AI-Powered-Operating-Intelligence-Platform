from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


InventorySeverity = Literal[
    "High",
    "Medium",
    "Low",
]


class InventoryFinding(BaseModel):
    """One inventory-related analytical finding."""

    finding_id: str
    analysis_type: str
    business_area: str
    severity: InventorySeverity

    entity_type: str
    entity_id: str

    store_id: str
    store_name: str
    product_id: str
    product_name: str

    vendor_id: str | None = None
    vendor_name: str | None = None

    inventory_date: date | None = None
    expiry_date: date | None = None
    days_to_expiry: int | None = None

    current_stock: float | None = None
    reorder_level: float | None = None
    stock_ratio: float | None = None

    stock_status: str
    reorder_required: str

    related_complaints: int
    high_severity_complaints: int

    summary: str
    evidence: str
    status: str
    detected_at: datetime


class InventoryFindingSummary(BaseModel):
    """Count of inventory findings by type and severity."""

    analysis_type: str
    severity: InventorySeverity
    finding_count: int


class InventoryAnalyticsResponse(BaseModel):
    """Response returned by the inventory analytics endpoint."""

    status: str = Field(default="success")
    generated_at: datetime

    total_findings: int
    matching_findings: int

    limit: int
    offset: int

    summary: list[InventoryFindingSummary]
    findings: list[InventoryFinding]
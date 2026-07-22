from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SalesSeverity = Literal[
    "High",
    "Medium",
    "Low",
]


class SalesFinding(BaseModel):
    """One sales-related analytical finding."""

    finding_id: str
    analysis_type: str
    business_area: str
    severity: SalesSeverity

    entity_type: str
    entity_id: str
    entity_name: str

    store_id: str | None = None
    store_name: str | None = None
    product_id: str | None = None
    product_name: str | None = None
    region: str | None = None
    category: str | None = None

    month: str | None = None
    previous_month: str | None = None

    current_sales: float | None = None
    previous_sales: float | None = None
    sales_change_percent: float | None = None

    benchmark_value: float | None = None
    benchmark_label: str | None = None
    target_achievement_percent: float | None = None

    summary: str
    evidence: str
    status: str
    detected_at: datetime


class SalesFindingSummary(BaseModel):
    """Count of findings by analysis type and severity."""

    analysis_type: str
    severity: SalesSeverity
    finding_count: int


class SalesAnalyticsResponse(BaseModel):
    """Response returned by GET /api/analytics/sales."""

    status: str = Field(default="success")
    generated_at: datetime

    total_findings: int
    matching_findings: int

    limit: int
    offset: int

    summary: list[SalesFindingSummary]
    findings: list[SalesFinding]
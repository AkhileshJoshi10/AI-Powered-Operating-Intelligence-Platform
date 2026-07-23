from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


VendorFinanceSeverity = Literal[
    "High",
    "Medium",
    "Low",
]


class VendorFinding(BaseModel):
    """One vendor or procurement analytical finding."""

    finding_id: str
    analysis_type: str
    business_area: Literal["Procurement"]
    severity: VendorFinanceSeverity

    entity_type: str
    entity_id: str
    entity_name: str

    vendor_id: str
    vendor_name: str

    delivery_count: int | None = None
    delayed_deliveries: int | None = None
    partial_deliveries: int | None = None

    average_delay_days: float | None = None
    maximum_delay_days: float | None = None
    average_quality_rating: float | None = None
    on_time_delivery_rate: float | None = None

    summary: str
    evidence: str
    status: str
    detected_at: datetime


class FinanceFinding(BaseModel):
    """One store-finance analytical finding."""

    finding_id: str
    analysis_type: str
    business_area: Literal["Finance"]
    severity: VendorFinanceSeverity

    entity_type: str
    entity_id: str
    entity_name: str

    store_id: str
    store_name: str
    month: str

    total_revenue: float | None = None
    operating_profit: float | None = None
    operating_profit_margin_percent: float | None = None
    target_achievement_percent: float | None = None
    risk_status: str | None = None

    summary: str
    evidence: str
    status: str
    detected_at: datetime


class VendorFinanceFindingSummary(BaseModel):
    """Count of findings by analysis type and severity."""

    analysis_type: str
    severity: VendorFinanceSeverity
    finding_count: int


class VendorAnalyticsResponse(BaseModel):
    """Response returned by GET /api/analytics/vendors."""

    status: str = Field(default="success")
    generated_at: datetime

    total_findings: int
    matching_findings: int

    limit: int
    offset: int

    summary: list[VendorFinanceFindingSummary]
    findings: list[VendorFinding]


class FinanceAnalyticsResponse(BaseModel):
    """Response returned by GET /api/analytics/finance."""

    status: str = Field(default="success")
    generated_at: datetime

    total_findings: int
    matching_findings: int

    limit: int
    offset: int

    summary: list[VendorFinanceFindingSummary]
    findings: list[FinanceFinding]
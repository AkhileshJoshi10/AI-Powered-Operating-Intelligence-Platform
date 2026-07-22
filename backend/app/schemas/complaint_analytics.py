from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


ComplaintFindingSeverity = Literal[
    "High",
    "Medium",
    "Low",
]


class ComplaintFinding(BaseModel):
    """One complaint-related analytical finding."""

    finding_id: str
    analysis_type: str
    business_area: str
    severity: ComplaintFindingSeverity

    entity_type: str
    entity_id: str
    entity_name: str

    store_id: str | None = None
    store_name: str | None = None
    product_id: str | None = None
    product_name: str | None = None
    region: str | None = None

    complaint_id: str | None = None
    complaint_type: str | None = None
    complaint_severity: str | None = None
    complaint_status: str | None = None
    complaint_date: date | None = None
    complaint_age_days: int | None = None

    total_complaints: int | None = None
    high_severity_complaints: int | None = None
    unresolved_complaints: int | None = None

    monthly_growth_percent: float | None = None
    benchmark_value: float | None = None
    benchmark_label: str | None = None

    summary: str
    evidence: str
    status: str
    detected_at: datetime


class ComplaintFindingSummary(BaseModel):
    """Count of complaint findings by analysis type and severity."""

    analysis_type: str
    severity: ComplaintFindingSeverity
    finding_count: int


class ComplaintAnalyticsResponse(BaseModel):
    """Response returned by the complaint analytics endpoint."""

    status: str = Field(default="success")
    generated_at: datetime

    total_findings: int
    matching_findings: int

    limit: int
    offset: int

    summary: list[ComplaintFindingSummary]
    findings: list[ComplaintFinding]
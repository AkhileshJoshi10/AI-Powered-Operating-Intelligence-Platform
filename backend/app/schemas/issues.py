from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IssueItem(BaseModel):
    """Summary and status information for one business issue."""

    issue_id: str
    title: str
    issue_type: str
    business_area: str
    priority_level: str
    priority_score: float
    priority_reason: str | None = None
    status: str

    entity_type: str | None = None
    entity_id: str | None = None
    store_id: str | None = None
    product_id: str | None = None
    vendor_id: str | None = None
    period_label: str | None = None

    finding_count: int
    high_finding_count: int
    medium_finding_count: int
    low_finding_count: int

    root_cause_status: str
    summary: str | None = None
    evidence_summary: str | None = None

    created_at: datetime
    updated_at: datetime
    last_detected_at: datetime


class IssueEvidenceItem(BaseModel):
    """One analytical finding supporting an issue."""

    evidence_id: int
    source_finding_id: str
    source_report: str
    source_module: str

    analysis_type: str | None = None
    business_area: str | None = None
    severity: str | None = None

    entity_type: str | None = None
    entity_id: str | None = None
    store_id: str | None = None
    product_id: str | None = None
    vendor_id: str | None = None

    summary: str | None = None
    evidence: str | None = None
    detected_at: datetime | None = None
    created_at: datetime


class RootCauseItem(BaseModel):
    """Current root-cause analysis linked to an issue."""

    root_cause_analysis_id: int
    root_cause_category: str
    root_cause_summary: str
    root_cause_explanation: str
    confidence_score: float
    evidence_count: int
    analysis_status: str
    review_status: str
    analysis_version: int
    generated_at: datetime
    reviewed_at: datetime | None = None
    updated_at: datetime


class IssueListResponse(BaseModel):
    """Paginated response returned by GET /api/issues."""

    status: str = Field(default="success")
    total_items: int
    limit: int
    offset: int
    items: list[IssueItem]


class IssueDetailResponse(BaseModel):
    """Detailed response returned for one issue."""

    status: str = Field(default="success")
    issue: IssueItem
    evidence_count: int
    evidence: list[IssueEvidenceItem]
    root_cause: RootCauseItem | None = None
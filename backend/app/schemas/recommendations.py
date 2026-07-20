from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RecommendationItem(BaseModel):
    """Summary information for one recommendation."""

    recommendation_id: int
    issue_id: str

    recommendation_title: str
    suggested_owner_role: str | None = None
    suggested_deadline: date | None = None
    expected_impact: str | None = None
    confidence_score: float | None = None
    status: str

    issue_title: str
    business_area: str
    priority_level: str
    priority_score: float

    created_at: datetime
    updated_at: datetime


class RecommendationDetail(BaseModel):
    """Complete recommendation and its supporting context."""

    recommendation_id: int
    issue_id: str

    recommendation_title: str
    recommendation_text: str
    suggested_owner_role: str | None = None
    suggested_deadline: date | None = None
    expected_impact: str | None = None
    confidence_score: float | None = None
    status: str

    issue_title: str
    issue_type: str
    business_area: str
    priority_level: str
    priority_score: float
    issue_status: str

    root_cause_category: str | None = None
    root_cause_summary: str | None = None
    root_cause_explanation: str | None = None
    root_cause_confidence: float | None = None
    root_cause_review_status: str | None = None

    created_at: datetime
    updated_at: datetime


class RecommendationEditRequest(BaseModel):
    """Fields that a manager may edit before accepting a recommendation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    recommendation_title: str | None = Field(
        default=None,
        min_length=5,
        max_length=500,
    )
    recommendation_text: str | None = Field(
        default=None,
        min_length=10,
        max_length=10000,
    )
    suggested_owner_role: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    suggested_deadline: date | None = None
    expected_impact: str | None = Field(
        default=None,
        min_length=5,
        max_length=5000,
    )


class RecommendationListResponse(BaseModel):
    """Paginated response returned by GET /api/recommendations."""

    status: str = Field(default="success")
    total_items: int
    limit: int
    offset: int
    items: list[RecommendationItem]


class RecommendationDetailResponse(BaseModel):
    """Response returned for one recommendation."""

    status: str = Field(default="success")
    recommendation: RecommendationDetail
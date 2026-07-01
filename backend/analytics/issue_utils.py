from __future__ import annotations

from datetime import datetime

import pandas as pd

from backend.analytics.date_utils import normalize_text
from backend.analytics.thresholds import (
    PRIORITY_HIGH_THRESHOLD,
    PRIORITY_MEDIUM_THRESHOLD,
)


ISSUE_COLUMNS = [
    "issue_id",
    "issue_type",
    "department",
    "title",
    "description",
    "priority",
    "priority_score",
    "impact_score",
    "urgency_score",
    "financial_risk_score",
    "customer_impact_score",
    "operational_risk_score",
    "confidence_score",
    "affected_store_id",
    "affected_product_id",
    "entity_type",
    "entity_id",
    "evidence",
    "status",
    "detection_source",
    "detected_date",
    "detected_at",
]


def safe_float(value: object) -> float:
    """Convert a value safely to float."""

    if pd.isna(value):
        return 0.0

    return float(value)


def safe_int(value: object) -> int:
    """Convert a value safely to integer."""

    if pd.isna(value):
        return 0

    return int(value)


def get_priority(priority_score: float) -> str:
    """Convert a numerical priority score into High, Medium, or Low."""

    if priority_score >= PRIORITY_HIGH_THRESHOLD:
        return "High"

    if priority_score >= PRIORITY_MEDIUM_THRESHOLD:
        return "Medium"

    return "Low"


def create_issue(
    *,
    issue_id: str,
    issue_type: str,
    department: str,
    priority_score: float,
    entity_type: str,
    entity_id: str,
    title: str,
    description: str,
    evidence: str,
    affected_store_id: str | None = None,
    affected_product_id: str | None = None,
    impact_score: float | None = None,
    urgency_score: float | None = None,
    financial_risk_score: float | None = None,
    customer_impact_score: float | None = None,
    operational_risk_score: float | None = None,
    confidence_score: float | None = None,
    status: str = "New",
    detection_source: str = "Rule-Based Analytics Engine",
) -> dict:
    """Create one standardized business issue record."""

    detected_at = datetime.now()

    return {
        "issue_id": normalize_text(issue_id),
        "issue_type": normalize_text(issue_type),
        "department": normalize_text(department),
        "title": normalize_text(title),
        "description": normalize_text(description),
        "priority": get_priority(priority_score),
        "priority_score": round(safe_float(priority_score), 2),
        "impact_score": impact_score,
        "urgency_score": urgency_score,
        "financial_risk_score": financial_risk_score,
        "customer_impact_score": customer_impact_score,
        "operational_risk_score": operational_risk_score,
        "confidence_score": confidence_score,
        "affected_store_id": (
            normalize_text(affected_store_id)
            if affected_store_id
            else None
        ),
        "affected_product_id": (
            normalize_text(affected_product_id)
            if affected_product_id
            else None
        ),
        "entity_type": normalize_text(entity_type),
        "entity_id": normalize_text(entity_id),
        "evidence": normalize_text(evidence),
        "status": normalize_text(status),
        "detection_source": normalize_text(detection_source),
        "detected_date": detected_at.strftime("%Y-%m-%d"),
        "detected_at": detected_at.strftime("%Y-%m-%d %H:%M:%S"),
    }
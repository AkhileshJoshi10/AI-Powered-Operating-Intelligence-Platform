from __future__ import annotations

from datetime import datetime

import pandas as pd

from backend.analytics.sales_analysis import run_sales_analysis
from backend.app.db.database import engine


SEVERITY_ORDER = {
    "High": 1,
    "Medium": 2,
    "Low": 3,
}


def is_missing(value: object) -> bool:
    """Return True when a pandas or Python value is missing."""

    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def clean_required_text(value: object) -> str:
    """Convert a required value safely to clean text."""

    if is_missing(value):
        return ""

    return " ".join(str(value).split())


def clean_optional_text(value: object) -> str | None:
    """Convert an optional value to clean text or None."""

    if is_missing(value):
        return None

    cleaned_value = " ".join(str(value).split())

    if not cleaned_value:
        return None

    return cleaned_value


def clean_optional_float(value: object) -> float | None:
    """Convert an optional numeric value to float."""

    if is_missing(value):
        return None

    return round(float(value), 2)


def clean_datetime(value: object) -> datetime:
    """Convert a finding timestamp into a datetime object."""

    if isinstance(value, datetime):
        return value

    return datetime.fromisoformat(str(value))


def build_sales_finding_record(row: object) -> dict:
    """Convert one pandas row into a JSON-compatible finding."""

    return {
        "finding_id": clean_required_text(row.finding_id),
        "analysis_type": clean_required_text(row.analysis_type),
        "business_area": clean_required_text(row.business_area),
        "severity": clean_required_text(row.severity),
        "entity_type": clean_required_text(row.entity_type),
        "entity_id": clean_required_text(row.entity_id),
        "entity_name": clean_required_text(row.entity_name),
        "store_id": clean_optional_text(row.store_id),
        "store_name": clean_optional_text(row.store_name),
        "product_id": clean_optional_text(row.product_id),
        "product_name": clean_optional_text(row.product_name),
        "region": clean_optional_text(row.region),
        "category": clean_optional_text(row.category),
        "month": clean_optional_text(row.month),
        "previous_month": clean_optional_text(row.previous_month),
        "current_sales": clean_optional_float(row.current_sales),
        "previous_sales": clean_optional_float(row.previous_sales),
        "sales_change_percent": clean_optional_float(
            row.sales_change_percent
        ),
        "benchmark_value": clean_optional_float(
            row.benchmark_value
        ),
        "benchmark_label": clean_optional_text(
            row.benchmark_label
        ),
        "target_achievement_percent": clean_optional_float(
            row.target_achievement_percent
        ),
        "summary": clean_required_text(row.summary),
        "evidence": clean_required_text(row.evidence),
        "status": clean_required_text(row.status),
        "detected_at": clean_datetime(row.detected_at),
    }


def get_sales_analytics(
    *,
    severity: str | None,
    analysis_type: str | None,
    limit: int,
    offset: int,
) -> dict:
    """Run and return the current sales analytics findings."""

    findings_dataframe = run_sales_analysis(engine)

    total_findings = len(findings_dataframe)

    filtered_findings = findings_dataframe.copy()

    if severity is not None:
        filtered_findings = filtered_findings[
            filtered_findings["severity"] == severity
        ]

    if analysis_type is not None:
        normalized_analysis_type = (
            analysis_type.strip().casefold()
        )

        analysis_type_values = filtered_findings[
            "analysis_type"
        ].map(
            lambda value: str(value).strip().casefold()
        )

        filtered_findings = filtered_findings[
            analysis_type_values == normalized_analysis_type
        ]

    filtered_findings = filtered_findings.reset_index(
        drop=True
    )

    matching_findings = len(filtered_findings)

    if filtered_findings.empty:
        summary_records = []
    else:
        summary_dataframe = (
            filtered_findings.groupby(
                [
                    "analysis_type",
                    "severity",
                ],
                dropna=False,
            )
            .size()
            .reset_index(name="finding_count")
        )

        summary_dataframe["severity_order"] = (
            summary_dataframe["severity"].map(
                SEVERITY_ORDER
            )
        )

        summary_dataframe = summary_dataframe.sort_values(
            by=[
                "severity_order",
                "analysis_type",
            ],
            ascending=[
                True,
                True,
            ],
        ).drop(
            columns=["severity_order"]
        )

        summary_records = [
            {
                "analysis_type": clean_required_text(
                    row.analysis_type
                ),
                "severity": clean_required_text(
                    row.severity
                ),
                "finding_count": int(
                    row.finding_count
                ),
            }
            for row in summary_dataframe.itertuples(
                index=False
            )
        ]

    paginated_findings = filtered_findings.iloc[
        offset:offset + limit
    ]

    finding_records = [
        build_sales_finding_record(row)
        for row in paginated_findings.itertuples(
            index=False
        )
    ]

    return {
        "status": "success",
        "generated_at": datetime.now(),
        "total_findings": total_findings,
        "matching_findings": matching_findings,
        "limit": limit,
        "offset": offset,
        "summary": summary_records,
        "findings": finding_records,
    }
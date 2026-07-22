from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from backend.analytics.inventory_analysis import (
    run_inventory_analysis,
)
from backend.app.db.database import engine


SEVERITY_ORDER = {
    "High": 1,
    "Medium": 2,
    "Low": 3,
}


def is_missing(value: object) -> bool:
    """Return True when a Python or pandas value is missing."""

    if value is None:
        return True

    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def clean_required_text(value: object) -> str:
    """Convert a required value to clean text."""

    if is_missing(value):
        return ""

    return " ".join(str(value).split())


def clean_optional_text(value: object) -> str | None:
    """Convert an optional value to clean text."""

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


def clean_optional_int(value: object) -> int | None:
    """Convert an optional numeric value to integer."""

    if is_missing(value):
        return None

    return int(value)


def clean_optional_date(value: object) -> date | None:
    """Convert an optional date-like value into a date."""

    if is_missing(value):
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    parsed_value = pd.to_datetime(
        value,
        errors="raise",
    )

    return parsed_value.date()


def clean_datetime(value: object) -> datetime:
    """Convert a finding timestamp into a datetime."""

    if isinstance(value, datetime):
        return value

    parsed_value = pd.to_datetime(
        value,
        errors="raise",
    )

    return parsed_value.to_pydatetime()


def apply_exact_text_filter(
    dataframe: pd.DataFrame,
    *,
    column_name: str,
    filter_value: str | None,
) -> pd.DataFrame:
    """Apply a case-insensitive exact-text filter."""

    if filter_value is None:
        return dataframe

    normalized_filter = filter_value.strip().casefold()

    normalized_column = (
        dataframe[column_name]
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    return dataframe[
        normalized_column == normalized_filter
    ]


def build_inventory_finding_record(row: object) -> dict:
    """Convert one pandas row into a JSON-compatible record."""

    return {
        "finding_id": clean_required_text(row.finding_id),
        "analysis_type": clean_required_text(row.analysis_type),
        "business_area": clean_required_text(row.business_area),
        "severity": clean_required_text(row.severity),
        "entity_type": clean_required_text(row.entity_type),
        "entity_id": clean_required_text(row.entity_id),
        "store_id": clean_required_text(row.store_id),
        "store_name": clean_required_text(row.store_name),
        "product_id": clean_required_text(row.product_id),
        "product_name": clean_required_text(row.product_name),
        "vendor_id": clean_optional_text(row.vendor_id),
        "vendor_name": clean_optional_text(row.vendor_name),
        "inventory_date": clean_optional_date(
            row.inventory_date
        ),
        "expiry_date": clean_optional_date(row.expiry_date),
        "days_to_expiry": clean_optional_int(
            row.days_to_expiry
        ),
        "current_stock": clean_optional_float(
            row.current_stock
        ),
        "reorder_level": clean_optional_float(
            row.reorder_level
        ),
        "stock_ratio": clean_optional_float(row.stock_ratio),
        "stock_status": clean_required_text(row.stock_status),
        "reorder_required": clean_required_text(
            row.reorder_required
        ),
        "related_complaints": int(
            row.related_complaints
        ),
        "high_severity_complaints": int(
            row.high_severity_complaints
        ),
        "summary": clean_required_text(row.summary),
        "evidence": clean_required_text(row.evidence),
        "status": clean_required_text(row.status),
        "detected_at": clean_datetime(row.detected_at),
    }


def build_inventory_summary(
    findings: pd.DataFrame,
) -> list[dict]:
    """Build counts by analysis type and severity."""

    if findings.empty:
        return []

    summary_dataframe = (
        findings.groupby(
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

    return [
        {
            "analysis_type": clean_required_text(
                row.analysis_type
            ),
            "severity": clean_required_text(row.severity),
            "finding_count": int(row.finding_count),
        }
        for row in summary_dataframe.itertuples(index=False)
    ]


def get_inventory_analytics(
    *,
    severity: str | None,
    analysis_type: str | None,
    store_id: str | None,
    product_id: str | None,
    vendor_id: str | None,
    limit: int,
    offset: int,
) -> dict:
    """Run and return current inventory analytics findings."""

    findings_dataframe = run_inventory_analysis(engine)

    total_findings = len(findings_dataframe)

    filtered_findings = findings_dataframe.copy()

    filtered_findings = apply_exact_text_filter(
        filtered_findings,
        column_name="severity",
        filter_value=severity,
    )

    filtered_findings = apply_exact_text_filter(
        filtered_findings,
        column_name="analysis_type",
        filter_value=analysis_type,
    )

    filtered_findings = apply_exact_text_filter(
        filtered_findings,
        column_name="store_id",
        filter_value=store_id,
    )

    filtered_findings = apply_exact_text_filter(
        filtered_findings,
        column_name="product_id",
        filter_value=product_id,
    )

    filtered_findings = apply_exact_text_filter(
        filtered_findings,
        column_name="vendor_id",
        filter_value=vendor_id,
    )

    filtered_findings = filtered_findings.reset_index(
        drop=True
    )

    matching_findings = len(filtered_findings)

    summary_records = build_inventory_summary(
        filtered_findings
    )

    paginated_findings = filtered_findings.iloc[
        offset:offset + limit
    ]

    finding_records = [
        build_inventory_finding_record(row)
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
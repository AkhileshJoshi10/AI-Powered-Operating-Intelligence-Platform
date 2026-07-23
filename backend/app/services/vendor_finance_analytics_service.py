from __future__ import annotations

from datetime import datetime

import pandas as pd

from backend.analytics.vendor_finance_analysis import (
    FINDING_COLUMNS,
    detect_high_financial_risk,
    detect_low_on_time_delivery_rate,
    detect_low_operating_profit,
    detect_low_target_achievement,
    detect_low_vendor_quality,
    detect_loss_making_store_months,
    detect_partial_deliveries,
    detect_repeated_vendor_delays,
    get_latest_finance_snapshot,
    get_vendor_snapshot,
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
    """Convert a required value into clean text."""

    if is_missing(value):
        return ""

    return " ".join(str(value).split())


def clean_optional_text(value: object) -> str | None:
    """Convert an optional value into clean text or None."""

    if is_missing(value):
        return None

    cleaned_value = " ".join(str(value).split())

    if not cleaned_value:
        return None

    return cleaned_value


def clean_optional_float(value: object) -> float | None:
    """Convert an optional numeric value into a float."""

    if is_missing(value):
        return None

    return round(float(value), 2)


def clean_optional_int(value: object) -> int | None:
    """Convert an optional numeric value into an integer."""

    if is_missing(value):
        return None

    return int(value)


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
        .fillna("")
        .astype(str)
        .str.strip()
        .str.casefold()
    )

    return dataframe[
        normalized_column == normalized_filter
    ]


def create_findings_dataframe(
    findings: list[dict],
) -> pd.DataFrame:
    """Create and sort a standardized findings DataFrame."""

    findings_dataframe = pd.DataFrame(
        findings,
        columns=FINDING_COLUMNS,
    )

    if findings_dataframe.empty:
        return findings_dataframe

    findings_dataframe["severity_order"] = (
        findings_dataframe["severity"].map(
            SEVERITY_ORDER
        )
    )

    findings_dataframe = findings_dataframe.sort_values(
        by=[
            "severity_order",
            "analysis_type",
            "average_delay_days",
            "target_achievement_percent",
        ],
        ascending=[
            True,
            True,
            False,
            True,
        ],
        na_position="last",
    ).drop(
        columns=["severity_order"]
    )

    return findings_dataframe.reset_index(drop=True)


def run_vendor_analysis() -> pd.DataFrame:
    """Run only the existing vendor and procurement rules."""

    print("Reading vendor performance data...")
    vendor_snapshot = get_vendor_snapshot(engine)

    findings: list[dict] = []

    print("Analyzing repeated vendor delays...")
    findings.extend(
        detect_repeated_vendor_delays(
            vendor_snapshot
        )
    )

    print("Analyzing partial vendor deliveries...")
    findings.extend(
        detect_partial_deliveries(
            vendor_snapshot
        )
    )

    print("Analyzing low vendor quality...")
    findings.extend(
        detect_low_vendor_quality(
            vendor_snapshot
        )
    )

    print("Analyzing on-time delivery rates...")
    findings.extend(
        detect_low_on_time_delivery_rate(
            vendor_snapshot
        )
    )

    return create_findings_dataframe(findings)


def run_finance_analysis() -> pd.DataFrame:
    """Run only the existing store-finance rules."""

    print("Reading latest finance data...")
    finance_snapshot = get_latest_finance_snapshot(
        engine
    )

    findings: list[dict] = []

    print("Analyzing low operating profit...")
    findings.extend(
        detect_low_operating_profit(
            finance_snapshot
        )
    )

    print("Analyzing loss-making stores...")
    findings.extend(
        detect_loss_making_store_months(
            finance_snapshot
        )
    )

    print("Analyzing low target achievement...")
    findings.extend(
        detect_low_target_achievement(
            finance_snapshot
        )
    )

    print("Analyzing high financial-risk stores...")
    findings.extend(
        detect_high_financial_risk(
            finance_snapshot
        )
    )

    return create_findings_dataframe(findings)


def build_finding_summary(
    findings: pd.DataFrame,
) -> list[dict]:
    """Build finding counts by analysis type and severity."""

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
        na_position="last",
    ).drop(
        columns=["severity_order"]
    )

    return [
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


def build_vendor_finding_record(row: object) -> dict:
    """Convert one vendor finding into JSON-compatible data."""

    return {
        "finding_id": clean_required_text(
            row.finding_id
        ),
        "analysis_type": clean_required_text(
            row.analysis_type
        ),
        "business_area": clean_required_text(
            row.business_area
        ),
        "severity": clean_required_text(
            row.severity
        ),
        "entity_type": clean_required_text(
            row.entity_type
        ),
        "entity_id": clean_required_text(
            row.entity_id
        ),
        "entity_name": clean_required_text(
            row.entity_name
        ),
        "vendor_id": clean_required_text(
            row.vendor_id
        ),
        "vendor_name": clean_required_text(
            row.vendor_name
        ),
        "delivery_count": clean_optional_int(
            row.delivery_count
        ),
        "delayed_deliveries": clean_optional_int(
            row.delayed_deliveries
        ),
        "partial_deliveries": clean_optional_int(
            row.partial_deliveries
        ),
        "average_delay_days": clean_optional_float(
            row.average_delay_days
        ),
        "maximum_delay_days": clean_optional_float(
            row.maximum_delay_days
        ),
        "average_quality_rating": clean_optional_float(
            row.average_quality_rating
        ),
        "on_time_delivery_rate": clean_optional_float(
            row.on_time_delivery_rate
        ),
        "summary": clean_required_text(
            row.summary
        ),
        "evidence": clean_required_text(
            row.evidence
        ),
        "status": clean_required_text(
            row.status
        ),
        "detected_at": clean_datetime(
            row.detected_at
        ),
    }


def build_finance_finding_record(row: object) -> dict:
    """Convert one finance finding into JSON-compatible data."""

    return {
        "finding_id": clean_required_text(
            row.finding_id
        ),
        "analysis_type": clean_required_text(
            row.analysis_type
        ),
        "business_area": clean_required_text(
            row.business_area
        ),
        "severity": clean_required_text(
            row.severity
        ),
        "entity_type": clean_required_text(
            row.entity_type
        ),
        "entity_id": clean_required_text(
            row.entity_id
        ),
        "entity_name": clean_required_text(
            row.entity_name
        ),
        "store_id": clean_required_text(
            row.store_id
        ),
        "store_name": clean_required_text(
            row.store_name
        ),
        "month": clean_required_text(
            row.month
        ),
        "total_revenue": clean_optional_float(
            row.total_revenue
        ),
        "operating_profit": clean_optional_float(
            row.operating_profit
        ),
        "operating_profit_margin_percent": (
            clean_optional_float(
                row.operating_profit_margin_percent
            )
        ),
        "target_achievement_percent": (
            clean_optional_float(
                row.target_achievement_percent
            )
        ),
        "risk_status": clean_optional_text(
            row.risk_status
        ),
        "summary": clean_required_text(
            row.summary
        ),
        "evidence": clean_required_text(
            row.evidence
        ),
        "status": clean_required_text(
            row.status
        ),
        "detected_at": clean_datetime(
            row.detected_at
        ),
    }


def get_vendor_analytics(
    *,
    severity: str | None,
    analysis_type: str | None,
    vendor_id: str | None,
    limit: int,
    offset: int,
) -> dict:
    """Return current vendor analytics findings."""

    findings_dataframe = run_vendor_analysis()

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
        column_name="vendor_id",
        filter_value=vendor_id,
    )

    filtered_findings = filtered_findings.reset_index(
        drop=True
    )

    matching_findings = len(filtered_findings)

    summary_records = build_finding_summary(
        filtered_findings
    )

    paginated_findings = filtered_findings.iloc[
        offset:offset + limit
    ]

    finding_records = [
        build_vendor_finding_record(row)
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


def get_finance_analytics(
    *,
    severity: str | None,
    analysis_type: str | None,
    store_id: str | None,
    month: str | None,
    risk_status: str | None,
    limit: int,
    offset: int,
) -> dict:
    """Return current store-finance analytics findings."""

    findings_dataframe = run_finance_analysis()

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
        column_name="month",
        filter_value=month,
    )

    filtered_findings = apply_exact_text_filter(
        filtered_findings,
        column_name="risk_status",
        filter_value=risk_status,
    )

    filtered_findings = filtered_findings.reset_index(
        drop=True
    )

    matching_findings = len(filtered_findings)

    summary_records = build_finding_summary(
        filtered_findings
    )

    paginated_findings = filtered_findings.iloc[
        offset:offset + limit
    ]

    finding_records = [
        build_finance_finding_record(row)
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
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from backend.analytics.thresholds import (
    LOW_OPERATING_PROFIT_MARGIN_PERCENT,
    LOW_TARGET_ACHIEVEMENT_PERCENT,
    VENDOR_AVERAGE_DELAY_DAYS_THRESHOLD,
    VENDOR_DELAYED_DELIVERIES_THRESHOLD,
    VENDOR_LOW_ON_TIME_DELIVERY_RATE,
    VENDOR_LOW_QUALITY_RATING_THRESHOLD,
    VENDOR_PARTIAL_DELIVERY_THRESHOLD,
)
from backend.database import get_database_engine, read_query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"


FINDING_COLUMNS = [
    "finding_id",
    "analysis_type",
    "business_area",
    "severity",
    "entity_type",
    "entity_id",
    "entity_name",
    "vendor_id",
    "vendor_name",
    "store_id",
    "store_name",
    "month",
    "delivery_count",
    "delayed_deliveries",
    "partial_deliveries",
    "average_delay_days",
    "maximum_delay_days",
    "average_quality_rating",
    "on_time_delivery_rate",
    "total_revenue",
    "operating_profit",
    "operating_profit_margin_percent",
    "target_achievement_percent",
    "risk_status",
    "summary",
    "evidence",
    "status",
    "detected_at",
]


def safe_float(value: object) -> float:
    """Convert a value safely to float."""

    if value is None or pd.isna(value):
        return 0.0

    return float(value)


def safe_int(value: object) -> int:
    """Convert a value safely to integer."""

    if value is None or pd.isna(value):
        return 0

    return int(value)


def optional_float(value: object) -> float | None:
    """Convert a value to float or return None when unavailable."""

    if value is None or pd.isna(value):
        return None

    return round(float(value), 2)


def optional_int(value: object) -> int | None:
    """Convert a value to integer or return None when unavailable."""

    if value is None or pd.isna(value):
        return None

    return int(value)


def clean_text(value: object) -> str:
    """Return clean text or an empty string for missing values."""

    if value is None or pd.isna(value):
        return ""

    return " ".join(str(value).split())


def format_currency(value: object) -> str:
    """Format a value as Indian currency."""

    if value is None or pd.isna(value):
        return "Not available"

    return f"₹{float(value):,.2f}"


def format_percent(value: object) -> str:
    """Format a value as a percentage."""

    if value is None or pd.isna(value):
        return "Not available"

    return f"{float(value):.2f}%"


def create_finding(
    *,
    finding_id: str,
    analysis_type: str,
    business_area: str,
    severity: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    summary: str,
    evidence: str,
    vendor_id: str | None = None,
    vendor_name: str | None = None,
    store_id: str | None = None,
    store_name: str | None = None,
    month: str | None = None,
    delivery_count: int | None = None,
    delayed_deliveries: int | None = None,
    partial_deliveries: int | None = None,
    average_delay_days: float | None = None,
    maximum_delay_days: float | None = None,
    average_quality_rating: float | None = None,
    on_time_delivery_rate: float | None = None,
    total_revenue: float | None = None,
    operating_profit: float | None = None,
    operating_profit_margin_percent: float | None = None,
    target_achievement_percent: float | None = None,
    risk_status: str | None = None,
) -> dict:
    """Create one standardized vendor or finance finding."""

    return {
        "finding_id": clean_text(finding_id),
        "analysis_type": clean_text(analysis_type),
        "business_area": clean_text(business_area),
        "severity": clean_text(severity),
        "entity_type": clean_text(entity_type),
        "entity_id": clean_text(entity_id),
        "entity_name": clean_text(entity_name),
        "vendor_id": clean_text(vendor_id),
        "vendor_name": clean_text(vendor_name),
        "store_id": clean_text(store_id),
        "store_name": clean_text(store_name),
        "month": clean_text(month),
        "delivery_count": optional_int(delivery_count),
        "delayed_deliveries": optional_int(delayed_deliveries),
        "partial_deliveries": optional_int(partial_deliveries),
        "average_delay_days": optional_float(average_delay_days),
        "maximum_delay_days": optional_float(maximum_delay_days),
        "average_quality_rating": optional_float(
            average_quality_rating
        ),
        "on_time_delivery_rate": optional_float(
            on_time_delivery_rate
        ),
        "total_revenue": optional_float(total_revenue),
        "operating_profit": optional_float(operating_profit),
        "operating_profit_margin_percent": optional_float(
            operating_profit_margin_percent
        ),
        "target_achievement_percent": optional_float(
            target_achievement_percent
        ),
        "risk_status": clean_text(risk_status),
        "summary": clean_text(summary),
        "evidence": clean_text(evidence),
        "status": "Open",
        "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_vendor_snapshot(engine: Engine) -> pd.DataFrame:
    """Return performance metrics for each vendor."""

    query = """
    SELECT
        vendor_id,
        vendor_name,
        COUNT(*) AS delivery_count,
        COUNT(*) FILTER (
            WHERE delay_days > 0
        ) AS delayed_deliveries,
        COUNT(*) FILTER (
            WHERE received_quantity < ordered_quantity
        ) AS partial_deliveries,
        AVG(delay_days) AS average_delay_days,
        MAX(delay_days) AS maximum_delay_days,
        AVG(quality_rating) AS average_quality_rating,
        COALESCE(
            (
                COUNT(*) FILTER (
                    WHERE delay_days <= 0
                )::NUMERIC
                / NULLIF(COUNT(*), 0)
            ) * 100,
            0
        ) AS on_time_delivery_rate
    FROM vendor_deliveries
    GROUP BY
        vendor_id,
        vendor_name
    ORDER BY vendor_id;
    """

    return read_query(engine, query)


def get_latest_finance_snapshot(engine: Engine) -> pd.DataFrame:
    """Return the latest finance metrics for every store."""

    query = """
    WITH latest_finance AS (
        SELECT DISTINCT ON (store_id)
            store_id,
            store_name,
            month,
            total_revenue,
            operating_profit,
            target_achievement_percent,
            risk_status
        FROM finance
        ORDER BY
            store_id,
            month DESC
    )
    SELECT
        store_id,
        store_name,
        month,
        total_revenue,
        operating_profit,
        target_achievement_percent,
        risk_status,
        CASE
            WHEN total_revenue > 0
            THEN (operating_profit / total_revenue) * 100
            ELSE 0
        END AS operating_profit_margin_percent
    FROM latest_finance
    ORDER BY store_id;
    """

    return read_query(engine, query)


def detect_repeated_vendor_delays(
    vendor_snapshot: pd.DataFrame,
) -> list[dict]:
    """Detect vendors with repeated delivery delays."""

    delay_data = vendor_snapshot[
        (vendor_snapshot["average_delay_days"]
         >= VENDOR_AVERAGE_DELAY_DAYS_THRESHOLD)
        | (
            vendor_snapshot["delayed_deliveries"]
            >= VENDOR_DELAYED_DELIVERIES_THRESHOLD
        )
    ].copy()

    findings = []

    for _, row in delay_data.iterrows():
        average_delay = safe_float(row["average_delay_days"])
        maximum_delay = safe_float(row["maximum_delay_days"])
        delayed_deliveries = safe_int(row["delayed_deliveries"])
        on_time_rate = safe_float(row["on_time_delivery_rate"])

        severity = "Medium"

        if (
            average_delay >= 10
            or maximum_delay >= 15
            or on_time_rate < 50
        ):
            severity = "High"

        findings.append(
            create_finding(
                finding_id=f"VENDOR-DELAY-{row['vendor_id']}",
                analysis_type="Repeated Vendor Delays",
                business_area="Procurement",
                severity=severity,
                entity_type="Vendor",
                entity_id=row["vendor_id"],
                entity_name=row["vendor_name"],
                vendor_id=row["vendor_id"],
                vendor_name=row["vendor_name"],
                delivery_count=safe_int(row["delivery_count"]),
                delayed_deliveries=delayed_deliveries,
                partial_deliveries=safe_int(row["partial_deliveries"]),
                average_delay_days=average_delay,
                maximum_delay_days=maximum_delay,
                average_quality_rating=safe_float(
                    row["average_quality_rating"]
                ),
                on_time_delivery_rate=on_time_rate,
                summary=(
                    f"{row['vendor_name']} has repeated delivery delays "
                    f"that may disrupt inventory replenishment."
                ),
                evidence=(
                    f"Delivery Count: {safe_int(row['delivery_count'])}; "
                    f"Delayed Deliveries: {delayed_deliveries}; "
                    f"Average Delay: {average_delay:.2f} days; "
                    f"Maximum Delay: {maximum_delay:.0f} days; "
                    f"On-Time Delivery Rate: {on_time_rate:.2f}%"
                ),
            )
        )

    return findings


def detect_partial_deliveries(
    vendor_snapshot: pd.DataFrame,
) -> list[dict]:
    """Detect vendors with repeated partial deliveries."""

    partial_data = vendor_snapshot[
        vendor_snapshot["partial_deliveries"]
        >= VENDOR_PARTIAL_DELIVERY_THRESHOLD
    ].copy()

    findings = []

    for _, row in partial_data.iterrows():
        partial_deliveries = safe_int(row["partial_deliveries"])

        severity = "High" if partial_deliveries >= 3 else "Medium"

        findings.append(
            create_finding(
                finding_id=f"PARTIAL-DELIVERY-{row['vendor_id']}",
                analysis_type="Partial Vendor Deliveries",
                business_area="Procurement",
                severity=severity,
                entity_type="Vendor",
                entity_id=row["vendor_id"],
                entity_name=row["vendor_name"],
                vendor_id=row["vendor_id"],
                vendor_name=row["vendor_name"],
                delivery_count=safe_int(row["delivery_count"]),
                delayed_deliveries=safe_int(row["delayed_deliveries"]),
                partial_deliveries=partial_deliveries,
                average_delay_days=safe_float(row["average_delay_days"]),
                maximum_delay_days=safe_float(row["maximum_delay_days"]),
                average_quality_rating=safe_float(
                    row["average_quality_rating"]
                ),
                on_time_delivery_rate=safe_float(
                    row["on_time_delivery_rate"]
                ),
                summary=(
                    f"{row['vendor_name']} has repeated partial deliveries, "
                    f"which may create inventory availability risk."
                ),
                evidence=(
                    f"Delivery Count: {safe_int(row['delivery_count'])}; "
                    f"Partial Deliveries: {partial_deliveries}; "
                    f"Delayed Deliveries: "
                    f"{safe_int(row['delayed_deliveries'])}; "
                    f"Average Delay: "
                    f"{safe_float(row['average_delay_days']):.2f} days"
                ),
            )
        )

    return findings


def detect_low_vendor_quality(
    vendor_snapshot: pd.DataFrame,
) -> list[dict]:
    """Detect vendors with below-threshold quality ratings."""

    quality_data = vendor_snapshot[
        vendor_snapshot["average_quality_rating"]
        < VENDOR_LOW_QUALITY_RATING_THRESHOLD
    ].copy()

    findings = []

    for _, row in quality_data.iterrows():
        quality_rating = safe_float(row["average_quality_rating"])

        severity = "High" if quality_rating < 3.0 else "Medium"

        findings.append(
            create_finding(
                finding_id=f"LOW-VENDOR-QUALITY-{row['vendor_id']}",
                analysis_type="Low Vendor Quality Rating",
                business_area="Procurement",
                severity=severity,
                entity_type="Vendor",
                entity_id=row["vendor_id"],
                entity_name=row["vendor_name"],
                vendor_id=row["vendor_id"],
                vendor_name=row["vendor_name"],
                delivery_count=safe_int(row["delivery_count"]),
                delayed_deliveries=safe_int(row["delayed_deliveries"]),
                partial_deliveries=safe_int(row["partial_deliveries"]),
                average_delay_days=safe_float(row["average_delay_days"]),
                maximum_delay_days=safe_float(row["maximum_delay_days"]),
                average_quality_rating=quality_rating,
                on_time_delivery_rate=safe_float(
                    row["on_time_delivery_rate"]
                ),
                summary=(
                    f"{row['vendor_name']} has a below-threshold average "
                    f"quality rating."
                ),
                evidence=(
                    f"Average Quality Rating: {quality_rating:.2f} out of 5; "
                    f"Delivery Count: {safe_int(row['delivery_count'])}; "
                    f"Partial Deliveries: "
                    f"{safe_int(row['partial_deliveries'])}; "
                    f"Average Delay: "
                    f"{safe_float(row['average_delay_days']):.2f} days"
                ),
            )
        )

    return findings


def detect_low_on_time_delivery_rate(
    vendor_snapshot: pd.DataFrame,
) -> list[dict]:
    """Detect vendors with low on-time delivery rates."""

    on_time_data = vendor_snapshot[
        vendor_snapshot["on_time_delivery_rate"]
        < VENDOR_LOW_ON_TIME_DELIVERY_RATE
    ].copy()

    findings = []

    for _, row in on_time_data.iterrows():
        on_time_rate = safe_float(row["on_time_delivery_rate"])

        severity = "High" if on_time_rate < 50 else "Medium"

        findings.append(
            create_finding(
                finding_id=f"LOW-ON-TIME-RATE-{row['vendor_id']}",
                analysis_type="Low On-Time Delivery Rate",
                business_area="Procurement",
                severity=severity,
                entity_type="Vendor",
                entity_id=row["vendor_id"],
                entity_name=row["vendor_name"],
                vendor_id=row["vendor_id"],
                vendor_name=row["vendor_name"],
                delivery_count=safe_int(row["delivery_count"]),
                delayed_deliveries=safe_int(row["delayed_deliveries"]),
                partial_deliveries=safe_int(row["partial_deliveries"]),
                average_delay_days=safe_float(row["average_delay_days"]),
                maximum_delay_days=safe_float(row["maximum_delay_days"]),
                average_quality_rating=safe_float(
                    row["average_quality_rating"]
                ),
                on_time_delivery_rate=on_time_rate,
                summary=(
                    f"{row['vendor_name']} has a low on-time delivery rate."
                ),
                evidence=(
                    f"On-Time Delivery Rate: {on_time_rate:.2f}%; "
                    f"Delayed Deliveries: "
                    f"{safe_int(row['delayed_deliveries'])}; "
                    f"Delivery Count: {safe_int(row['delivery_count'])}; "
                    f"Average Delay: "
                    f"{safe_float(row['average_delay_days']):.2f} days"
                ),
            )
        )

    return findings


def detect_low_operating_profit(
    finance_snapshot: pd.DataFrame,
) -> list[dict]:
    """Detect stores with low operating-profit margins."""

    profit_data = finance_snapshot[
        (finance_snapshot["operating_profit"] >= 0)
        & (
            finance_snapshot["operating_profit_margin_percent"]
            < LOW_OPERATING_PROFIT_MARGIN_PERCENT
        )
    ].copy()

    findings = []

    for _, row in profit_data.iterrows():
        profit_margin = safe_float(
            row["operating_profit_margin_percent"]
        )

        severity = "High" if profit_margin < 5 else "Medium"

        findings.append(
            create_finding(
                finding_id=f"LOW-PROFIT-{row['store_id']}-{row['month']}",
                analysis_type="Low Operating Profit",
                business_area="Finance",
                severity=severity,
                entity_type="Store",
                entity_id=row["store_id"],
                entity_name=row["store_name"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                month=row["month"],
                total_revenue=safe_float(row["total_revenue"]),
                operating_profit=safe_float(row["operating_profit"]),
                operating_profit_margin_percent=profit_margin,
                target_achievement_percent=safe_float(
                    row["target_achievement_percent"]
                ),
                risk_status=row["risk_status"],
                summary=(
                    f"{row['store_name']} has a low operating-profit margin "
                    f"in {row['month']}."
                ),
                evidence=(
                    f"Revenue: {format_currency(row['total_revenue'])}; "
                    f"Operating Profit: "
                    f"{format_currency(row['operating_profit'])}; "
                    f"Operating Profit Margin: {profit_margin:.2f}%; "
                    f"Target Achievement: "
                    f"{safe_float(row['target_achievement_percent']):.2f}%"
                ),
            )
        )

    return findings


def detect_loss_making_store_months(
    finance_snapshot: pd.DataFrame,
) -> list[dict]:
    """Detect latest store finance records with operating losses."""

    loss_data = finance_snapshot[
        finance_snapshot["operating_profit"] < 0
    ].copy()

    findings = []

    for _, row in loss_data.iterrows():
        findings.append(
            create_finding(
                finding_id=(
                    f"LOSS-MAKING-{row['store_id']}-{row['month']}"
                ),
                analysis_type="Loss-Making Store",
                business_area="Finance",
                severity="High",
                entity_type="Store",
                entity_id=row["store_id"],
                entity_name=row["store_name"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                month=row["month"],
                total_revenue=safe_float(row["total_revenue"]),
                operating_profit=safe_float(row["operating_profit"]),
                operating_profit_margin_percent=safe_float(
                    row["operating_profit_margin_percent"]
                ),
                target_achievement_percent=safe_float(
                    row["target_achievement_percent"]
                ),
                risk_status=row["risk_status"],
                summary=(
                    f"{row['store_name']} recorded an operating loss in "
                    f"{row['month']}."
                ),
                evidence=(
                    f"Revenue: {format_currency(row['total_revenue'])}; "
                    f"Operating Profit: "
                    f"{format_currency(row['operating_profit'])}; "
                    f"Operating Profit Margin: "
                    f"{safe_float(row['operating_profit_margin_percent']):.2f}%; "
                    f"Risk Status: {clean_text(row['risk_status'])}"
                ),
            )
        )

    return findings


def detect_low_target_achievement(
    finance_snapshot: pd.DataFrame,
) -> list[dict]:
    """Detect stores with low latest target achievement."""

    target_data = finance_snapshot[
        finance_snapshot["target_achievement_percent"]
        < LOW_TARGET_ACHIEVEMENT_PERCENT
    ].copy()

    findings = []

    for _, row in target_data.iterrows():
        target_achievement = safe_float(
            row["target_achievement_percent"]
        )

        severity = "High" if target_achievement < 50 else "Medium"

        findings.append(
            create_finding(
                finding_id=f"LOW-TARGET-{row['store_id']}-{row['month']}",
                analysis_type="Low Target Achievement",
                business_area="Finance",
                severity=severity,
                entity_type="Store",
                entity_id=row["store_id"],
                entity_name=row["store_name"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                month=row["month"],
                total_revenue=safe_float(row["total_revenue"]),
                operating_profit=safe_float(row["operating_profit"]),
                operating_profit_margin_percent=safe_float(
                    row["operating_profit_margin_percent"]
                ),
                target_achievement_percent=target_achievement,
                risk_status=row["risk_status"],
                summary=(
                    f"{row['store_name']} achieved only "
                    f"{target_achievement:.2f}% of its target in "
                    f"{row['month']}."
                ),
                evidence=(
                    f"Revenue: {format_currency(row['total_revenue'])}; "
                    f"Operating Profit: "
                    f"{format_currency(row['operating_profit'])}; "
                    f"Target Achievement: {target_achievement:.2f}%; "
                    f"Risk Status: {clean_text(row['risk_status'])}"
                ),
            )
        )

    return findings


def detect_high_financial_risk(
    finance_snapshot: pd.DataFrame,
) -> list[dict]:
    """Detect stores marked as high financial risk."""

    risk_data = finance_snapshot[
        finance_snapshot["risk_status"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("high risk")
    ].copy()

    findings = []

    for _, row in risk_data.iterrows():
        target_achievement = safe_float(
            row["target_achievement_percent"]
        )
        operating_profit = safe_float(row["operating_profit"])

        severity = "High"

        findings.append(
            create_finding(
                finding_id=(
                    f"HIGH-FINANCIAL-RISK-"
                    f"{row['store_id']}-{row['month']}"
                ),
                analysis_type="High Financial Risk",
                business_area="Finance",
                severity=severity,
                entity_type="Store",
                entity_id=row["store_id"],
                entity_name=row["store_name"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                month=row["month"],
                total_revenue=safe_float(row["total_revenue"]),
                operating_profit=operating_profit,
                operating_profit_margin_percent=safe_float(
                    row["operating_profit_margin_percent"]
                ),
                target_achievement_percent=target_achievement,
                risk_status=row["risk_status"],
                summary=(
                    f"{row['store_name']} is classified as High Risk in "
                    f"the finance report for {row['month']}."
                ),
                evidence=(
                    f"Revenue: {format_currency(row['total_revenue'])}; "
                    f"Operating Profit: {format_currency(operating_profit)}; "
                    f"Operating Profit Margin: "
                    f"{safe_float(row['operating_profit_margin_percent']):.2f}%; "
                    f"Target Achievement: {target_achievement:.2f}%; "
                    f"Risk Status: {clean_text(row['risk_status'])}"
                ),
            )
        )

    return findings


def run_vendor_finance_analysis(engine: Engine) -> pd.DataFrame:
    """Run all Day 13 vendor and finance analytics rules."""

    print("Reading vendor performance data...")
    vendor_snapshot = get_vendor_snapshot(engine)

    print("Reading latest finance data...")
    finance_snapshot = get_latest_finance_snapshot(engine)

    findings = []

    print("Analyzing repeated vendor delays...")
    findings.extend(detect_repeated_vendor_delays(vendor_snapshot))

    print("Analyzing partial vendor deliveries...")
    findings.extend(detect_partial_deliveries(vendor_snapshot))

    print("Analyzing low vendor quality...")
    findings.extend(detect_low_vendor_quality(vendor_snapshot))

    print("Analyzing on-time delivery rates...")
    findings.extend(detect_low_on_time_delivery_rate(vendor_snapshot))

    print("Analyzing low operating profit...")
    findings.extend(detect_low_operating_profit(finance_snapshot))

    print("Analyzing loss-making stores...")
    findings.extend(detect_loss_making_store_months(finance_snapshot))

    print("Analyzing low target achievement...")
    findings.extend(detect_low_target_achievement(finance_snapshot))

    print("Analyzing high financial-risk stores...")
    findings.extend(detect_high_financial_risk(finance_snapshot))

    findings_dataframe = pd.DataFrame(
        findings,
        columns=FINDING_COLUMNS,
    )

    if findings_dataframe.empty:
        return findings_dataframe

    severity_order = {
        "High": 1,
        "Medium": 2,
        "Low": 3,
    }

    findings_dataframe["severity_order"] = (
        findings_dataframe["severity"].map(severity_order)
    )

    findings_dataframe = findings_dataframe.sort_values(
        by=[
            "severity_order",
            "business_area",
            "analysis_type",
            "average_delay_days",
            "target_achievement_percent",
        ],
        ascending=[
            True,
            True,
            True,
            False,
            True,
        ],
        na_position="last",
    ).drop(columns=["severity_order"])

    return findings_dataframe.reset_index(drop=True)


def create_markdown_report(findings: pd.DataFrame) -> str:
    """Create a readable Markdown vendor and finance report."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Vendor and Finance Analysis Report",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        "This report contains procurement and finance findings calculated "
        "from validated PostgreSQL vendor-delivery and finance data.",
        "",
        "## Detection Rules",
        "",
        f"- Repeated vendor delay: average delay of "
        f"{VENDOR_AVERAGE_DELAY_DAYS_THRESHOLD:.0f} days or more, or "
        f"{VENDOR_DELAYED_DELIVERIES_THRESHOLD} or more delayed deliveries.",
        f"- Low vendor quality: below "
        f"{VENDOR_LOW_QUALITY_RATING_THRESHOLD:.1f} out of 5.",
        f"- Low on-time delivery rate: below "
        f"{VENDOR_LOW_ON_TIME_DELIVERY_RATE:.0f}%.",
        f"- Partial delivery risk: "
        f"{VENDOR_PARTIAL_DELIVERY_THRESHOLD} or more partial deliveries.",
        f"- Low operating profit margin: below "
        f"{LOW_OPERATING_PROFIT_MARGIN_PERCENT:.0f}%.",
        f"- Low target achievement: below "
        f"{LOW_TARGET_ACHIEVEMENT_PERCENT:.0f}%.",
        "",
    ]

    if findings.empty:
        lines.extend(
            [
                "No vendor or finance findings met the configured rules.",
                "",
            ]
        )
        return "\n".join(lines)

    summary = (
        findings.groupby(
            ["business_area", "analysis_type", "severity"]
        )
        .size()
        .reset_index(name="finding_count")
        .sort_values(
            by=["business_area", "analysis_type", "severity"]
        )
    )

    lines.extend(
        [
            "## Finding Summary",
            "",
            "| Area | Analysis Type | Severity | Findings |",
            "|---|---|---|---:|",
        ]
    )

    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.business_area} | {row.analysis_type} | "
            f"{row.severity} | {row.finding_count} |"
        )

    lines.extend(
        [
            "",
            "## Vendor and Finance Findings",
            "",
            "| Severity | Area | Analysis Type | Entity | Main Metric |",
            "|---|---|---|---|---|",
        ]
    )

    for row in findings.itertuples(index=False):
        metric_text = "Not available"

        if row.business_area == "Procurement":
            metric_text = (
                f"On-Time Rate: "
                f"{format_percent(row.on_time_delivery_rate)}"
            )

        elif row.business_area == "Finance":
            metric_text = (
                f"Target Achievement: "
                f"{format_percent(row.target_achievement_percent)}"
            )

        lines.append(
            f"| {row.severity} | {row.business_area} | "
            f"{row.analysis_type} | {row.entity_name} | "
            f"{metric_text} |"
        )

    lines.extend(
        [
            "",
            "## Detailed Findings",
            "",
        ]
    )

    for row in findings.itertuples(index=False):
        lines.extend(
            [
                f"### {row.finding_id}",
                "",
                f"**Severity:** {row.severity}",
                "",
                f"**Business Area:** {row.business_area}",
                "",
                f"**Analysis Type:** {row.analysis_type}",
                "",
                f"**Entity:** {row.entity_name} ({row.entity_type})",
                "",
                f"**Summary:** {row.summary}",
                "",
                f"**Evidence:** {row.evidence}",
                "",
            ]
        )

    return "\n".join(lines)


def print_primary_scenario_check(findings: pd.DataFrame) -> None:
    """Print the expected V004, V009, and S003 scenario results."""

    v004_delay = findings[
        (findings["analysis_type"] == "Repeated Vendor Delays")
        & (findings["vendor_id"] == "V004")
    ]

    v009_delay = findings[
        (findings["analysis_type"] == "Repeated Vendor Delays")
        & (findings["vendor_id"] == "V009")
    ]

    s003_financial_risk = findings[
        (findings["analysis_type"] == "High Financial Risk")
        & (findings["store_id"] == "S003")
    ]

    print("\nPrimary Scenario Check:")

    print(
        "- V004 vendor delay risk detected: "
        f"{'Yes' if not v004_delay.empty else 'No'}"
    )
    print(
        "- V009 vendor delay risk detected: "
        f"{'Yes' if not v009_delay.empty else 'No'}"
    )
    print(
        "- S003 high financial risk detected: "
        f"{'Yes' if not s003_financial_risk.empty else 'No'}"
    )


def main() -> None:
    """Run Day 13 vendor and finance analytics."""

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        findings_dataframe = run_vendor_finance_analysis(engine)

        csv_output_path = (
            REPORTS_DIRECTORY / "vendor_finance_analysis.csv"
        )
        markdown_output_path = (
            REPORTS_DIRECTORY / "vendor_finance_analysis_report.md"
        )

        findings_dataframe.to_csv(csv_output_path, index=False)

        markdown_report = create_markdown_report(findings_dataframe)

        markdown_output_path.write_text(
            markdown_report,
            encoding="utf-8",
        )

        print("\nVendor and finance analysis completed successfully.")
        print(f"Total findings created: {len(findings_dataframe)}")

        if not findings_dataframe.empty:
            print("\nFindings by analysis type and severity:")

            print(
                findings_dataframe.groupby(
                    ["analysis_type", "severity"]
                )
                .size()
                .reset_index(name="finding_count")
                .to_string(index=False)
            )

        print_primary_scenario_check(findings_dataframe)

        print(f"\nCSV report saved at: {csv_output_path}")
        print(f"Markdown report saved at: {markdown_output_path}")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
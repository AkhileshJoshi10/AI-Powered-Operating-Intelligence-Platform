from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from backend.analytics.thresholds import (
    COMPLAINT_GROWTH_PERCENT,
    COMPLAINT_OUTLIER_MULTIPLIER,
    REPEATED_COMPLAINT_CATEGORY_MULTIPLIER,
    UNRESOLVED_COMPLAINT_AGE_DAYS,
    URGENT_UNRESOLVED_COMPLAINT_AGE_DAYS,
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
    "store_id",
    "store_name",
    "product_id",
    "product_name",
    "region",
    "complaint_id",
    "complaint_type",
    "complaint_severity",
    "complaint_status",
    "complaint_date",
    "complaint_age_days",
    "total_complaints",
    "high_severity_complaints",
    "unresolved_complaints",
    "monthly_growth_percent",
    "benchmark_value",
    "benchmark_label",
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
    """Convert a value to float or return None if unavailable."""

    if value is None or pd.isna(value):
        return None

    return round(float(value), 2)


def optional_int(value: object) -> int | None:
    """Convert a value to integer or return None if unavailable."""

    if value is None or pd.isna(value):
        return None

    return int(value)


def clean_text(value: object) -> str:
    """Return clean text or an empty string for missing values."""

    if value is None or pd.isna(value):
        return ""

    return " ".join(str(value).split())


def format_percent(value: object) -> str:
    """Format a value as a percentage."""

    if value is None or pd.isna(value):
        return "Not available"

    return f"{float(value):.2f}%"


def safe_identifier(value: object) -> str:
    """Create a clean identifier component from text."""

    clean_value = clean_text(value).upper()
    clean_value = re.sub(r"[^A-Z0-9]+", "-", clean_value)

    return clean_value.strip("-")


def get_outlier_severity(
    complaint_ratio: float,
    high_severity_ratio: float,
) -> str:
    """Return severity for complaint-volume outliers."""

    if complaint_ratio >= 2.0 or high_severity_ratio >= 2.0:
        return "High"

    return "Medium"


def get_growth_severity(growth_percent: float) -> str:
    """Return severity for month-on-month complaint growth."""

    if growth_percent >= 40:
        return "High"

    return "Medium"


def get_ageing_severity(age_days: int) -> str:
    """Return severity for unresolved complaint ageing."""

    if age_days >= URGENT_UNRESOLVED_COMPLAINT_AGE_DAYS:
        return "High"

    return "Medium"


def create_finding(
    *,
    finding_id: str,
    analysis_type: str,
    severity: str,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    summary: str,
    evidence: str,
    store_id: str | None = None,
    store_name: str | None = None,
    product_id: str | None = None,
    product_name: str | None = None,
    region: str | None = None,
    complaint_id: str | None = None,
    complaint_type: str | None = None,
    complaint_severity: str | None = None,
    complaint_status: str | None = None,
    complaint_date: str | None = None,
    complaint_age_days: int | None = None,
    total_complaints: int | None = None,
    high_severity_complaints: int | None = None,
    unresolved_complaints: int | None = None,
    monthly_growth_percent: float | None = None,
    benchmark_value: float | None = None,
    benchmark_label: str | None = None,
) -> dict:
    """Create one standardized complaint-analysis finding."""

    return {
        "finding_id": clean_text(finding_id),
        "analysis_type": clean_text(analysis_type),
        "business_area": "Customer Support",
        "severity": clean_text(severity),
        "entity_type": clean_text(entity_type),
        "entity_id": clean_text(entity_id),
        "entity_name": clean_text(entity_name),
        "store_id": clean_text(store_id),
        "store_name": clean_text(store_name),
        "product_id": clean_text(product_id),
        "product_name": clean_text(product_name),
        "region": clean_text(region),
        "complaint_id": clean_text(complaint_id),
        "complaint_type": clean_text(complaint_type),
        "complaint_severity": clean_text(complaint_severity),
        "complaint_status": clean_text(complaint_status),
        "complaint_date": clean_text(complaint_date),
        "complaint_age_days": optional_int(complaint_age_days),
        "total_complaints": optional_int(total_complaints),
        "high_severity_complaints": optional_int(
            high_severity_complaints
        ),
        "unresolved_complaints": optional_int(unresolved_complaints),
        "monthly_growth_percent": optional_float(monthly_growth_percent),
        "benchmark_value": optional_float(benchmark_value),
        "benchmark_label": clean_text(benchmark_label),
        "summary": clean_text(summary),
        "evidence": clean_text(evidence),
        "status": "Open",
        "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def detect_high_complaint_products(engine: Engine) -> list[dict]:
    """Detect products with unusually high complaint volume."""

    query = """
    WITH product_summary AS (
        SELECT
            product_id,
            MAX(product_name) AS product_name,
            COUNT(*) AS total_complaints,
            COUNT(*) FILTER (
                WHERE severity = 'High'
            ) AS high_severity_complaints,
            COUNT(*) FILTER (
                WHERE status IN ('Open', 'In Progress')
            ) AS unresolved_complaints
        FROM complaints
        GROUP BY product_id
    ),
    benchmarks AS (
        SELECT
            AVG(total_complaints) AS average_complaints,
            AVG(high_severity_complaints) AS average_high_severity
        FROM product_summary
    )
    SELECT
        product_summary.product_id,
        product_summary.product_name,
        product_summary.total_complaints,
        product_summary.high_severity_complaints,
        product_summary.unresolved_complaints,
        benchmarks.average_complaints,
        benchmarks.average_high_severity
    FROM product_summary
    CROSS JOIN benchmarks
    WHERE
        product_summary.total_complaints
            >= benchmarks.average_complaints * :outlier_multiplier
        OR product_summary.high_severity_complaints
            >= benchmarks.average_high_severity * :outlier_multiplier
    ORDER BY
        product_summary.total_complaints DESC,
        product_summary.high_severity_complaints DESC;
    """

    product_data = read_query(
        engine,
        query,
        {
            "outlier_multiplier": COMPLAINT_OUTLIER_MULTIPLIER,
        },
    )

    findings = []

    for row in product_data.itertuples(index=False):
        total_complaints = safe_int(row.total_complaints)
        high_severity_complaints = safe_int(
            row.high_severity_complaints
        )
        unresolved_complaints = safe_int(row.unresolved_complaints)

        average_complaints = safe_float(row.average_complaints)
        average_high_severity = safe_float(row.average_high_severity)

        complaint_ratio = (
            total_complaints / average_complaints
            if average_complaints > 0
            else 0
        )

        high_severity_ratio = (
            high_severity_complaints / average_high_severity
            if average_high_severity > 0
            else 0
        )

        findings.append(
            create_finding(
                finding_id=f"HIGH-COMPLAINT-PRODUCT-{row.product_id}",
                analysis_type="High Complaint Product",
                severity=get_outlier_severity(
                    complaint_ratio,
                    high_severity_ratio,
                ),
                entity_type="Product",
                entity_id=row.product_id,
                entity_name=row.product_name,
                product_id=row.product_id,
                product_name=row.product_name,
                total_complaints=total_complaints,
                high_severity_complaints=high_severity_complaints,
                unresolved_complaints=unresolved_complaints,
                benchmark_value=average_complaints,
                benchmark_label="Average Complaints per Product",
                summary=(
                    f"{row.product_name} has an unusually high complaint "
                    f"volume compared with other products."
                ),
                evidence=(
                    f"Total Complaints: {total_complaints}; "
                    f"High-Severity Complaints: "
                    f"{high_severity_complaints}; "
                    f"Open or In-Progress Complaints: "
                    f"{unresolved_complaints}; "
                    f"Average Complaints per Product: "
                    f"{average_complaints:.2f}"
                ),
            )
        )

    return findings


def detect_high_complaint_stores(engine: Engine) -> list[dict]:
    """Detect stores with unusually high complaint volume."""

    query = """
    WITH store_summary AS (
        SELECT
            store_id,
            MAX(store_name) AS store_name,
            MAX(region) AS region,
            COUNT(*) AS total_complaints,
            COUNT(*) FILTER (
                WHERE severity = 'High'
            ) AS high_severity_complaints,
            COUNT(*) FILTER (
                WHERE status IN ('Open', 'In Progress')
            ) AS unresolved_complaints
        FROM complaints
        GROUP BY store_id
    ),
    benchmarks AS (
        SELECT
            AVG(total_complaints) AS average_complaints,
            AVG(high_severity_complaints) AS average_high_severity
        FROM store_summary
    )
    SELECT
        store_summary.store_id,
        store_summary.store_name,
        store_summary.region,
        store_summary.total_complaints,
        store_summary.high_severity_complaints,
        store_summary.unresolved_complaints,
        benchmarks.average_complaints,
        benchmarks.average_high_severity
    FROM store_summary
    CROSS JOIN benchmarks
    WHERE
        store_summary.total_complaints
            >= benchmarks.average_complaints * :outlier_multiplier
        OR store_summary.high_severity_complaints
            >= benchmarks.average_high_severity * :outlier_multiplier
    ORDER BY
        store_summary.total_complaints DESC,
        store_summary.high_severity_complaints DESC;
    """

    store_data = read_query(
        engine,
        query,
        {
            "outlier_multiplier": COMPLAINT_OUTLIER_MULTIPLIER,
        },
    )

    findings = []

    for row in store_data.itertuples(index=False):
        total_complaints = safe_int(row.total_complaints)
        high_severity_complaints = safe_int(
            row.high_severity_complaints
        )
        unresolved_complaints = safe_int(row.unresolved_complaints)

        average_complaints = safe_float(row.average_complaints)
        average_high_severity = safe_float(row.average_high_severity)

        complaint_ratio = (
            total_complaints / average_complaints
            if average_complaints > 0
            else 0
        )

        high_severity_ratio = (
            high_severity_complaints / average_high_severity
            if average_high_severity > 0
            else 0
        )

        findings.append(
            create_finding(
                finding_id=f"HIGH-COMPLAINT-STORE-{row.store_id}",
                analysis_type="High Complaint Store",
                severity=get_outlier_severity(
                    complaint_ratio,
                    high_severity_ratio,
                ),
                entity_type="Store",
                entity_id=row.store_id,
                entity_name=row.store_name,
                store_id=row.store_id,
                store_name=row.store_name,
                region=row.region,
                total_complaints=total_complaints,
                high_severity_complaints=high_severity_complaints,
                unresolved_complaints=unresolved_complaints,
                benchmark_value=average_complaints,
                benchmark_label="Average Complaints per Store",
                summary=(
                    f"{row.store_name} has an unusually high complaint "
                    f"burden compared with other stores."
                ),
                evidence=(
                    f"Total Complaints: {total_complaints}; "
                    f"High-Severity Complaints: "
                    f"{high_severity_complaints}; "
                    f"Open or In-Progress Complaints: "
                    f"{unresolved_complaints}; "
                    f"Average Complaints per Store: "
                    f"{average_complaints:.2f}; "
                    f"Region: {clean_text(row.region)}"
                ),
            )
        )

    return findings


def detect_repeated_complaint_categories(engine: Engine) -> list[dict]:
    """Detect complaint categories that recur more than expected."""

    query = """
    WITH category_summary AS (
        SELECT
            complaint_type,
            COUNT(*) AS total_complaints,
            COUNT(*) FILTER (
                WHERE severity = 'High'
            ) AS high_severity_complaints,
            COUNT(*) FILTER (
                WHERE status IN ('Open', 'In Progress')
            ) AS unresolved_complaints
        FROM complaints
        GROUP BY complaint_type
    ),
    benchmarks AS (
        SELECT
            AVG(total_complaints) AS average_complaints,
            AVG(high_severity_complaints) AS average_high_severity
        FROM category_summary
    )
    SELECT
        category_summary.complaint_type,
        category_summary.total_complaints,
        category_summary.high_severity_complaints,
        category_summary.unresolved_complaints,
        benchmarks.average_complaints,
        benchmarks.average_high_severity
    FROM category_summary
    CROSS JOIN benchmarks
    WHERE
        category_summary.total_complaints
            >= benchmarks.average_complaints * :category_multiplier
        OR category_summary.high_severity_complaints
            >= benchmarks.average_high_severity * :category_multiplier
    ORDER BY
        category_summary.total_complaints DESC,
        category_summary.high_severity_complaints DESC;
    """

    category_data = read_query(
        engine,
        query,
        {
            "category_multiplier": (
                REPEATED_COMPLAINT_CATEGORY_MULTIPLIER
            ),
        },
    )

    findings = []

    for row in category_data.itertuples(index=False):
        total_complaints = safe_int(row.total_complaints)
        high_severity_complaints = safe_int(
            row.high_severity_complaints
        )
        unresolved_complaints = safe_int(row.unresolved_complaints)

        average_complaints = safe_float(row.average_complaints)
        average_high_severity = safe_float(row.average_high_severity)

        complaint_ratio = (
            total_complaints / average_complaints
            if average_complaints > 0
            else 0
        )

        high_severity_ratio = (
            high_severity_complaints / average_high_severity
            if average_high_severity > 0
            else 0
        )

        category_id = safe_identifier(row.complaint_type)

        findings.append(
            create_finding(
                finding_id=(
                    f"REPEATED-COMPLAINT-CATEGORY-{category_id}"
                ),
                analysis_type="Repeated Complaint Category",
                severity=get_outlier_severity(
                    complaint_ratio,
                    high_severity_ratio,
                ),
                entity_type="Complaint Category",
                entity_id=category_id,
                entity_name=row.complaint_type,
                complaint_type=row.complaint_type,
                total_complaints=total_complaints,
                high_severity_complaints=high_severity_complaints,
                unresolved_complaints=unresolved_complaints,
                benchmark_value=average_complaints,
                benchmark_label="Average Complaints per Category",
                summary=(
                    f"{row.complaint_type} is a repeatedly occurring "
                    f"complaint category."
                ),
                evidence=(
                    f"Total Complaints: {total_complaints}; "
                    f"High-Severity Complaints: "
                    f"{high_severity_complaints}; "
                    f"Open or In-Progress Complaints: "
                    f"{unresolved_complaints}; "
                    f"Average Complaints per Category: "
                    f"{average_complaints:.2f}"
                ),
            )
        )

    return findings


def detect_open_high_severity_complaints(
    engine: Engine,
) -> list[dict]:
    """Detect all open or in-progress high-severity complaints."""

    query = """
    WITH latest_date AS (
        SELECT MAX(date) AS reference_date
        FROM complaints
    )
    SELECT
        c.complaint_id,
        c.date,
        c.store_id,
        c.store_name,
        c.product_id,
        c.product_name,
        c.region,
        c.complaint_type,
        c.severity,
        c.status,
        c.assigned_employee_id,
        c.resolution_time_days,
        latest_date.reference_date - c.date AS complaint_age_days
    FROM complaints AS c
    CROSS JOIN latest_date
    WHERE
        c.severity = 'High'
        AND c.status IN ('Open', 'In Progress')
    ORDER BY
        complaint_age_days DESC,
        c.date ASC;
    """

    complaint_data = read_query(engine, query)
    findings = []

    for row in complaint_data.itertuples(index=False):
        age_days = safe_int(row.complaint_age_days)

        findings.append(
            create_finding(
                finding_id=f"OPEN-HIGH-COMPLAINT-{row.complaint_id}",
                analysis_type="Open High-Severity Complaint",
                severity=get_ageing_severity(age_days),
                entity_type="Complaint",
                entity_id=row.complaint_id,
                entity_name=row.complaint_type,
                store_id=row.store_id,
                store_name=row.store_name,
                product_id=row.product_id,
                product_name=row.product_name,
                region=row.region,
                complaint_id=row.complaint_id,
                complaint_type=row.complaint_type,
                complaint_severity=row.severity,
                complaint_status=row.status,
                complaint_date=str(row.date),
                complaint_age_days=age_days,
                summary=(
                    f"A High-severity {row.complaint_type} complaint for "
                    f"{row.product_name} at {row.store_name} remains "
                    f"{row.status}."
                ),
                evidence=(
                    f"Complaint Date: {row.date}; "
                    f"Age Against Latest Dataset Date: {age_days} days; "
                    f"Status: {row.status}; "
                    f"Assigned Employee: "
                    f"{clean_text(row.assigned_employee_id)}; "
                    f"Recorded Resolution Time: "
                    f"{safe_int(row.resolution_time_days)} days"
                ),
            )
        )

    return findings


def detect_monthly_complaint_growth(engine: Engine) -> list[dict]:
    """Detect stores with substantial latest-month complaint growth."""

    query = """
    WITH monthly_store_complaints AS (
        SELECT
            store_id,
            MAX(store_name) AS store_name,
            MAX(region) AS region,
            TO_CHAR(date, 'YYYY-MM') AS month,
            COUNT(*) AS total_complaints,
            COUNT(*) FILTER (
                WHERE severity = 'High'
            ) AS high_severity_complaints,
            COUNT(*) FILTER (
                WHERE status IN ('Open', 'In Progress')
            ) AS unresolved_complaints
        FROM complaints
        GROUP BY
            store_id,
            TO_CHAR(date, 'YYYY-MM')
    ),
    complaint_comparison AS (
        SELECT
            store_id,
            store_name,
            region,
            month,
            total_complaints,
            high_severity_complaints,
            unresolved_complaints,
            LAG(month) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_month,
            LAG(total_complaints) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_month_complaints
        FROM monthly_store_complaints
    )
    SELECT
        store_id,
        store_name,
        region,
        month,
        total_complaints,
        high_severity_complaints,
        unresolved_complaints,
        previous_month,
        previous_month_complaints
    FROM complaint_comparison
    WHERE
        month = (
            SELECT MAX(month)
            FROM monthly_store_complaints
        )
        AND previous_month_complaints > 0
        AND total_complaints >= previous_month_complaints * (
            1 + :growth_ratio
        )
    ORDER BY
        (
            (total_complaints - previous_month_complaints)
            / NULLIF(previous_month_complaints, 0)
        ) DESC;
    """

    growth_data = read_query(
        engine,
        query,
        {
            "growth_ratio": COMPLAINT_GROWTH_PERCENT / 100,
        },
    )

    findings = []

    for row in growth_data.itertuples(index=False):
        current_complaints = safe_int(row.total_complaints)
        previous_complaints = safe_int(
            row.previous_month_complaints
        )

        growth_percent = (
            (
                (current_complaints - previous_complaints)
                / previous_complaints
            )
            * 100
            if previous_complaints > 0
            else 0
        )

        findings.append(
            create_finding(
                finding_id=(
                    f"COMPLAINT-GROWTH-{row.store_id}-{row.month}"
                ),
                analysis_type="Monthly Complaint Growth",
                severity=get_growth_severity(growth_percent),
                entity_type="Store",
                entity_id=row.store_id,
                entity_name=row.store_name,
                store_id=row.store_id,
                store_name=row.store_name,
                region=row.region,
                total_complaints=current_complaints,
                high_severity_complaints=safe_int(
                    row.high_severity_complaints
                ),
                unresolved_complaints=safe_int(
                    row.unresolved_complaints
                ),
                monthly_growth_percent=growth_percent,
                benchmark_value=previous_complaints,
                benchmark_label=(
                    f"Previous Month Complaints ({row.previous_month})"
                ),
                summary=(
                    f"{row.store_name} recorded a {growth_percent:.2f}% "
                    f"increase in complaints in {row.month} compared with "
                    f"{row.previous_month}."
                ),
                evidence=(
                    f"Current Month Complaints: {current_complaints}; "
                    f"Previous Month Complaints: {previous_complaints}; "
                    f"High-Severity Complaints: "
                    f"{safe_int(row.high_severity_complaints)}; "
                    f"Open or In-Progress Complaints: "
                    f"{safe_int(row.unresolved_complaints)}"
                ),
            )
        )

    return findings


def detect_unresolved_complaint_ageing(engine: Engine) -> list[dict]:
    """Detect unresolved complaints that have aged beyond the threshold."""

    query = """
    WITH latest_date AS (
        SELECT MAX(date) AS reference_date
        FROM complaints
    )
    SELECT
        c.complaint_id,
        c.date,
        c.store_id,
        c.store_name,
        c.product_id,
        c.product_name,
        c.region,
        c.complaint_type,
        c.severity,
        c.status,
        c.assigned_employee_id,
        c.resolution_time_days,
        latest_date.reference_date - c.date AS complaint_age_days
    FROM complaints AS c
    CROSS JOIN latest_date
    WHERE
        c.status IN ('Open', 'In Progress')
        AND latest_date.reference_date - c.date >= :age_threshold
    ORDER BY
        complaint_age_days DESC,
        c.severity DESC,
        c.date ASC;
    """

    ageing_data = read_query(
        engine,
        query,
        {
            "age_threshold": UNRESOLVED_COMPLAINT_AGE_DAYS,
        },
    )

    findings = []

    for row in ageing_data.itertuples(index=False):
        age_days = safe_int(row.complaint_age_days)

        findings.append(
            create_finding(
                finding_id=f"UNRESOLVED-AGEING-{row.complaint_id}",
                analysis_type="Unresolved Complaint Ageing",
                severity=get_ageing_severity(age_days),
                entity_type="Complaint",
                entity_id=row.complaint_id,
                entity_name=row.complaint_type,
                store_id=row.store_id,
                store_name=row.store_name,
                product_id=row.product_id,
                product_name=row.product_name,
                region=row.region,
                complaint_id=row.complaint_id,
                complaint_type=row.complaint_type,
                complaint_severity=row.severity,
                complaint_status=row.status,
                complaint_date=str(row.date),
                complaint_age_days=age_days,
                summary=(
                    f"A {row.severity}-severity complaint for "
                    f"{row.product_name} at {row.store_name} has remained "
                    f"{row.status} for {age_days} days relative to the "
                    f"latest dataset date."
                ),
                evidence=(
                    f"Complaint Date: {row.date}; "
                    f"Age Against Latest Dataset Date: {age_days} days; "
                    f"Complaint Severity: {row.severity}; "
                    f"Status: {row.status}; "
                    f"Assigned Employee: "
                    f"{clean_text(row.assigned_employee_id)}"
                ),
            )
        )

    return findings


def run_complaint_analysis(engine: Engine) -> pd.DataFrame:
    """Run all Day 12 complaint-analysis rules."""

    findings = []

    print("Analyzing high complaint products...")
    findings.extend(detect_high_complaint_products(engine))

    print("Analyzing high complaint stores...")
    findings.extend(detect_high_complaint_stores(engine))

    print("Analyzing repeated complaint categories...")
    findings.extend(detect_repeated_complaint_categories(engine))

    print("Analyzing open high-severity complaints...")
    findings.extend(detect_open_high_severity_complaints(engine))

    print("Analyzing monthly complaint growth...")
    findings.extend(detect_monthly_complaint_growth(engine))

    print("Analyzing unresolved complaint ageing...")
    findings.extend(detect_unresolved_complaint_ageing(engine))

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
            "analysis_type",
            "complaint_age_days",
            "total_complaints",
        ],
        ascending=[
            True,
            True,
            False,
            False,
        ],
        na_position="last",
    ).drop(columns=["severity_order"])

    return findings_dataframe.reset_index(drop=True)


def create_markdown_report(findings: pd.DataFrame) -> str:
    """Create a readable Markdown report from complaint findings."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Complaint Analysis Report",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        "This report contains complaint-related findings calculated from "
        "validated PostgreSQL complaint data.",
        "",
        "## Detection Rules",
        "",
        f"- Complaint outlier: at least "
        f"{COMPLAINT_OUTLIER_MULTIPLIER:.2f} times the relevant average.",
        f"- Repeated complaint category: at least "
        f"{REPEATED_COMPLAINT_CATEGORY_MULTIPLIER:.2f} times the category "
        "average.",
        f"- Monthly complaint growth: {COMPLAINT_GROWTH_PERCENT:.0f}% or more.",
        f"- Unresolved complaint ageing: {UNRESOLVED_COMPLAINT_AGE_DAYS} "
        "days or more against the latest complaint date in the dataset.",
        "",
    ]

    if findings.empty:
        lines.extend(
            [
                "No complaint findings met the configured rules.",
                "",
            ]
        )
        return "\n".join(lines)

    summary = (
        findings.groupby(["analysis_type", "severity"])
        .size()
        .reset_index(name="finding_count")
        .sort_values(by=["analysis_type", "severity"])
    )

    lines.extend(
        [
            "## Finding Summary",
            "",
            "| Analysis Type | Severity | Findings |",
            "|---|---|---:|",
        ]
    )

    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.analysis_type} | {row.severity} | "
            f"{row.finding_count} |"
        )

    lines.extend(
        [
            "",
            "## Complaint Findings",
            "",
            "| Severity | Analysis Type | Entity | Store | Complaint Metric |",
            "|---|---|---|---|---|",
        ]
    )

    for row in findings.itertuples(index=False):
        metric_text = "Not available"

        if pd.notna(row.monthly_growth_percent):
            metric_text = (
                f"Growth: {format_percent(row.monthly_growth_percent)}"
            )

        elif pd.notna(row.complaint_age_days):
            metric_text = f"Age: {int(row.complaint_age_days)} days"

        elif pd.notna(row.total_complaints):
            metric_text = f"Complaints: {int(row.total_complaints)}"

        lines.append(
            f"| {row.severity} | {row.analysis_type} | "
            f"{row.entity_name} | {row.store_name or '-'} | "
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
    """Print expected S003 and P017 complaint scenario results."""

    store_s003 = findings[
        (findings["analysis_type"] == "High Complaint Store")
        & (findings["store_id"] == "S003")
    ]

    product_p017 = findings[
        (findings["analysis_type"] == "High Complaint Product")
        & (findings["product_id"] == "P017")
    ]

    print("\nPrimary Scenario Check:")

    if store_s003.empty:
        print("- S003 high complaint store detected: No")
    else:
        total_complaints = safe_int(
            store_s003.iloc[0]["total_complaints"]
        )
        print(
            "- S003 high complaint store detected: Yes "
            f"({total_complaints} complaints)"
        )

    if product_p017.empty:
        print("- P017 high complaint product detected: No")
    else:
        total_complaints = safe_int(
            product_p017.iloc[0]["total_complaints"]
        )
        print(
            "- P017 high complaint product detected: Yes "
            f"({total_complaints} complaints)"
        )


def main() -> None:
    """Run Day 12 complaint analytics and save output files."""

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        findings_dataframe = run_complaint_analysis(engine)

        csv_output_path = REPORTS_DIRECTORY / "complaint_analysis.csv"
        markdown_output_path = (
            REPORTS_DIRECTORY / "complaint_analysis_report.md"
        )

        findings_dataframe.to_csv(csv_output_path, index=False)

        markdown_report = create_markdown_report(findings_dataframe)

        markdown_output_path.write_text(
            markdown_report,
            encoding="utf-8",
        )

        print("\nComplaint analysis completed successfully.")
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
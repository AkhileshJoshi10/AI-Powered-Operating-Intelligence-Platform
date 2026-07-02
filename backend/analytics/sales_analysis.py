from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from backend.analytics.thresholds import (
    CATEGORY_SALES_DECLINE_PERCENT,
    LOW_TARGET_ACHIEVEMENT_PERCENT,
    MINIMUM_PRODUCT_PREVIOUS_MONTH_SALES,
    PRODUCT_SALES_DECLINE_PERCENT,
    PRODUCT_TO_CATEGORY_AVERAGE_RATIO,
    REGIONAL_SALES_DECLINE_PERCENT,
    STORE_SALES_DECLINE_PERCENT,
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
    "category",
    "month",
    "previous_month",
    "current_sales",
    "previous_sales",
    "sales_change_percent",
    "benchmark_value",
    "benchmark_label",
    "target_achievement_percent",
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


def optional_float(value: object) -> float | None:
    """Convert a value to float or return None when unavailable."""

    if value is None or pd.isna(value):
        return None

    return round(float(value), 2)


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


def safe_identifier(value: object) -> str:
    """Create a clean identifier component from text."""

    clean_value = clean_text(value).upper()
    clean_value = re.sub(r"[^A-Z0-9]+", "-", clean_value)

    return clean_value.strip("-")


def get_decline_severity(decline_percent: float) -> str:
    """Return severity based on the size of sales decline."""

    if decline_percent >= 40:
        return "High"

    return "Medium"


def get_target_severity(target_achievement_percent: float) -> str:
    """Return severity based on target-achievement performance."""

    if target_achievement_percent < 50:
        return "High"

    return "Medium"


def get_product_underperformance_severity(
    performance_ratio: float,
) -> str:
    """Return severity for product performance against category average."""

    if performance_ratio < 0.40:
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
    category: str | None = None,
    month: str | None = None,
    previous_month: str | None = None,
    current_sales: float | None = None,
    previous_sales: float | None = None,
    sales_change_percent: float | None = None,
    benchmark_value: float | None = None,
    benchmark_label: str | None = None,
    target_achievement_percent: float | None = None,
) -> dict:
    """Create one standardized sales-analysis finding."""

    return {
        "finding_id": clean_text(finding_id),
        "analysis_type": clean_text(analysis_type),
        "business_area": "Sales",
        "severity": clean_text(severity),
        "entity_type": clean_text(entity_type),
        "entity_id": clean_text(entity_id),
        "entity_name": clean_text(entity_name),
        "store_id": clean_text(store_id),
        "store_name": clean_text(store_name),
        "product_id": clean_text(product_id),
        "product_name": clean_text(product_name),
        "region": clean_text(region),
        "category": clean_text(category),
        "month": clean_text(month),
        "previous_month": clean_text(previous_month),
        "current_sales": optional_float(current_sales),
        "previous_sales": optional_float(previous_sales),
        "sales_change_percent": optional_float(sales_change_percent),
        "benchmark_value": optional_float(benchmark_value),
        "benchmark_label": clean_text(benchmark_label),
        "target_achievement_percent": optional_float(
            target_achievement_percent
        ),
        "summary": clean_text(summary),
        "evidence": clean_text(evidence),
        "status": "Open",
        "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def detect_store_sales_decline(engine: Engine) -> list[dict]:
    """Detect major latest-month sales declines by store."""

    query = """
    WITH monthly_store_sales AS (
        SELECT
            store_id,
            MAX(store_name) AS store_name,
            MAX(region) AS region,
            TO_CHAR(date, 'YYYY-MM') AS month,
            SUM(total_sales) AS monthly_sales
        FROM sales
        GROUP BY
            store_id,
            TO_CHAR(date, 'YYYY-MM')
    ),
    sales_comparison AS (
        SELECT
            store_id,
            store_name,
            region,
            month,
            monthly_sales,
            LAG(month) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_month,
            LAG(monthly_sales) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_month_sales
        FROM monthly_store_sales
    )
    SELECT
        store_id,
        store_name,
        region,
        month,
        monthly_sales,
        previous_month,
        previous_month_sales
    FROM sales_comparison
    WHERE
        month = (
            SELECT MAX(month)
            FROM monthly_store_sales
        )
        AND previous_month_sales IS NOT NULL
        AND monthly_sales <= previous_month_sales * (
            1 - :decline_ratio
        )
    ORDER BY
        (
            (previous_month_sales - monthly_sales)
            / NULLIF(previous_month_sales, 0)
        ) DESC;
    """

    store_data = read_query(
        engine,
        query,
        {
            "decline_ratio": STORE_SALES_DECLINE_PERCENT / 100,
        },
    )

    findings = []

    for row in store_data.itertuples(index=False):
        current_sales = safe_float(row.monthly_sales)
        previous_sales = safe_float(row.previous_month_sales)

        decline_percent = (
            ((previous_sales - current_sales) / previous_sales) * 100
            if previous_sales > 0
            else 0
        )

        findings.append(
            create_finding(
                finding_id=(
                    f"STORE-DECLINE-{row.store_id}-{row.month}"
                ),
                analysis_type="Store Sales Decline",
                severity=get_decline_severity(decline_percent),
                entity_type="Store",
                entity_id=row.store_id,
                entity_name=row.store_name,
                store_id=row.store_id,
                store_name=row.store_name,
                region=row.region,
                month=row.month,
                previous_month=row.previous_month,
                current_sales=current_sales,
                previous_sales=previous_sales,
                sales_change_percent=-decline_percent,
                summary=(
                    f"{row.store_name} recorded a {decline_percent:.2f}% "
                    f"sales decline in {row.month} compared with "
                    f"{row.previous_month}."
                ),
                evidence=(
                    f"Current Month Sales: {format_currency(current_sales)}; "
                    f"Previous Month Sales: {format_currency(previous_sales)}; "
                    f"Sales Decline: {decline_percent:.2f}%; "
                    f"Region: {clean_text(row.region)}"
                ),
            )
        )

    return findings


def detect_product_sales_decline(engine: Engine) -> list[dict]:
    """Detect major latest-month sales declines by product."""

    query = """
    WITH monthly_product_sales AS (
        SELECT
            product_id,
            MAX(product_name) AS product_name,
            MAX(category) AS category,
            TO_CHAR(date, 'YYYY-MM') AS month,
            SUM(total_sales) AS monthly_sales
        FROM sales
        GROUP BY
            product_id,
            TO_CHAR(date, 'YYYY-MM')
    ),
    sales_comparison AS (
        SELECT
            product_id,
            product_name,
            category,
            month,
            monthly_sales,
            LAG(month) OVER (
                PARTITION BY product_id
                ORDER BY month
            ) AS previous_month,
            LAG(monthly_sales) OVER (
                PARTITION BY product_id
                ORDER BY month
            ) AS previous_month_sales
        FROM monthly_product_sales
    )
    SELECT
        product_id,
        product_name,
        category,
        month,
        monthly_sales,
        previous_month,
        previous_month_sales
    FROM sales_comparison
    WHERE
        month = (
            SELECT MAX(month)
            FROM monthly_product_sales
        )
        AND previous_month_sales >= :minimum_previous_sales
        AND monthly_sales <= previous_month_sales * (
            1 - :decline_ratio
        )
    ORDER BY
        (
            (previous_month_sales - monthly_sales)
            / NULLIF(previous_month_sales, 0)
        ) DESC;
    """

    product_data = read_query(
        engine,
        query,
        {
            "decline_ratio": PRODUCT_SALES_DECLINE_PERCENT / 100,
            "minimum_previous_sales": MINIMUM_PRODUCT_PREVIOUS_MONTH_SALES,
        },
    )

    findings = []

    for row in product_data.itertuples(index=False):
        current_sales = safe_float(row.monthly_sales)
        previous_sales = safe_float(row.previous_month_sales)

        decline_percent = (
            ((previous_sales - current_sales) / previous_sales) * 100
            if previous_sales > 0
            else 0
        )

        findings.append(
            create_finding(
                finding_id=(
                    f"PRODUCT-DECLINE-{row.product_id}-{row.month}"
                ),
                analysis_type="Product Sales Decline",
                severity=get_decline_severity(decline_percent),
                entity_type="Product",
                entity_id=row.product_id,
                entity_name=row.product_name,
                product_id=row.product_id,
                product_name=row.product_name,
                category=row.category,
                month=row.month,
                previous_month=row.previous_month,
                current_sales=current_sales,
                previous_sales=previous_sales,
                sales_change_percent=-decline_percent,
                summary=(
                    f"{row.product_name} recorded a {decline_percent:.2f}% "
                    f"sales decline in {row.month} compared with "
                    f"{row.previous_month}."
                ),
                evidence=(
                    f"Current Month Sales: {format_currency(current_sales)}; "
                    f"Previous Month Sales: {format_currency(previous_sales)}; "
                    f"Sales Decline: {decline_percent:.2f}%; "
                    f"Category: {clean_text(row.category)}"
                ),
            )
        )

    return findings


def detect_low_target_achievement(engine: Engine) -> list[dict]:
    """Detect stores with low latest-month sales-target achievement."""

    query = """
    WITH latest_finance AS (
        SELECT DISTINCT ON (store_id)
            store_id,
            store_name,
            month,
            monthly_sales_target,
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
        finance.store_id,
        finance.store_name,
        finance.month,
        finance.monthly_sales_target,
        finance.total_revenue,
        finance.operating_profit,
        finance.target_achievement_percent,
        finance.risk_status,
        stores.region
    FROM latest_finance AS finance
    LEFT JOIN stores
        ON finance.store_id = stores.store_id
    WHERE finance.target_achievement_percent < :target_threshold
    ORDER BY finance.target_achievement_percent ASC;
    """

    target_data = read_query(
        engine,
        query,
        {
            "target_threshold": LOW_TARGET_ACHIEVEMENT_PERCENT,
        },
    )

    findings = []

    for row in target_data.itertuples(index=False):
        target_achievement = safe_float(row.target_achievement_percent)
        target_value = safe_float(row.monthly_sales_target)
        current_revenue = safe_float(row.total_revenue)

        findings.append(
            create_finding(
                finding_id=(
                    f"LOW-TARGET-{row.store_id}-{row.month}"
                ),
                analysis_type="Low Target Achievement",
                severity=get_target_severity(target_achievement),
                entity_type="Store",
                entity_id=row.store_id,
                entity_name=row.store_name,
                store_id=row.store_id,
                store_name=row.store_name,
                region=row.region,
                month=row.month,
                current_sales=current_revenue,
                benchmark_value=target_value,
                benchmark_label="Monthly Sales Target",
                target_achievement_percent=target_achievement,
                summary=(
                    f"{row.store_name} achieved only "
                    f"{target_achievement:.2f}% of its sales target "
                    f"in {row.month}."
                ),
                evidence=(
                    f"Monthly Target: {format_currency(target_value)}; "
                    f"Revenue: {format_currency(current_revenue)}; "
                    f"Operating Profit: "
                    f"{format_currency(row.operating_profit)}; "
                    f"Risk Status: {clean_text(row.risk_status)}"
                ),
            )
        )

    return findings


def detect_underperforming_products(engine: Engine) -> list[dict]:
    """Detect products performing well below their category average."""

    query = """
    WITH latest_month AS (
        SELECT MAX(TO_CHAR(date, 'YYYY-MM')) AS month
        FROM sales
    ),
    latest_product_sales AS (
        SELECT
            product_id,
            MAX(product_name) AS product_name,
            category,
            SUM(total_sales) AS current_sales
        FROM sales
        WHERE TO_CHAR(date, 'YYYY-MM') = (
            SELECT month
            FROM latest_month
        )
        GROUP BY
            product_id,
            category
    ),
    category_benchmarks AS (
        SELECT
            category,
            AVG(current_sales) AS category_average_sales,
            COUNT(*) AS product_count
        FROM latest_product_sales
        GROUP BY category
    )
    SELECT
        product_sales.product_id,
        product_sales.product_name,
        product_sales.category,
        product_sales.current_sales,
        benchmarks.category_average_sales,
        benchmarks.product_count,
        (
            product_sales.current_sales
            / NULLIF(benchmarks.category_average_sales, 0)
        ) AS performance_ratio,
        (
            SELECT month
            FROM latest_month
        ) AS month
    FROM latest_product_sales AS product_sales
    JOIN category_benchmarks AS benchmarks
        ON product_sales.category = benchmarks.category
    WHERE
        benchmarks.product_count >= 2
        AND product_sales.current_sales <= (
            benchmarks.category_average_sales * :performance_ratio
        )
    ORDER BY
        performance_ratio ASC,
        product_sales.current_sales ASC;
    """

    underperforming_product_data = read_query(
        engine,
        query,
        {
            "performance_ratio": PRODUCT_TO_CATEGORY_AVERAGE_RATIO,
        },
    )

    findings = []

    for row in underperforming_product_data.itertuples(index=False):
        current_sales = safe_float(row.current_sales)
        category_average_sales = safe_float(
            row.category_average_sales
        )
        performance_ratio = safe_float(row.performance_ratio)

        findings.append(
            create_finding(
                finding_id=(
                    f"PRODUCT-UNDERPERFORMANCE-"
                    f"{row.product_id}-{row.month}"
                ),
                analysis_type="Product Underperformance",
                severity=get_product_underperformance_severity(
                    performance_ratio
                ),
                entity_type="Product",
                entity_id=row.product_id,
                entity_name=row.product_name,
                product_id=row.product_id,
                product_name=row.product_name,
                category=row.category,
                month=row.month,
                current_sales=current_sales,
                benchmark_value=category_average_sales,
                benchmark_label="Latest Category Average Sales",
                summary=(
                    f"{row.product_name} achieved only "
                    f"{performance_ratio * 100:.2f}% of the latest-month "
                    f"average sales for the {row.category} category."
                ),
                evidence=(
                    f"Product Sales: {format_currency(current_sales)}; "
                    f"Category Average Sales: "
                    f"{format_currency(category_average_sales)}; "
                    f"Product Count in Category: {int(row.product_count)}"
                ),
            )
        )

    return findings


def detect_category_sales_decline(engine: Engine) -> list[dict]:
    """Detect major latest-month sales declines by product category."""

    query = """
    WITH monthly_category_sales AS (
        SELECT
            category,
            TO_CHAR(date, 'YYYY-MM') AS month,
            SUM(total_sales) AS monthly_sales
        FROM sales
        GROUP BY
            category,
            TO_CHAR(date, 'YYYY-MM')
    ),
    sales_comparison AS (
        SELECT
            category,
            month,
            monthly_sales,
            LAG(month) OVER (
                PARTITION BY category
                ORDER BY month
            ) AS previous_month,
            LAG(monthly_sales) OVER (
                PARTITION BY category
                ORDER BY month
            ) AS previous_month_sales
        FROM monthly_category_sales
    )
    SELECT
        category,
        month,
        monthly_sales,
        previous_month,
        previous_month_sales
    FROM sales_comparison
    WHERE
        month = (
            SELECT MAX(month)
            FROM monthly_category_sales
        )
        AND previous_month_sales IS NOT NULL
        AND monthly_sales <= previous_month_sales * (
            1 - :decline_ratio
        )
    ORDER BY
        (
            (previous_month_sales - monthly_sales)
            / NULLIF(previous_month_sales, 0)
        ) DESC;
    """

    category_data = read_query(
        engine,
        query,
        {
            "decline_ratio": CATEGORY_SALES_DECLINE_PERCENT / 100,
        },
    )

    findings = []

    for row in category_data.itertuples(index=False):
        current_sales = safe_float(row.monthly_sales)
        previous_sales = safe_float(row.previous_month_sales)

        decline_percent = (
            ((previous_sales - current_sales) / previous_sales) * 100
            if previous_sales > 0
            else 0
        )

        category_id = safe_identifier(row.category)

        findings.append(
            create_finding(
                finding_id=(
                    f"CATEGORY-DECLINE-{category_id}-{row.month}"
                ),
                analysis_type="Category Sales Decline",
                severity=get_decline_severity(decline_percent),
                entity_type="Category",
                entity_id=category_id,
                entity_name=row.category,
                category=row.category,
                month=row.month,
                previous_month=row.previous_month,
                current_sales=current_sales,
                previous_sales=previous_sales,
                sales_change_percent=-decline_percent,
                summary=(
                    f"The {row.category} category recorded a "
                    f"{decline_percent:.2f}% sales decline in {row.month} "
                    f"compared with {row.previous_month}."
                ),
                evidence=(
                    f"Current Month Sales: {format_currency(current_sales)}; "
                    f"Previous Month Sales: {format_currency(previous_sales)}; "
                    f"Sales Decline: {decline_percent:.2f}%"
                ),
            )
        )

    return findings


def detect_regional_sales_decline(engine: Engine) -> list[dict]:
    """Detect major latest-month sales declines by region."""

    query = """
    WITH monthly_region_sales AS (
        SELECT
            region,
            TO_CHAR(date, 'YYYY-MM') AS month,
            SUM(total_sales) AS monthly_sales
        FROM sales
        WHERE region IS NOT NULL
            AND BTRIM(region) <> ''
        GROUP BY
            region,
            TO_CHAR(date, 'YYYY-MM')
    ),
    sales_comparison AS (
        SELECT
            region,
            month,
            monthly_sales,
            LAG(month) OVER (
                PARTITION BY region
                ORDER BY month
            ) AS previous_month,
            LAG(monthly_sales) OVER (
                PARTITION BY region
                ORDER BY month
            ) AS previous_month_sales
        FROM monthly_region_sales
    )
    SELECT
        region,
        month,
        monthly_sales,
        previous_month,
        previous_month_sales
    FROM sales_comparison
    WHERE
        month = (
            SELECT MAX(month)
            FROM monthly_region_sales
        )
        AND previous_month_sales IS NOT NULL
        AND monthly_sales <= previous_month_sales * (
            1 - :decline_ratio
        )
    ORDER BY
        (
            (previous_month_sales - monthly_sales)
            / NULLIF(previous_month_sales, 0)
        ) DESC;
    """

    region_data = read_query(
        engine,
        query,
        {
            "decline_ratio": REGIONAL_SALES_DECLINE_PERCENT / 100,
        },
    )

    findings = []

    for row in region_data.itertuples(index=False):
        current_sales = safe_float(row.monthly_sales)
        previous_sales = safe_float(row.previous_month_sales)

        decline_percent = (
            ((previous_sales - current_sales) / previous_sales) * 100
            if previous_sales > 0
            else 0
        )

        region_id = safe_identifier(row.region)

        findings.append(
            create_finding(
                finding_id=(
                    f"REGION-DECLINE-{region_id}-{row.month}"
                ),
                analysis_type="Regional Sales Decline",
                severity=get_decline_severity(decline_percent),
                entity_type="Region",
                entity_id=region_id,
                entity_name=row.region,
                region=row.region,
                month=row.month,
                previous_month=row.previous_month,
                current_sales=current_sales,
                previous_sales=previous_sales,
                sales_change_percent=-decline_percent,
                summary=(
                    f"The {row.region} region recorded a "
                    f"{decline_percent:.2f}% sales decline in {row.month} "
                    f"compared with {row.previous_month}."
                ),
                evidence=(
                    f"Current Month Sales: {format_currency(current_sales)}; "
                    f"Previous Month Sales: {format_currency(previous_sales)}; "
                    f"Sales Decline: {decline_percent:.2f}%"
                ),
            )
        )

    return findings


def run_sales_analysis(engine: Engine) -> pd.DataFrame:
    """Run all Day 10 sales-analysis rules."""

    findings = []

    print("Analyzing store sales decline...")
    findings.extend(detect_store_sales_decline(engine))

    print("Analyzing product sales decline...")
    findings.extend(detect_product_sales_decline(engine))

    print("Analyzing low target achievement...")
    findings.extend(detect_low_target_achievement(engine))

    print("Analyzing underperforming products...")
    findings.extend(detect_underperforming_products(engine))

    print("Analyzing category sales decline...")
    findings.extend(detect_category_sales_decline(engine))

    print("Analyzing regional sales decline...")
    findings.extend(detect_regional_sales_decline(engine))

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
            "sales_change_percent",
            "target_achievement_percent",
        ],
        ascending=[
            True,
            True,
            True,
            True,
        ],
        na_position="last",
    ).drop(columns=["severity_order"])

    return findings_dataframe.reset_index(drop=True)


def create_markdown_report(findings: pd.DataFrame) -> str:
    """Create a readable Markdown report from sales findings."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Sales Analysis Report",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        "This report contains deterministic sales findings calculated from "
        "validated PostgreSQL data. The findings will later provide evidence "
        "to the central issue-detection and priority engines.",
        "",
        "## Detection Rules",
        "",
        f"- Store sales decline: {STORE_SALES_DECLINE_PERCENT:.0f}% or more",
        f"- Product sales decline: {PRODUCT_SALES_DECLINE_PERCENT:.0f}% or more",
        f"- Low target achievement: below "
        f"{LOW_TARGET_ACHIEVEMENT_PERCENT:.0f}%",
        f"- Product underperformance: below "
        f"{PRODUCT_TO_CATEGORY_AVERAGE_RATIO * 100:.0f}% of category average",
        f"- Category sales decline: "
        f"{CATEGORY_SALES_DECLINE_PERCENT:.0f}% or more",
        f"- Regional sales decline: "
        f"{REGIONAL_SALES_DECLINE_PERCENT:.0f}% or more",
        "",
    ]

    if findings.empty:
        lines.extend(
            [
                "No sales findings met the configured thresholds.",
                "",
            ]
        )
        return "\n".join(lines)

    summary = (
        findings.groupby(
            ["analysis_type", "severity"]
        )
        .size()
        .reset_index(name="finding_count")
        .sort_values(
            by=["analysis_type", "severity"],
        )
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
            "## Sales Findings",
            "",
            "| Severity | Analysis Type | Entity | Period | Change / Performance |",
            "|---|---|---|---|---|",
        ]
    )

    for row in findings.itertuples(index=False):
        metric_text = ""

        if pd.notna(row.sales_change_percent):
            metric_text = format_percent(row.sales_change_percent)

        elif pd.notna(row.target_achievement_percent):
            metric_text = (
                f"Target Achievement: "
                f"{format_percent(row.target_achievement_percent)}"
            )

        elif pd.notna(row.benchmark_value):
            metric_text = (
                f"Sales: {format_currency(row.current_sales)}; "
                f"Benchmark: {format_currency(row.benchmark_value)}"
            )

        else:
            metric_text = "Not available"

        period = row.month

        if row.previous_month:
            period = f"{row.previous_month} → {row.month}"

        lines.append(
            f"| {row.severity} | {row.analysis_type} | "
            f"{row.entity_name} | {period} | {metric_text} |"
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
    """Print the expected S003 June sales-decline scenario result."""

    s003_june_decline = findings[
        (findings["analysis_type"] == "Store Sales Decline")
        & (findings["store_id"] == "S003")
        & (findings["month"] == "2026-06")
    ]

    print("\nPrimary Scenario Check:")

    if s003_june_decline.empty:
        print("- Store S003 June sales decline detected: No")

    else:
        decline = abs(
            safe_float(
                s003_june_decline.iloc[0]["sales_change_percent"]
            )
        )

        print(
            "- Store S003 June sales decline detected: Yes "
            f"({decline:.2f}% decline)"
        )


def main() -> None:
    """Run Day 10 sales analytics and save output files."""

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        findings_dataframe = run_sales_analysis(engine)

        csv_output_path = REPORTS_DIRECTORY / "sales_analysis.csv"
        markdown_output_path = (
            REPORTS_DIRECTORY / "sales_analysis_report.md"
        )

        findings_dataframe.to_csv(csv_output_path, index=False)

        markdown_report = create_markdown_report(findings_dataframe)

        markdown_output_path.write_text(
            markdown_report,
            encoding="utf-8",
        )

        print("\nSales analysis completed successfully.")
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
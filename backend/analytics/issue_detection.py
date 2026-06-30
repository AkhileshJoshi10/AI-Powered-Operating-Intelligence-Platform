from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"

load_dotenv(PROJECT_ROOT / ".env")


def get_database_url() -> str:
    """Build the PostgreSQL connection URL from .env values."""

    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    database_name = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB")
    username = os.getenv("DB_USER") or os.getenv("POSTGRES_USER")
    password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")

    missing_values = []

    if not database_name:
        missing_values.append("DB_NAME")
    if not username:
        missing_values.append("DB_USER")
    if not password:
        missing_values.append("DB_PASSWORD")

    if missing_values:
        raise ValueError(
            "Missing database settings in .env: "
            + ", ".join(missing_values)
        )

    encoded_password = quote_plus(password)

    return (
        f"postgresql+psycopg2://{username}:{encoded_password}"
        f"@{host}:{port}/{database_name}"
    )


def get_database_engine() -> Engine:
    """Create and return the SQLAlchemy database engine."""

    return create_engine(get_database_url())


def read_query(engine: Engine, query: str) -> pd.DataFrame:
    """Run a SQL query and return the result as a DataFrame."""

    with engine.connect() as connection:
        return pd.read_sql(text(query), connection)


def safe_float(value: object) -> float:
    """Convert values safely to float."""

    if pd.isna(value):
        return 0.0

    return float(value)


def get_priority(score: float) -> str:
    """Convert priority score into a priority level."""

    if score >= 85:
        return "High"

    if score >= 65:
        return "Medium"

    return "Low"


def create_issue(
    issue_id: str,
    issue_type: str,
    business_area: str,
    priority_score: float,
    entity_type: str,
    entity_id: str,
    title: str,
    description: str,
    evidence: str,
) -> dict:
    """Create one standardized issue record."""

    return {
        "issue_id": issue_id,
        "issue_type": issue_type,
        "business_area": business_area,
        "priority": get_priority(priority_score),
        "priority_score": round(priority_score, 2),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "issue_title": title,
        "issue_description": description,
        "evidence": evidence,
        "status": "New",
        "detection_source": "Rule-Based Analytics Engine",
        "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def detect_financial_risk(engine: Engine) -> list[dict]:
    """Detect stores with high financial risk in their latest reporting month."""

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
        ORDER BY store_id, month DESC
    )
    SELECT
        store_id,
        store_name,
        month,
        total_revenue,
        operating_profit,
        target_achievement_percent,
        risk_status
    FROM latest_finance
    WHERE
        risk_status = 'High Risk'
        OR target_achievement_percent < 70
        OR operating_profit < 0
    ORDER BY target_achievement_percent ASC;
    """

    finance_risk = read_query(engine, query)
    detected_issues = []

    for row in finance_risk.itertuples(index=False):
        target_achievement = safe_float(row.target_achievement_percent)
        operating_profit = safe_float(row.operating_profit)

        score = 82.0

        if target_achievement < 70:
            score += 8

        if operating_profit < 0:
            score += 10

        score = min(score, 100)

        description = (
            f"{row.store_name} has a high financial risk in {row.month}. "
            f"The store achieved only {target_achievement:.2f}% of its "
            f"monthly sales target."
        )

        evidence = (
            f"Revenue: {safe_float(row.total_revenue):,.2f}; "
            f"Operating Profit: {operating_profit:,.2f}; "
            f"Target Achievement: {target_achievement:.2f}%; "
            f"Risk Status: {row.risk_status}"
        )

        detected_issues.append(
            create_issue(
                issue_id=f"FIN-{row.store_id}-{row.month}",
                issue_type="Financial Risk",
                business_area="Finance",
                priority_score=score,
                entity_type="Store",
                entity_id=row.store_id,
                title=f"High financial risk at {row.store_name}",
                description=description,
                evidence=evidence,
            )
        )

    return detected_issues


def detect_sales_decline(engine: Engine) -> list[dict]:
    """Detect major month-on-month sales decline in the latest month."""

    query = """
    WITH monthly_store_sales AS (
        SELECT
            store_id,
            store_name,
            TO_CHAR(date, 'YYYY-MM') AS month,
            SUM(total_sales) AS monthly_sales
        FROM sales
        GROUP BY
            store_id,
            store_name,
            TO_CHAR(date, 'YYYY-MM')
    ),
    sales_comparison AS (
        SELECT
            store_id,
            store_name,
            month,
            monthly_sales,
            LAG(monthly_sales) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_month_sales
        FROM monthly_store_sales
    )
    SELECT
        store_id,
        store_name,
        month,
        monthly_sales,
        previous_month_sales
    FROM sales_comparison
    WHERE
        month = (
            SELECT MAX(month)
            FROM monthly_store_sales
        )
        AND previous_month_sales IS NOT NULL
        AND monthly_sales < previous_month_sales * 0.70
    ORDER BY monthly_sales ASC;
    """

    sales_decline = read_query(engine, query)
    detected_issues = []

    for row in sales_decline.itertuples(index=False):
        current_sales = safe_float(row.monthly_sales)
        previous_sales = safe_float(row.previous_month_sales)

        decline_percent = (
            ((previous_sales - current_sales) / previous_sales) * 100
            if previous_sales > 0
            else 0
        )

        score = min(70 + (decline_percent * 0.70), 95)

        description = (
            f"{row.store_name} recorded a {decline_percent:.2f}% sales decline "
            f"in {row.month} compared with the previous month."
        )

        evidence = (
            f"Current Month Sales: {current_sales:,.2f}; "
            f"Previous Month Sales: {previous_sales:,.2f}; "
            f"Sales Decline: {decline_percent:.2f}%"
        )

        detected_issues.append(
            create_issue(
                issue_id=f"SALES-{row.store_id}-{row.month}",
                issue_type="Sales Decline",
                business_area="Sales",
                priority_score=score,
                entity_type="Store",
                entity_id=row.store_id,
                title=f"Major sales decline at {row.store_name}",
                description=description,
                evidence=evidence,
            )
        )

    return detected_issues


def detect_critical_inventory_risk(engine: Engine) -> list[dict]:
    """Detect meaningful low-stock risks with customer-service impact."""

    query = """
    SELECT
        i.inventory_id,
        i.date,
        i.store_id,
        i.store_name,
        i.product_id,
        i.product_name,
        i.current_stock,
        i.reorder_level,
        i.stock_status,
        COUNT(c.complaint_id) AS related_complaints,
        COUNT(*) FILTER (
            WHERE c.severity = 'High'
        ) AS related_high_severity_complaints
    FROM inventory AS i
    LEFT JOIN complaints AS c
        ON i.store_id = c.store_id
        AND i.product_id = c.product_id
    WHERE i.stock_status = 'Low Stock'
    GROUP BY
        i.inventory_id,
        i.date,
        i.store_id,
        i.store_name,
        i.product_id,
        i.product_name,
        i.current_stock,
        i.reorder_level,
        i.stock_status
    ORDER BY
        related_high_severity_complaints DESC,
        related_complaints DESC,
        i.current_stock ASC;
    """

    inventory_risk = read_query(engine, query)
    detected_issues = []

    for row in inventory_risk.itertuples(index=False):
        current_stock = safe_float(row.current_stock)
        reorder_level = safe_float(row.reorder_level)
        related_complaints = int(row.related_complaints)
        high_severity_complaints = int(
            row.related_high_severity_complaints
        )

        stock_ratio = (
            current_stock / reorder_level
            if reorder_level > 0
            else 1
        )

        is_meaningful_risk = (
            stock_ratio <= 0.50
            or (
                related_complaints >= 20
                and high_severity_complaints >= 5
            )
        )

        if not is_meaningful_risk:
            continue

        score = (
            45
            + max(0, (0.80 - stock_ratio) * 20)
            + min(related_complaints * 0.20, 12)
            + min(high_severity_complaints * 0.75, 12)
        )

        if stock_ratio <= 0.25:
            score += 7

        score = min(score, 90)

        description = (
            f"{row.product_name} has a low-stock operational risk at "
            f"{row.store_name}. The issue may affect customer service "
            f"because the product is linked with customer complaints."
        )

        evidence = (
            f"Current Stock: {current_stock:.0f}; "
            f"Reorder Level: {reorder_level:.0f}; "
            f"Stock Ratio: {stock_ratio:.2%}; "
            f"Related Complaints: {related_complaints}; "
            f"High-Severity Complaints: {high_severity_complaints}"
        )

        detected_issues.append(
            create_issue(
                issue_id=(
                    f"INV-{row.store_id}-{row.product_id}-{row.date}"
                ),
                issue_type="Inventory  Stock Risk",
                business_area="Operations",
                priority_score=score,
                entity_type="Store Product",
                entity_id=f"{row.store_id}-{row.product_id}",
                title=(
                    f"Low-stock risk: {row.product_name} "
                    f"at {row.store_name}"
                ),
                description=description,
                evidence=evidence,
            )
        )

    return detected_issues


def detect_complaint_hotspots(engine: Engine) -> list[dict]:
    """Detect complaint outliers compared with the average store."""

    query = """
    WITH store_complaint_summary AS (
        SELECT
            store_id,
            store_name,
            COUNT(*) AS complaint_count,
            COUNT(*) FILTER (
                WHERE severity = 'High'
            ) AS high_severity_complaints,
            COUNT(*) FILTER (
                WHERE status IN ('Open', 'In Progress')
            ) AS unresolved_complaints
        FROM complaints
        GROUP BY
            store_id,
            store_name
    ),
    benchmarks AS (
        SELECT
            AVG(complaint_count) AS average_complaint_count,
            AVG(high_severity_complaints) AS average_high_severity_count,
            AVG(unresolved_complaints) AS average_unresolved_count
        FROM store_complaint_summary
    )
    SELECT
        summary.store_id,
        summary.store_name,
        summary.complaint_count,
        summary.high_severity_complaints,
        summary.unresolved_complaints,
        benchmarks.average_complaint_count,
        benchmarks.average_high_severity_count,
        benchmarks.average_unresolved_count
    FROM store_complaint_summary AS summary
    CROSS JOIN benchmarks
    WHERE
        summary.complaint_count
            >= benchmarks.average_complaint_count * 1.50
        OR summary.high_severity_complaints
            >= benchmarks.average_high_severity_count * 1.50
        OR summary.unresolved_complaints
            >= benchmarks.average_unresolved_count * 1.50
    ORDER BY
        summary.complaint_count DESC;
    """

    complaint_hotspots = read_query(engine, query)
    detected_issues = []

    for row in complaint_hotspots.itertuples(index=False):
        complaint_count = int(row.complaint_count)
        high_severity_complaints = int(row.high_severity_complaints)
        unresolved_complaints = int(row.unresolved_complaints)

        average_complaints = safe_float(row.average_complaint_count)
        average_high_severity = safe_float(
            row.average_high_severity_count
        )
        average_unresolved = safe_float(row.average_unresolved_count)

        complaint_ratio = (
            complaint_count / average_complaints
            if average_complaints > 0
            else 0
        )

        high_severity_ratio = (
            high_severity_complaints / average_high_severity
            if average_high_severity > 0
            else 0
        )

        unresolved_ratio = (
            unresolved_complaints / average_unresolved
            if average_unresolved > 0
            else 0
        )

        score = (
            65
            + min(max(complaint_ratio - 1, 0) * 20, 15)
            + min(max(high_severity_ratio - 1, 0) * 15, 10)
            + min(max(unresolved_ratio - 1, 0) * 10, 5)
        )

        score = min(score, 95)

        description = (
            f"{row.store_name} has a significantly higher complaint burden "
            f"than the average SmartMart store."
        )

        evidence = (
            f"Total Complaints: {complaint_count}; "
            f"High-Severity Complaints: {high_severity_complaints}; "
            f"Open or In-Progress Complaints: {unresolved_complaints}; "
            f"Average Store Complaints: {average_complaints:.2f}"
        )

        detected_issues.append(
            create_issue(
                issue_id=f"COMP-{row.store_id}",
                issue_type="Customer Complaint Hotspot",
                business_area="Customer Support",
                priority_score=score,
                entity_type="Store",
                entity_id=row.store_id,
                title=f"Customer complaint hotspot at {row.store_name}",
                description=description,
                evidence=evidence,
            )
        )

    return detected_issues


def detect_vendor_performance_risk(engine: Engine) -> list[dict]:
    """Detect vendors with delivery delays or poor quality performance."""

    query = """
    SELECT
        vendor_id,
        vendor_name,
        COUNT(*) AS delivery_count,
        AVG(delay_days) AS average_delay_days,
        MAX(delay_days) AS maximum_delay_days,
        AVG(quality_rating) AS average_quality_rating,
        COUNT(*) FILTER (
            WHERE delay_days > 0
        ) AS delayed_deliveries
    FROM vendor_deliveries
    GROUP BY
        vendor_id,
        vendor_name
    HAVING
        AVG(delay_days) >= 5
        OR COUNT(*) FILTER (
            WHERE delay_days > 0
        ) >= 3
        OR AVG(quality_rating) < 3.5
    ORDER BY
        AVG(delay_days) DESC,
        AVG(quality_rating) ASC;
    """

    vendor_risk = read_query(engine, query)
    detected_issues = []

    for row in vendor_risk.itertuples(index=False):
        average_delay = safe_float(row.average_delay_days)
        maximum_delay = safe_float(row.maximum_delay_days)
        quality_rating = safe_float(row.average_quality_rating)
        delayed_deliveries = int(row.delayed_deliveries)

        score = (
            55
            + min(average_delay * 4, 20)
            + min(maximum_delay * 1.5, 15)
            + min(delayed_deliveries * 2, 10)
        )

        if quality_rating < 3.5:
            score += 8

        score = min(score, 100)

        description = (
            f"{row.vendor_name} shows delivery-performance risk due to "
            f"recurring delays and/or below-expected quality ratings."
        )

        evidence = (
            f"Delivery Count: {int(row.delivery_count)}; "
            f"Average Delay: {average_delay:.2f} days; "
            f"Maximum Delay: {maximum_delay:.0f} days; "
            f"Delayed Deliveries: {delayed_deliveries}; "
            f"Average Quality Rating: {quality_rating:.2f}"
        )

        detected_issues.append(
            create_issue(
                issue_id=f"VENDOR-{row.vendor_id}",
                issue_type="Vendor Performance Risk",
                business_area="Procurement",
                priority_score=score,
                entity_type="Vendor",
                entity_id=row.vendor_id,
                title=f"Vendor delivery risk: {row.vendor_name}",
                description=description,
                evidence=evidence,
            )
        )

    return detected_issues


def create_markdown_report(issues: pd.DataFrame) -> str:
    """Create a readable Markdown report from detected issues."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Detected Business Issues Report",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        "This report contains business issues identified through deterministic "
        "SQL and Python analytics rules. These results will later be used by "
        "the AI agents for root-cause analysis and recommendations.",
        "",
        "## Priority Summary",
        "",
    ]

    if issues.empty:
        lines.extend(
            [
                "No business issues were detected by the current rules.",
                "",
            ]
        )
        return "\n".join(lines)

    priority_summary = (
        issues.groupby("priority")
        .size()
        .reset_index(name="issue_count")
    )

    priority_order = {"High": 1, "Medium": 2, "Low": 3}

    priority_summary["priority_order"] = priority_summary["priority"].map(
        priority_order
    )

    priority_summary = priority_summary.sort_values("priority_order")

    lines.extend(
        [
            "| Priority | Issue Count |",
            "|---|---:|",
        ]
    )

    for row in priority_summary.itertuples(index=False):
        lines.append(f"| {row.priority} | {row.issue_count} |")

    lines.extend(
        [
            "",
            "## Detected Issues",
            "",
            "| Priority | Score | Business Area | Issue | Entity |",
            "|---|---:|---|---|---|",
        ]
    )

    sorted_issues = issues.sort_values(
        by=["priority_score", "business_area"],
        ascending=[False, True],
    )

    for row in sorted_issues.itertuples(index=False):
        title = str(row.issue_title).replace("|", "/")
        lines.append(
            f"| {row.priority} | {row.priority_score:.2f} | "
            f"{row.business_area} | {title} | {row.entity_id} |"
        )

    lines.extend(
        [
            "",
            "## Detailed Evidence",
            "",
        ]
    )

    for row in sorted_issues.itertuples(index=False):
        lines.extend(
            [
                f"### {row.issue_id} — {row.issue_title}",
                "",
                f"**Priority:** {row.priority}",
                "",
                f"**Business Area:** {row.business_area}",
                "",
                f"**Description:** {row.issue_description}",
                "",
                f"**Evidence:** {row.evidence}",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    """Run all analytics rules and save detected issue outputs."""

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        detected_issues = []

        print("Detecting financial risks...")
        detected_issues.extend(detect_financial_risk(engine))

        print("Detecting sales decline...")
        detected_issues.extend(detect_sales_decline(engine))

        print("Detecting inventory risks...")
        detected_issues.extend(detect_critical_inventory_risk(engine))

        print("Detecting complaint hotspots...")
        detected_issues.extend(detect_complaint_hotspots(engine))

        print("Detecting vendor performance risks...")
        detected_issues.extend(detect_vendor_performance_risk(engine))

        issue_columns = [
            "issue_id",
            "issue_type",
            "business_area",
            "priority",
            "priority_score",
            "entity_type",
            "entity_id",
            "issue_title",
            "issue_description",
            "evidence",
            "status",
            "detection_source",
            "detected_at",
        ]

        issues_dataframe = pd.DataFrame(
            detected_issues,
            columns=issue_columns,
        )

        priority_order = {"High": 1, "Medium": 2, "Low": 3}

        if not issues_dataframe.empty:
            issues_dataframe["priority_order"] = (
                issues_dataframe["priority"].map(priority_order)
            )

            issues_dataframe = issues_dataframe.sort_values(
                by=["priority_order", "priority_score"],
                ascending=[True, False],
            )

            issues_dataframe = issues_dataframe.drop(
                columns=["priority_order"]
            )

        csv_output_path = REPORTS_DIRECTORY / "detected_issues.csv"
        markdown_output_path = REPORTS_DIRECTORY / "detected_issues_report.md"

        issues_dataframe.to_csv(csv_output_path, index=False)

        markdown_report = create_markdown_report(issues_dataframe)
        markdown_output_path.write_text(
            markdown_report,
            encoding="utf-8",
        )

        print("\nIssue detection completed successfully.")
        print(f"Total issues detected: {len(issues_dataframe)}")

        if not issues_dataframe.empty:
            print("\nIssues by priority:")
            print(
                issues_dataframe["priority"]
                .value_counts()
                .reindex(["High", "Medium", "Low"])
                .fillna(0)
                .astype(int)
            )

            print("\nTop detected issues:")
            print(
                issues_dataframe[
                    [
                        "priority",
                        "priority_score",
                        "business_area",
                        "issue_title",
                    ]
                ]
                .head(10)
                .to_string(index=False)
            )

        print(f"\nCSV report saved at: {csv_output_path}")
        print(f"Markdown report saved at: {markdown_output_path}")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
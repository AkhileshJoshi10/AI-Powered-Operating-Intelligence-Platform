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
ISSUES_CSV_PATH = REPORTS_DIRECTORY / "detected_issues.csv"

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


def read_query(
    engine: Engine,
    query: str,
    parameters: dict | None = None,
) -> pd.DataFrame:
    """Run a SQL query and return the result as a DataFrame."""

    with engine.connect() as connection:
        return pd.read_sql(
            text(query),
            connection,
            params=parameters,
        )


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


def format_currency(value: object) -> str:
    """Format a numeric value as a readable currency amount."""

    return f"₹{safe_float(value):,.2f}"


def clean_text(value: object) -> str:
    """Convert a value safely to clean text."""

    if pd.isna(value):
        return "Not available"

    return str(value).strip()


def create_analysis_record(
    issue: pd.Series,
    primary_root_cause: str,
    contributing_factors: str,
    evidence_summary: str,
    investigation_focus: str,
) -> dict:
    """Create one standardized root-cause analysis record."""

    return {
        "analysis_id": f"RCA-{issue['issue_id']}",
        "issue_id": issue["issue_id"],
        "issue_type": issue["issue_type"],
        "business_area": issue["business_area"],
        "priority": issue["priority"],
        "priority_score": safe_float(issue["priority_score"]),
        "entity_type": issue["entity_type"],
        "entity_id": issue["entity_id"],
        "issue_title": issue["issue_title"],
        "primary_root_cause": primary_root_cause,
        "contributing_factors": contributing_factors,
        "evidence_summary": evidence_summary,
        "investigation_focus": investigation_focus,
        "analysis_method": "Rule-Based Evidence Analysis",
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def analyze_financial_risk(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Analyze likely root causes behind a financial-risk issue."""

    store_id = clean_text(issue["entity_id"])
    month = "-".join(clean_text(issue["issue_id"]).split("-")[-2:])

    query = """
    WITH finance_history AS (
        SELECT
            store_id,
            store_name,
            month,
            total_revenue,
            total_cost,
            gross_profit,
            operating_expense,
            operating_profit,
            target_achievement_percent,
            risk_status,
            LAG(month) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_month,
            LAG(total_revenue) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_revenue,
            LAG(operating_profit) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_operating_profit
        FROM finance
        WHERE store_id = :store_id
    )
    SELECT *
    FROM finance_history
    WHERE month = :month;
    """

    finance_data = read_query(
        engine,
        query,
        {
            "store_id": store_id,
            "month": month,
        },
    )

    if finance_data.empty:
        return create_analysis_record(
            issue=issue,
            primary_root_cause=(
                "Financial-risk record could not be matched to the "
                "current finance table."
            ),
            contributing_factors="Further database review is required.",
            evidence_summary="No matching finance record was returned.",
            investigation_focus=(
                "Verify the store ID and finance month linked to this issue."
            ),
        )

    finance_row = finance_data.iloc[0]

    revenue = safe_float(finance_row["total_revenue"])
    operating_profit = safe_float(finance_row["operating_profit"])
    operating_expense = safe_float(finance_row["operating_expense"])
    target_achievement = safe_float(
        finance_row["target_achievement_percent"]
    )
    previous_revenue = safe_float(finance_row["previous_revenue"])
    previous_month = clean_text(finance_row["previous_month"])

    profit_margin = (
        (operating_profit / revenue) * 100
        if revenue > 0
        else 0
    )

    revenue_change_percent = (
        ((revenue - previous_revenue) / previous_revenue) * 100
        if previous_revenue > 0
        else 0
    )

    category_query = """
    SELECT
        category,
        SUM(
            CASE
                WHEN TO_CHAR(date, 'YYYY-MM') = :current_month
                THEN total_sales
                ELSE 0
            END
        ) AS current_sales,
        SUM(
            CASE
                WHEN TO_CHAR(date, 'YYYY-MM') = :previous_month
                THEN total_sales
                ELSE 0
            END
        ) AS previous_sales
    FROM sales
    WHERE
        store_id = :store_id
        AND TO_CHAR(date, 'YYYY-MM') IN (
            :current_month,
            :previous_month
        )
    GROUP BY category
    ORDER BY
        (
            SUM(
                CASE
                    WHEN TO_CHAR(date, 'YYYY-MM') = :current_month
                    THEN total_sales
                    ELSE 0
                END
            )
            -
            SUM(
                CASE
                    WHEN TO_CHAR(date, 'YYYY-MM') = :previous_month
                    THEN total_sales
                    ELSE 0
                END
            )
        ) ASC
    LIMIT 3;
    """

    category_changes = pd.DataFrame()

    if previous_month != "Not available":
        category_changes = read_query(
            engine,
            category_query,
            {
                "store_id": store_id,
                "current_month": month,
                "previous_month": previous_month,
            },
        )

    category_factor = "No prior-month category comparison was available."

    if not category_changes.empty:
        largest_decline = category_changes.iloc[0]
        current_category_sales = safe_float(largest_decline["current_sales"])
        previous_category_sales = safe_float(
            largest_decline["previous_sales"]
        )

        category_decline_percent = (
            (
                (previous_category_sales - current_category_sales)
                / previous_category_sales
            )
            * 100
            if previous_category_sales > 0
            else 0
        )

        if category_decline_percent > 0:
            category_factor = (
                f"{clean_text(largest_decline['category'])} sales declined by "
                f"{category_decline_percent:.2f}% compared with "
                f"{previous_month}."
            )

    primary_root_cause = (
        f"Severe underachievement of the sales target: the store achieved "
        f"only {target_achievement:.2f}% of its target in {month}."
    )

    contributing_factors = []

    if revenue_change_percent < 0:
        contributing_factors.append(
            f"Revenue declined by {abs(revenue_change_percent):.2f}% "
            f"from {previous_month}."
        )

    if profit_margin < 10:
        contributing_factors.append(
            f"Operating profit margin was only {profit_margin:.2f}%."
        )

    if operating_expense > 0:
        contributing_factors.append(
            f"Operating expenses were {format_currency(operating_expense)}."
        )

    contributing_factors.append(category_factor)

    evidence_summary = (
        f"Revenue: {format_currency(revenue)}; "
        f"Operating Profit: {format_currency(operating_profit)}; "
        f"Target Achievement: {target_achievement:.2f}%; "
        f"Financial Risk Status: {clean_text(finance_row['risk_status'])}."
    )

    investigation_focus = (
        "Review the largest declining product categories, store-level sales "
        "activities, discounting practices, and local operational constraints."
    )

    return create_analysis_record(
        issue=issue,
        primary_root_cause=primary_root_cause,
        contributing_factors=" ".join(contributing_factors),
        evidence_summary=evidence_summary,
        investigation_focus=investigation_focus,
    )


def analyze_sales_decline(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Analyze likely root causes behind a sales-decline issue."""

    store_id = clean_text(issue["entity_id"])
    month = "-".join(clean_text(issue["issue_id"]).split("-")[-2:])

    sales_query = """
    WITH monthly_store_sales AS (
        SELECT
            store_id,
            store_name,
            TO_CHAR(date, 'YYYY-MM') AS month,
            SUM(total_sales) AS monthly_sales,
            SUM(profit) AS monthly_profit
        FROM sales
        WHERE store_id = :store_id
        GROUP BY
            store_id,
            store_name,
            TO_CHAR(date, 'YYYY-MM')
    ),
    sales_history AS (
        SELECT
            store_id,
            store_name,
            month,
            monthly_sales,
            monthly_profit,
            LAG(month) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_month,
            LAG(monthly_sales) OVER (
                PARTITION BY store_id
                ORDER BY month
            ) AS previous_sales
        FROM monthly_store_sales
    )
    SELECT *
    FROM sales_history
    WHERE month = :month;
    """

    sales_data = read_query(
        engine,
        sales_query,
        {
            "store_id": store_id,
            "month": month,
        },
    )

    if sales_data.empty:
        return create_analysis_record(
            issue=issue,
            primary_root_cause=(
                "Sales-decline record could not be matched to the "
                "transaction data."
            ),
            contributing_factors="Further database review is required.",
            evidence_summary="No matching sales trend record was returned.",
            investigation_focus=(
                "Verify the store ID and month linked to this issue."
            ),
        )

    sales_row = sales_data.iloc[0]

    current_sales = safe_float(sales_row["monthly_sales"])
    previous_sales = safe_float(sales_row["previous_sales"])
    previous_month = clean_text(sales_row["previous_month"])

    decline_percent = (
        ((previous_sales - current_sales) / previous_sales) * 100
        if previous_sales > 0
        else 0
    )

    category_query = """
    SELECT
        category,
        SUM(
            CASE
                WHEN TO_CHAR(date, 'YYYY-MM') = :current_month
                THEN total_sales
                ELSE 0
            END
        ) AS current_sales,
        SUM(
            CASE
                WHEN TO_CHAR(date, 'YYYY-MM') = :previous_month
                THEN total_sales
                ELSE 0
            END
        ) AS previous_sales
    FROM sales
    WHERE
        store_id = :store_id
        AND TO_CHAR(date, 'YYYY-MM') IN (
            :current_month,
            :previous_month
        )
    GROUP BY category
    ORDER BY
        (
            SUM(
                CASE
                    WHEN TO_CHAR(date, 'YYYY-MM') = :current_month
                    THEN total_sales
                    ELSE 0
                END
            )
            -
            SUM(
                CASE
                    WHEN TO_CHAR(date, 'YYYY-MM') = :previous_month
                    THEN total_sales
                    ELSE 0
                END
            )
        ) ASC
    LIMIT 3;
    """

    inventory_query = """
    SELECT
        COUNT(*) FILTER (
            WHERE stock_status = 'Low Stock'
        ) AS low_stock_items,
        COUNT(*) FILTER (
            WHERE stock_status = 'Reorder Soon'
        ) AS reorder_soon_items,
        COUNT(*) FILTER (
            WHERE stock_status = 'Overstock'
        ) AS overstock_items
    FROM inventory
    WHERE store_id = :store_id;
    """

    complaint_query = """
    SELECT
        COUNT(*) AS complaint_count,
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaints
    FROM complaints
    WHERE
        store_id = :store_id
        AND TO_CHAR(date, 'YYYY-MM') = :month;
    """

    category_changes = read_query(
        engine,
        category_query,
        {
            "store_id": store_id,
            "current_month": month,
            "previous_month": previous_month,
        },
    )

    inventory_data = read_query(
        engine,
        inventory_query,
        {"store_id": store_id},
    )

    complaint_data = read_query(
        engine,
        complaint_query,
        {
            "store_id": store_id,
            "month": month,
        },
    )

    factors = []

    if not category_changes.empty:
        category_row = category_changes.iloc[0]
        current_category_sales = safe_float(category_row["current_sales"])
        previous_category_sales = safe_float(category_row["previous_sales"])

        category_decline_percent = (
            (
                (previous_category_sales - current_category_sales)
                / previous_category_sales
            )
            * 100
            if previous_category_sales > 0
            else 0
        )

        if category_decline_percent > 0:
            factors.append(
                f"{clean_text(category_row['category'])} was the largest "
                f"declining category, falling by "
                f"{category_decline_percent:.2f}%."
            )

    if not inventory_data.empty:
        inventory_row = inventory_data.iloc[0]
        low_stock_items = safe_int(inventory_row["low_stock_items"])
        reorder_soon_items = safe_int(inventory_row["reorder_soon_items"])

        if low_stock_items > 0 or reorder_soon_items > 0:
            factors.append(
                f"The store also has {low_stock_items} Low Stock and "
                f"{reorder_soon_items} Reorder Soon inventory records."
            )

    if not complaint_data.empty:
        complaint_row = complaint_data.iloc[0]
        complaint_count = safe_int(complaint_row["complaint_count"])
        high_severity_complaints = safe_int(
            complaint_row["high_severity_complaints"]
        )

        if complaint_count > 0:
            factors.append(
                f"{complaint_count} complaints were registered in {month}, "
                f"including {high_severity_complaints} High-severity cases."
            )

    primary_root_cause = (
        f"Store revenue declined by {decline_percent:.2f}% in {month} "
        f"compared with {previous_month}."
    )

    evidence_summary = (
        f"Current Month Sales: {format_currency(current_sales)}; "
        f"Previous Month Sales: {format_currency(previous_sales)}; "
        f"Sales Decline: {decline_percent:.2f}%."
    )

    investigation_focus = (
        "Review declining categories, stock availability of fast-moving "
        "products, customer complaints, and changes in local demand or "
        "sales execution."
    )

    return create_analysis_record(
        issue=issue,
        primary_root_cause=primary_root_cause,
        contributing_factors=(
            " ".join(factors)
            if factors
            else "No additional contributing factor was identified."
        ),
        evidence_summary=evidence_summary,
        investigation_focus=investigation_focus,
    )


def analyze_inventory_stock_risk(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Analyze likely root causes behind an inventory stock-risk issue."""

    entity_id = clean_text(issue["entity_id"])

    if "-" not in entity_id:
        return create_analysis_record(
            issue=issue,
            primary_root_cause=(
                "The issue entity does not contain a valid store-product ID."
            ),
            contributing_factors="Further database review is required.",
            evidence_summary=f"Invalid entity ID: {entity_id}",
            investigation_focus=(
                "Verify the entity ID format for the inventory issue."
            ),
        )

    store_id, product_id = entity_id.split("-", 1)

    inventory_query = """
    SELECT
        i.inventory_id,
        i.date,
        i.store_id,
        i.store_name,
        i.product_id,
        i.product_name,
        i.vendor_id,
        i.current_stock,
        i.reorder_level,
        i.stock_status,
        i.reorder_required,
        p.is_perishable,
        v.vendor_name,
        COUNT(c.complaint_id) AS related_complaints,
        COUNT(*) FILTER (
            WHERE c.severity = 'High'
        ) AS high_severity_complaints,
        COUNT(*) FILTER (
            WHERE c.status IN ('Open', 'In Progress')
        ) AS unresolved_complaints,
        COUNT(*) FILTER (
            WHERE c.complaint_type = 'Out of Stock'
        ) AS out_of_stock_complaints
    FROM inventory AS i
    JOIN products AS p
        ON i.product_id = p.product_id
    JOIN vendors AS v
        ON i.vendor_id = v.vendor_id
    LEFT JOIN complaints AS c
        ON i.store_id = c.store_id
        AND i.product_id = c.product_id
    WHERE
        i.store_id = :store_id
        AND i.product_id = :product_id
    GROUP BY
        i.inventory_id,
        i.date,
        i.store_id,
        i.store_name,
        i.product_id,
        i.product_name,
        i.vendor_id,
        i.current_stock,
        i.reorder_level,
        i.stock_status,
        i.reorder_required,
        p.is_perishable,
        v.vendor_name
    ORDER BY i.date DESC
    LIMIT 1;
    """

    inventory_data = read_query(
        engine,
        inventory_query,
        {
            "store_id": store_id,
            "product_id": product_id,
        },
    )

    if inventory_data.empty:
        return create_analysis_record(
            issue=issue,
            primary_root_cause=(
                "The inventory issue could not be matched to an inventory "
                "record."
            ),
            contributing_factors="Further database review is required.",
            evidence_summary="No matching inventory record was returned.",
            investigation_focus=(
                "Verify the store-product combination in the issue."
            ),
        )

    inventory_row = inventory_data.iloc[0]

    vendor_query = """
    SELECT
        COUNT(*) AS delivery_count,
        AVG(delay_days) AS average_delay_days,
        MAX(delay_days) AS maximum_delay_days,
        COUNT(*) FILTER (
            WHERE delay_days > 0
        ) AS delayed_deliveries,
        AVG(quality_rating) AS average_quality_rating
    FROM vendor_deliveries
    WHERE vendor_id = :vendor_id;
    """

    vendor_data = read_query(
        engine,
        vendor_query,
        {"vendor_id": inventory_row["vendor_id"]},
    )

    current_stock = safe_float(inventory_row["current_stock"])
    reorder_level = safe_float(inventory_row["reorder_level"])

    stock_ratio = (
        current_stock / reorder_level
        if reorder_level > 0
        else 0
    )

    related_complaints = safe_int(inventory_row["related_complaints"])
    high_severity_complaints = safe_int(
        inventory_row["high_severity_complaints"]
    )
    unresolved_complaints = safe_int(
        inventory_row["unresolved_complaints"]
    )
    out_of_stock_complaints = safe_int(
        inventory_row["out_of_stock_complaints"]
    )

    primary_root_cause = (
        f"Stock is at {stock_ratio:.2%} of its reorder level "
        f"({current_stock:.0f} units available against a reorder level "
        f"of {reorder_level:.0f})."
    )

    factors = []

    if related_complaints > 0:
        factors.append(
            f"The product is linked with {related_complaints} customer "
            f"complaints, including {high_severity_complaints} "
            f"High-severity cases."
        )

    if unresolved_complaints > 0:
        factors.append(
            f"{unresolved_complaints} related complaints remain Open or "
            f"In Progress."
        )

    if out_of_stock_complaints > 0:
        factors.append(
            f"{out_of_stock_complaints} related complaints are specifically "
            f"categorized as Out of Stock."
        )

    if not vendor_data.empty:
        vendor_row = vendor_data.iloc[0]
        average_delay = safe_float(vendor_row["average_delay_days"])
        maximum_delay = safe_float(vendor_row["maximum_delay_days"])
        delayed_deliveries = safe_int(vendor_row["delayed_deliveries"])

        if average_delay >= 3 or delayed_deliveries >= 2:
            factors.append(
                f"Supplier {clean_text(inventory_row['vendor_name'])} has "
                f"an average delivery delay of {average_delay:.2f} days "
                f"and {delayed_deliveries} delayed deliveries."
            )

        if maximum_delay >= 10:
            factors.append(
                f"The supplier's maximum observed delay is "
                f"{maximum_delay:.0f} days."
            )

    evidence_summary = (
        f"Store: {clean_text(inventory_row['store_name'])}; "
        f"Product: {clean_text(inventory_row['product_name'])}; "
        f"Stock Status: {clean_text(inventory_row['stock_status'])}; "
        f"Current Stock: {current_stock:.0f}; "
        f"Reorder Level: {reorder_level:.0f}; "
        f"Related Complaints: {related_complaints}."
    )

    investigation_focus = (
        "Review the latest purchase order, vendor delivery status, recent "
        "sales velocity, stock-transfer availability, and replenishment "
        "approval process."
    )

    return create_analysis_record(
        issue=issue,
        primary_root_cause=primary_root_cause,
        contributing_factors=(
            " ".join(factors)
            if factors
            else "No additional contributing factor was identified."
        ),
        evidence_summary=evidence_summary,
        investigation_focus=investigation_focus,
    )


def analyze_complaint_hotspot(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Analyze likely root causes behind a complaint-hotspot issue."""

    store_id = clean_text(issue["entity_id"])

    summary_query = """
    SELECT
        COUNT(*) AS total_complaints,
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaints,
        COUNT(*) FILTER (
            WHERE status IN ('Open', 'In Progress')
        ) AS unresolved_complaints
    FROM complaints
    WHERE store_id = :store_id;
    """

    complaint_type_query = """
    SELECT
        complaint_type,
        COUNT(*) AS complaint_count,
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaints,
        COUNT(*) FILTER (
            WHERE status IN ('Open', 'In Progress')
        ) AS unresolved_complaints
    FROM complaints
    WHERE store_id = :store_id
    GROUP BY complaint_type
    ORDER BY
        complaint_count DESC,
        high_severity_complaints DESC
    LIMIT 3;
    """

    product_query = """
    SELECT
        product_id,
        product_name,
        COUNT(*) AS complaint_count,
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaints
    FROM complaints
    WHERE store_id = :store_id
    GROUP BY
        product_id,
        product_name
    ORDER BY
        complaint_count DESC,
        high_severity_complaints DESC
    LIMIT 3;
    """

    inventory_query = """
    SELECT
        COUNT(*) FILTER (
            WHERE stock_status = 'Low Stock'
        ) AS low_stock_items,
        COUNT(*) FILTER (
            WHERE stock_status = 'Reorder Soon'
        ) AS reorder_soon_items
    FROM inventory
    WHERE store_id = :store_id;
    """

    summary_data = read_query(
        engine,
        summary_query,
        {"store_id": store_id},
    )

    complaint_type_data = read_query(
        engine,
        complaint_type_query,
        {"store_id": store_id},
    )

    product_data = read_query(
        engine,
        product_query,
        {"store_id": store_id},
    )

    inventory_data = read_query(
        engine,
        inventory_query,
        {"store_id": store_id},
    )

    if summary_data.empty:
        return create_analysis_record(
            issue=issue,
            primary_root_cause=(
                "The complaint-hotspot issue could not be matched to "
                "complaint records."
            ),
            contributing_factors="Further database review is required.",
            evidence_summary="No complaint summary was returned.",
            investigation_focus="Verify the store ID linked to the issue.",
        )

    summary_row = summary_data.iloc[0]

    total_complaints = safe_int(summary_row["total_complaints"])
    high_severity_complaints = safe_int(
        summary_row["high_severity_complaints"]
    )
    unresolved_complaints = safe_int(
        summary_row["unresolved_complaints"]
    )

    primary_root_cause = (
        "A concentrated volume of customer complaints has accumulated "
        "at the store."
    )

    factors = []

    if not complaint_type_data.empty:
        top_type = complaint_type_data.iloc[0]

        factors.append(
            f"The largest complaint category is "
            f"{clean_text(top_type['complaint_type'])} with "
            f"{safe_int(top_type['complaint_count'])} cases."
        )

    if not product_data.empty:
        top_product = product_data.iloc[0]

        factors.append(
            f"The most frequently complained-about product is "
            f"{clean_text(top_product['product_name'])} with "
            f"{safe_int(top_product['complaint_count'])} cases."
        )

    if unresolved_complaints > 0:
        factors.append(
            f"{unresolved_complaints} complaints are still Open or "
            f"In Progress."
        )

    if not inventory_data.empty:
        inventory_row = inventory_data.iloc[0]
        low_stock_items = safe_int(inventory_row["low_stock_items"])
        reorder_soon_items = safe_int(
            inventory_row["reorder_soon_items"]
        )

        if low_stock_items > 0 or reorder_soon_items > 0:
            factors.append(
                f"The store has {low_stock_items} Low Stock and "
                f"{reorder_soon_items} Reorder Soon inventory records, "
                f"which may be contributing to service-related complaints."
            )

    evidence_summary = (
        f"Total Complaints: {total_complaints}; "
        f"High-Severity Complaints: {high_severity_complaints}; "
        f"Open or In-Progress Complaints: {unresolved_complaints}."
    )

    investigation_focus = (
        "Review the main complaint categories, product availability, "
        "frontline service quality, complaint-resolution workload, and "
        "store-manager escalation process."
    )

    return create_analysis_record(
        issue=issue,
        primary_root_cause=primary_root_cause,
        contributing_factors=" ".join(factors),
        evidence_summary=evidence_summary,
        investigation_focus=investigation_focus,
    )


def analyze_vendor_performance_risk(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Analyze likely root causes behind a vendor-performance issue."""

    vendor_id = clean_text(issue["entity_id"])

    vendor_query = """
    SELECT
        vendor_id,
        vendor_name,
        COUNT(*) AS delivery_count,
        AVG(delay_days) AS average_delay_days,
        MAX(delay_days) AS maximum_delay_days,
        COUNT(*) FILTER (
            WHERE delay_days > 0
        ) AS delayed_deliveries,
        COUNT(*) FILTER (
            WHERE received_quantity < ordered_quantity
        ) AS partial_deliveries,
        AVG(quality_rating) AS average_quality_rating
    FROM vendor_deliveries
    WHERE vendor_id = :vendor_id
    GROUP BY
        vendor_id,
        vendor_name;
    """

    affected_store_query = """
    SELECT
        store_name,
        COUNT(*) AS delivery_count,
        AVG(delay_days) AS average_delay_days,
        MAX(delay_days) AS maximum_delay_days
    FROM vendor_deliveries
    WHERE vendor_id = :vendor_id
    GROUP BY store_name
    ORDER BY
        average_delay_days DESC,
        maximum_delay_days DESC
    LIMIT 3;
    """

    vendor_data = read_query(
        engine,
        vendor_query,
        {"vendor_id": vendor_id},
    )

    affected_store_data = read_query(
        engine,
        affected_store_query,
        {"vendor_id": vendor_id},
    )

    if vendor_data.empty:
        return create_analysis_record(
            issue=issue,
            primary_root_cause=(
                "The vendor-risk issue could not be matched to delivery "
                "records."
            ),
            contributing_factors="Further database review is required.",
            evidence_summary="No vendor delivery summary was returned.",
            investigation_focus="Verify the vendor ID linked to the issue.",
        )

    vendor_row = vendor_data.iloc[0]

    average_delay = safe_float(vendor_row["average_delay_days"])
    maximum_delay = safe_float(vendor_row["maximum_delay_days"])
    delayed_deliveries = safe_int(vendor_row["delayed_deliveries"])
    partial_deliveries = safe_int(vendor_row["partial_deliveries"])
    quality_rating = safe_float(vendor_row["average_quality_rating"])

    if average_delay >= 5:
        primary_root_cause = (
            f"Recurring delivery delays are the main risk: average delay is "
            f"{average_delay:.2f} days."
        )
    elif quality_rating < 3.5:
        primary_root_cause = (
            f"Below-expected product quality is the main risk: average "
            f"quality rating is {quality_rating:.2f} out of 5."
        )
    else:
        primary_root_cause = (
            "Repeated delivery-performance exceptions are affecting "
            "supplier reliability."
        )

    factors = []

    if maximum_delay > 0:
        factors.append(
            f"The maximum observed delivery delay is "
            f"{maximum_delay:.0f} days."
        )

    if delayed_deliveries > 0:
        factors.append(
            f"{delayed_deliveries} deliveries were delayed."
        )

    if partial_deliveries > 0:
        factors.append(
            f"{partial_deliveries} deliveries were partial."
        )

    if quality_rating < 4:
        factors.append(
            f"Average quality rating is {quality_rating:.2f} out of 5."
        )

    if not affected_store_data.empty:
        most_affected_store = affected_store_data.iloc[0]

        factors.append(
            f"The most affected store is "
            f"{clean_text(most_affected_store['store_name'])}, where the "
            f"average delay is "
            f"{safe_float(most_affected_store['average_delay_days']):.2f} "
            f"days."
        )

    evidence_summary = (
        f"Vendor: {clean_text(vendor_row['vendor_name'])}; "
        f"Delivery Count: {safe_int(vendor_row['delivery_count'])}; "
        f"Average Delay: {average_delay:.2f} days; "
        f"Maximum Delay: {maximum_delay:.0f} days; "
        f"Average Quality Rating: {quality_rating:.2f}."
    )

    investigation_focus = (
        "Review vendor service-level agreement compliance, purchase-order "
        "planning, supply capacity, product quality checks, and backup "
        "supplier availability."
    )

    return create_analysis_record(
        issue=issue,
        primary_root_cause=primary_root_cause,
        contributing_factors=" ".join(factors),
        evidence_summary=evidence_summary,
        investigation_focus=investigation_focus,
    )


def analyze_unknown_issue(
    issue: pd.Series,
) -> dict:
    """Create a fallback analysis for unrecognized issue types."""

    return create_analysis_record(
        issue=issue,
        primary_root_cause=(
            "No specialized root-cause rule has been created for this "
            "issue type yet."
        ),
        contributing_factors=(
            "Use the issue evidence and linked business records for review."
        ),
        evidence_summary=clean_text(issue["evidence"]),
        investigation_focus=(
            "Create a dedicated root-cause rule for this issue type."
        ),
    )


def create_markdown_report(analyses: pd.DataFrame) -> str:
    """Create a readable Markdown root-cause analysis report."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Root Cause Analysis Report",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        "This report provides evidence-based probable root causes for "
        "High and Medium priority issues. The findings are generated from "
        "PostgreSQL business data using deterministic analytics rules.",
        "",
        "## Analysis Scope",
        "",
        "- Only High and Medium priority issues are analyzed.",
        "- Findings indicate evidence-supported probable causes, not "
        "unverified assumptions.",
        "- AI agents will later use these structured findings to prepare "
        "recommendations and executive briefs.",
        "",
    ]

    if analyses.empty:
        lines.extend(
            [
                "No High or Medium priority issues were available for "
                "root-cause analysis.",
                "",
            ]
        )
        return "\n".join(lines)

    priority_summary = (
        analyses.groupby("priority")
        .size()
        .reset_index(name="analysis_count")
    )

    priority_order = {"High": 1, "Medium": 2, "Low": 3}

    priority_summary["priority_order"] = priority_summary["priority"].map(
        priority_order
    )

    priority_summary = priority_summary.sort_values("priority_order")

    lines.extend(
        [
            "## Analysis Summary",
            "",
            "| Priority | Analyses |",
            "|---|---:|",
        ]
    )

    for row in priority_summary.itertuples(index=False):
        lines.append(f"| {row.priority} | {row.analysis_count} |")

    lines.extend(
        [
            "",
            "## Root Cause Summary",
            "",
            "| Priority | Business Area | Issue | Primary Root Cause |",
            "|---|---|---|---|",
        ]
    )

    sorted_analyses = analyses.sort_values(
        by=["priority_score", "business_area"],
        ascending=[False, True],
    )

    for row in sorted_analyses.itertuples(index=False):
        issue_title = clean_text(row.issue_title).replace("|", "/")
        root_cause = clean_text(row.primary_root_cause).replace("|", "/")

        lines.append(
            f"| {row.priority} | {row.business_area} | "
            f"{issue_title} | {root_cause} |"
        )

    lines.extend(
        [
            "",
            "## Detailed Root Cause Analyses",
            "",
        ]
    )

    for row in sorted_analyses.itertuples(index=False):
        lines.extend(
            [
                f"### {row.analysis_id} — {row.issue_title}",
                "",
                f"**Priority:** {row.priority} "
                f"({row.priority_score:.2f})",
                "",
                f"**Business Area:** {row.business_area}",
                "",
                f"**Primary Root Cause:** {row.primary_root_cause}",
                "",
                f"**Contributing Factors:** {row.contributing_factors}",
                "",
                f"**Evidence Summary:** {row.evidence_summary}",
                "",
                f"**Investigation Focus:** {row.investigation_focus}",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> None:
    """Run root-cause analysis for High and Medium priority issues."""

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if not ISSUES_CSV_PATH.exists():
        raise FileNotFoundError(
            "Issue file not found. Run "
            "'python backend/analytics/issue_detection.py' first."
        )

    issues_dataframe = pd.read_csv(ISSUES_CSV_PATH)

    required_columns = {
        "issue_id",
        "issue_type",
        "business_area",
        "priority",
        "priority_score",
        "entity_type",
        "entity_id",
        "issue_title",
        "evidence",
    }

    missing_columns = required_columns - set(issues_dataframe.columns)

    if missing_columns:
        raise ValueError(
            "The detected issues file is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    issues_to_analyze = issues_dataframe[
        issues_dataframe["priority"].isin(["High", "Medium"])
    ].copy()

    priority_order = {"High": 1, "Medium": 2, "Low": 3}

    issues_to_analyze["priority_order"] = (
        issues_to_analyze["priority"].map(priority_order)
    )

    issues_to_analyze = issues_to_analyze.sort_values(
        by=["priority_order", "priority_score"],
        ascending=[True, False],
    ).drop(columns=["priority_order"])

    print("Connecting to PostgreSQL database...")
    print(
        f"High and Medium priority issues selected: "
        f"{len(issues_to_analyze)}"
    )

    engine = get_database_engine()
    analysis_records = []

    try:
        for issue_index, issue in issues_to_analyze.iterrows():
            issue_type = clean_text(issue["issue_type"])

            print(
                f"Analyzing {issue['issue_id']} "
                f"({issue_type})..."
            )

            try:
                if issue_type == "Financial Risk":
                    analysis = analyze_financial_risk(engine, issue)

                elif issue_type == "Sales Decline":
                    analysis = analyze_sales_decline(engine, issue)

                elif issue_type in {
                    "Inventory Stock Risk",
                    "Critical Inventory Risk",
                }:
                    analysis = analyze_inventory_stock_risk(engine, issue)

                elif issue_type == "Customer Complaint Hotspot":
                    analysis = analyze_complaint_hotspot(engine, issue)

                elif issue_type == "Vendor Performance Risk":
                    analysis = analyze_vendor_performance_risk(engine, issue)

                else:
                    analysis = analyze_unknown_issue(issue)

                analysis_records.append(analysis)

            except Exception as error:
                analysis_records.append(
                    create_analysis_record(
                        issue=issue,
                        primary_root_cause=(
                            "Analysis could not be completed automatically."
                        ),
                        contributing_factors=(
                            "A technical review is required before "
                            "concluding the root cause."
                        ),
                        evidence_summary=(
                            f"Root-cause analysis error: {error}"
                        ),
                        investigation_focus=(
                            "Review the data and rule logic for this issue."
                        ),
                    )
                )

    finally:
        engine.dispose()

    analysis_columns = [
        "analysis_id",
        "issue_id",
        "issue_type",
        "business_area",
        "priority",
        "priority_score",
        "entity_type",
        "entity_id",
        "issue_title",
        "primary_root_cause",
        "contributing_factors",
        "evidence_summary",
        "investigation_focus",
        "analysis_method",
        "analyzed_at",
    ]

    analyses_dataframe = pd.DataFrame(
        analysis_records,
        columns=analysis_columns,
    )

    csv_output_path = REPORTS_DIRECTORY / "root_cause_analysis.csv"
    markdown_output_path = REPORTS_DIRECTORY / "root_cause_analysis_report.md"

    analyses_dataframe.to_csv(csv_output_path, index=False)

    markdown_report = create_markdown_report(analyses_dataframe)

    markdown_output_path.write_text(
        markdown_report,
        encoding="utf-8",
    )

    print("\nRoot-cause analysis completed successfully.")
    print(f"Total analyses created: {len(analyses_dataframe)}")

    if not analyses_dataframe.empty:
        print("\nAnalyses by priority:")
        print(
            analyses_dataframe["priority"]
            .value_counts()
            .reindex(["High", "Medium", "Low"])
            .fillna(0)
            .astype(int)
        )

        print("\nTop root-cause analyses:")
        print(
            analyses_dataframe[
                [
                    "priority",
                    "business_area",
                    "issue_title",
                    "primary_root_cause",
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

    print(f"\nCSV report saved at: {csv_output_path}")
    print(f"Markdown report saved at: {markdown_output_path}")


if __name__ == "__main__":
    main()
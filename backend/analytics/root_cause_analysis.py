from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.database import get_database_engine, read_query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"

EXECUTIVE_PRIORITY_FILE = (
    REPORTS_DIRECTORY / "executive_priority_list.csv"
)

EVIDENCE_COLUMNS = [
    "issue_id",
    "source_finding_id",
    "source_report",
    "source_module",
    "analysis_type",
    "business_area",
    "severity",
    "entity_type",
    "entity_id",
    "store_id",
    "product_id",
    "vendor_id",
    "summary",
    "evidence",
    "detected_at",
]

OUTPUT_COLUMNS = [
    "analysis_id",
    "executive_rank",
    "issue_id",
    "title",
    "issue_type",
    "business_area",
    "priority_level",
    "priority_score",
    "executive_score",
    "entity_type",
    "entity_id",
    "store_id",
    "product_id",
    "vendor_id",
    "period_label",
    "root_cause_category",
    "root_cause_summary",
    "root_cause_explanation",
    "contributing_factors",
    "evidence_summary",
    "investigation_focus",
    "confidence_score",
    "evidence_count",
    "evidence_types",
    "analysis_method",
    "analysis_status",
    "review_status",
    "generated_at",
]

SEVERITY_ORDER = {
    "High": 1,
    "Medium": 2,
    "Low": 3,
}


def clean_text(value: object) -> str:
    """Return clean text and safely handle missing values."""

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass

    text_value = " ".join(str(value).split())

    if text_value.lower() == "nan":
        return ""

    return text_value


def safe_float(value: object) -> float:
    """Convert a scalar value safely to float."""

    if value is None:
        return 0.0

    try:
        if pd.isna(value):
            return 0.0
    except TypeError:
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: object) -> int:
    """Convert a scalar value safely to integer."""

    return int(safe_float(value))


def optional_float(value: object) -> float | None:
    """Convert a scalar value to float or return None."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except TypeError:
        return None

    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def format_currency(value: object) -> str:
    """Format a value as a readable Indian currency amount."""

    return f"₹{safe_float(value):,.2f}"


def unique_non_empty(values: pd.Series) -> list[str]:
    """Return unique non-empty values while preserving original order."""

    result: list[str] = []

    for value in values:
        cleaned_value = clean_text(value)

        if cleaned_value and cleaned_value not in result:
            result.append(cleaned_value)

    return result


def extract_number(pattern: str, text_value: object) -> float | None:
    """Extract the first number matching a regular-expression pattern."""

    match = re.search(
        pattern,
        clean_text(text_value),
        flags=re.IGNORECASE,
    )

    if match is None:
        return None

    try:
        return float(match.group(1).replace(",", ""))
    except (TypeError, ValueError):
        return None


def get_period_label(issue: pd.Series) -> str | None:
    """Return a YYYY-MM period from the issue period label when available."""

    period_text = clean_text(issue.get("period_label"))
    match = re.search(r"\d{4}-\d{2}", period_text)

    return match.group(0) if match else None


def get_store_id(issue: pd.Series) -> str:
    """Return the store ID from explicit fields or a store entity."""

    store_id = clean_text(issue.get("store_id"))

    if store_id:
        return store_id

    if clean_text(issue.get("entity_type")) == "Store":
        return clean_text(issue.get("entity_id"))

    entity_id = clean_text(issue.get("entity_id"))
    match = re.search(r"\bS\d{3}\b", entity_id)

    return match.group(0) if match else ""


def get_product_id(issue: pd.Series) -> str:
    """Return the product ID from explicit fields or a composite entity."""

    product_id = clean_text(issue.get("product_id"))

    if product_id:
        return product_id

    if clean_text(issue.get("entity_type")) == "Product":
        return clean_text(issue.get("entity_id"))

    entity_id = clean_text(issue.get("entity_id"))
    match = re.search(r"\bP\d{3}\b", entity_id)

    return match.group(0) if match else ""


def get_vendor_id(issue: pd.Series) -> str:
    """Return the vendor ID from explicit fields or a vendor entity."""

    vendor_id = clean_text(issue.get("vendor_id"))

    if vendor_id:
        return vendor_id

    if clean_text(issue.get("entity_type")) == "Vendor":
        return clean_text(issue.get("entity_id"))

    entity_id = clean_text(issue.get("entity_id"))
    match = re.search(r"\bV\d{3}\b", entity_id)

    return match.group(0) if match else ""


def create_investigation_result(
    *,
    root_cause_category: str,
    root_cause_summary: str,
    explanation_points: list[str],
    evidence_summary: str,
    investigation_focus: str,
) -> dict:
    """Create a standardized intermediate investigation result."""

    explanation_points = [
        clean_text(point)
        for point in explanation_points
        if clean_text(point)
    ]

    if not explanation_points:
        explanation_points = [
            "Available data did not identify a stronger contributing factor."
        ]

    return {
        "root_cause_category": root_cause_category,
        "root_cause_summary": root_cause_summary,
        "contributing_factors": " ".join(explanation_points),
        "evidence_summary": evidence_summary,
        "investigation_focus": investigation_focus,
    }


def load_executive_priority_reference(limit: int) -> pd.DataFrame:
    """Load the current executive issue list that should be analyzed."""

    if not EXECUTIVE_PRIORITY_FILE.exists():
        raise FileNotFoundError(
            "Executive priority file was not found. Run this first:\n"
            "python -m backend.analytics.executive_priority_selector"
        )

    priorities = pd.read_csv(EXECUTIVE_PRIORITY_FILE, dtype=object)

    required_columns = {
        "issue_id",
        "executive_rank",
        "executive_score",
    }

    missing_columns = required_columns.difference(priorities.columns)

    if missing_columns:
        raise ValueError(
            "Executive priority CSV is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    priorities["executive_rank"] = pd.to_numeric(
        priorities["executive_rank"],
        errors="coerce",
    )

    priorities["executive_score"] = pd.to_numeric(
        priorities["executive_score"],
        errors="coerce",
    )

    priorities = priorities.dropna(
        subset=["issue_id", "executive_rank"]
    )

    return priorities.sort_values("executive_rank").head(limit)[
        [
            "issue_id",
            "executive_rank",
            "executive_score",
        ]
    ].copy()


def load_selected_issues(
    engine: Engine,
    priority_reference: pd.DataFrame,
) -> pd.DataFrame:
    """Load active PostgreSQL issue details for executive priorities."""

    query = """
    SELECT
        issue_id,
        title,
        issue_type,
        business_area,
        priority_level,
        priority_score,
        priority_reason,
        status,
        entity_type,
        entity_id,
        store_id,
        product_id,
        vendor_id,
        period_label,
        finding_count,
        high_finding_count,
        medium_finding_count,
        low_finding_count,
        summary,
        evidence_summary,
        last_detected_at
    FROM issues
    WHERE status IN ('Open', 'In Progress');
    """

    issues = read_query(engine, query)

    if issues.empty:
        return issues

    selected_issues = priority_reference.merge(
        issues,
        on="issue_id",
        how="inner",
    )

    return selected_issues.sort_values(
        "executive_rank"
    ).reset_index(drop=True)


def load_selected_evidence(
    engine: Engine,
    issue_ids: list[str],
) -> pd.DataFrame:
    """Load evidence only for selected executive issues."""

    if not issue_ids:
        return pd.DataFrame(columns=EVIDENCE_COLUMNS)

    query = """
    SELECT
        issue_id,
        source_finding_id,
        source_report,
        source_module,
        analysis_type,
        business_area,
        severity,
        entity_type,
        entity_id,
        store_id,
        product_id,
        vendor_id,
        summary,
        evidence,
        detected_at
    FROM issue_evidence;
    """

    evidence = read_query(engine, query)

    if evidence.empty:
        return pd.DataFrame(columns=EVIDENCE_COLUMNS)

    return evidence[evidence["issue_id"].isin(issue_ids)].copy()


def get_store_finance_context(
    engine: Engine,
    store_id: str,
    period_label: str | None,
) -> pd.Series | None:
    """Return selected-month finance context with prior-period comparison."""

    if not store_id:
        return None

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
    WHERE month = COALESCE(
        :period_label,
        (SELECT MAX(month) FROM finance_history)
    );
    """

    finance_data = read_query(
        engine,
        query,
        {
            "store_id": store_id,
            "period_label": period_label,
        },
    )

    return finance_data.iloc[0] if not finance_data.empty else None


def get_store_sales_context(
    engine: Engine,
    store_id: str,
    period_label: str | None,
) -> pd.Series | None:
    """Return selected-month store sales with previous-month comparison."""

    if not store_id:
        return None

    query = """
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
    WHERE month = COALESCE(
        :period_label,
        (SELECT MAX(month) FROM sales_history)
    );
    """

    sales_data = read_query(
        engine,
        query,
        {
            "store_id": store_id,
            "period_label": period_label,
        },
    )

    return sales_data.iloc[0] if not sales_data.empty else None


def get_store_category_decline(
    engine: Engine,
    store_id: str,
    current_month: str,
    previous_month: str,
) -> pd.Series | None:
    """Return the largest negative category movement for one store."""

    if not store_id or not current_month or not previous_month:
        return None

    query = """
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
    LIMIT 1;
    """

    category_data = read_query(
        engine,
        query,
        {
            "store_id": store_id,
            "current_month": current_month,
            "previous_month": previous_month,
        },
    )

    return category_data.iloc[0] if not category_data.empty else None


def get_store_inventory_summary(
    engine: Engine,
    store_id: str,
) -> pd.Series | None:
    """Return inventory-risk counts for one store."""

    if not store_id:
        return None

    query = """
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

    inventory_data = read_query(
        engine,
        query,
        {"store_id": store_id},
    )

    return inventory_data.iloc[0] if not inventory_data.empty else None


def get_store_complaint_summary(
    engine: Engine,
    store_id: str,
    period_label: str | None = None,
) -> pd.Series | None:
    """Return overall or selected-month complaint metrics for one store."""

    if not store_id:
        return None

    query = """
    SELECT
        COUNT(*) AS total_complaints,
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaints,
        COUNT(*) FILTER (
            WHERE status IN ('Open', 'In Progress')
        ) AS unresolved_complaints
    FROM complaints
    WHERE
        store_id = :store_id
        AND (
            :period_label IS NULL
            OR TO_CHAR(date, 'YYYY-MM') = :period_label
        );
    """

    complaint_data = read_query(
        engine,
        query,
        {
            "store_id": store_id,
            "period_label": period_label,
        },
    )

    return complaint_data.iloc[0] if not complaint_data.empty else None


def get_inventory_product_context(
    engine: Engine,
    store_id: str,
    product_id: str,
) -> pd.Series | None:
    """Return latest stock, complaint, and vendor context for one product."""

    if not store_id or not product_id:
        return None

    query = """
    SELECT
        i.inventory_id,
        i.date AS inventory_date,
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
    LEFT JOIN vendors AS v
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
        query,
        {
            "store_id": store_id,
            "product_id": product_id,
        },
    )

    return inventory_data.iloc[0] if not inventory_data.empty else None


def get_vendor_delivery_context(
    engine: Engine,
    vendor_id: str,
) -> pd.Series | None:
    """Return overall vendor delivery performance metrics."""

    if not vendor_id:
        return None

    query = """
    SELECT
        vendor_id,
        MAX(vendor_name) AS vendor_name,
        COUNT(*) AS delivery_count,
        AVG(delay_days) AS average_delay_days,
        MAX(delay_days) AS maximum_delay_days,
        COUNT(*) FILTER (
            WHERE delay_days > 0
        ) AS delayed_deliveries,
        COUNT(*) FILTER (
            WHERE received_quantity < ordered_quantity
        ) AS partial_deliveries,
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
    WHERE vendor_id = :vendor_id
    GROUP BY vendor_id;
    """

    vendor_data = read_query(
        engine,
        query,
        {"vendor_id": vendor_id},
    )

    return vendor_data.iloc[0] if not vendor_data.empty else None


def get_vendor_affected_stores(
    engine: Engine,
    vendor_id: str,
) -> pd.DataFrame:
    """Return stores most affected by a vendor's delivery performance."""

    if not vendor_id:
        return pd.DataFrame()

    query = """
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

    return read_query(
        engine,
        query,
        {"vendor_id": vendor_id},
    )


def get_store_complaint_breakdown(
    engine: Engine,
    store_id: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return main complaint types and products for one store."""

    if not store_id:
        return pd.DataFrame(), pd.DataFrame()

    type_query = """
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
        MAX(product_name) AS product_name,
        COUNT(*) AS complaint_count,
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaints
    FROM complaints
    WHERE store_id = :store_id
    GROUP BY product_id
    ORDER BY
        complaint_count DESC,
        high_severity_complaints DESC
    LIMIT 3;
    """

    return (
        read_query(
            engine,
            type_query,
            {"store_id": store_id},
        ),
        read_query(
            engine,
            product_query,
            {"store_id": store_id},
        ),
    )


def get_product_complaint_context(
    engine: Engine,
    product_id: str,
    store_id: str | None,
) -> pd.Series | None:
    """Return complaint metrics for a product, optionally at one store."""

    if not product_id:
        return None

    query = """
    SELECT
        MAX(product_name) AS product_name,
        COUNT(*) AS total_complaints,
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaints,
        COUNT(*) FILTER (
            WHERE status IN ('Open', 'In Progress')
        ) AS unresolved_complaints,
        COUNT(*) FILTER (
            WHERE complaint_type = 'Out of Stock'
        ) AS out_of_stock_complaints
    FROM complaints
    WHERE
        product_id = :product_id
        AND (
            :store_id IS NULL
            OR store_id = :store_id
        );
    """

    complaint_data = read_query(
        engine,
        query,
        {
            "product_id": product_id,
            "store_id": store_id or None,
        },
    )

    return complaint_data.iloc[0] if not complaint_data.empty else None


def get_product_sales_context(
    engine: Engine,
    product_id: str,
    store_id: str | None,
    period_label: str | None,
) -> pd.Series | None:
    """Return current and previous period sales for a product."""

    if not product_id:
        return None

    query = """
    WITH monthly_product_sales AS (
        SELECT
            product_id,
            MAX(product_name) AS product_name,
            MAX(category) AS category,
            TO_CHAR(date, 'YYYY-MM') AS month,
            SUM(total_sales) AS monthly_sales,
            SUM(profit) AS monthly_profit
        FROM sales
        WHERE
            product_id = :product_id
            AND (
                :store_id IS NULL
                OR store_id = :store_id
            )
        GROUP BY
            product_id,
            TO_CHAR(date, 'YYYY-MM')
    ),
    sales_history AS (
        SELECT
            product_id,
            product_name,
            category,
            month,
            monthly_sales,
            monthly_profit,
            LAG(month) OVER (
                PARTITION BY product_id
                ORDER BY month
            ) AS previous_month,
            LAG(monthly_sales) OVER (
                PARTITION BY product_id
                ORDER BY month
            ) AS previous_sales
        FROM monthly_product_sales
    )
    SELECT *
    FROM sales_history
    WHERE month = COALESCE(
        :period_label,
        (SELECT MAX(month) FROM sales_history)
    );
    """

    sales_data = read_query(
        engine,
        query,
        {
            "product_id": product_id,
            "store_id": store_id or None,
            "period_label": period_label,
        },
    )

    return sales_data.iloc[0] if not sales_data.empty else None


def get_complaint_category_context(
    engine: Engine,
    complaint_type: str,
) -> pd.Series | None:
    """Return overall evidence for a repeated complaint category."""

    if not complaint_type:
        return None

    query = """
    SELECT
        COUNT(*) AS total_complaints,
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaints,
        COUNT(*) FILTER (
            WHERE status IN ('Open', 'In Progress')
        ) AS unresolved_complaints,
        COUNT(DISTINCT store_id) AS affected_store_count,
        COUNT(DISTINCT product_id) AS affected_product_count
    FROM complaints
    WHERE complaint_type = :complaint_type;
    """

    category_data = read_query(
        engine,
        query,
        {"complaint_type": complaint_type},
    )

    return category_data.iloc[0] if not category_data.empty else None


def investigate_store_performance(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Investigate financial, sales, inventory, and complaint drivers."""

    store_id = get_store_id(issue)
    period_label = get_period_label(issue)

    finance_row = get_store_finance_context(
        engine,
        store_id,
        period_label,
    )

    sales_row = get_store_sales_context(
        engine,
        store_id,
        period_label,
    )

    selected_month = period_label
    factors: list[str] = []
    evidence_parts: list[str] = []

    if finance_row is not None:
        selected_month = (
            clean_text(finance_row["month"])
            or selected_month
        )

        previous_month = clean_text(
            finance_row["previous_month"]
        )

        revenue = safe_float(finance_row["total_revenue"])
        operating_profit = safe_float(
            finance_row["operating_profit"]
        )

        operating_expense = safe_float(
            finance_row["operating_expense"]
        )

        target_achievement = safe_float(
            finance_row["target_achievement_percent"]
        )

        previous_revenue = safe_float(
            finance_row["previous_revenue"]
        )

        profit_margin = (
            (operating_profit / revenue) * 100
            if revenue > 0
            else 0.0
        )

        revenue_change = (
            ((revenue - previous_revenue) / previous_revenue)
            * 100
            if previous_revenue > 0
            else 0.0
        )

        evidence_parts.append(
            f"Revenue: {format_currency(revenue)}; "
            f"Operating Profit: {format_currency(operating_profit)}; "
            f"Target Achievement: {target_achievement:.2f}%; "
            f"Risk Status: {clean_text(finance_row['risk_status'])}."
        )

        if target_achievement < 70:
            factors.append(
                f"Target achievement was only "
                f"{target_achievement:.2f}% in {selected_month}."
            )

        if revenue_change < 0:
            factors.append(
                f"Revenue declined by "
                f"{abs(revenue_change):.2f}% from "
                f"{previous_month or 'the previous period'}."
            )

        if profit_margin < 10:
            factors.append(
                f"Operating profit margin was only "
                f"{profit_margin:.2f}%."
            )

        if operating_expense > 0:
            factors.append(
                f"Operating expenses were "
                f"{format_currency(operating_expense)}."
            )

    if sales_row is not None:
        current_month = (
            clean_text(sales_row["month"])
            or selected_month
        )

        previous_sales_month = clean_text(
            sales_row["previous_month"]
        )

        current_sales = safe_float(
            sales_row["monthly_sales"]
        )

        previous_sales = safe_float(
            sales_row["previous_sales"]
        )

        sales_decline = (
            ((previous_sales - current_sales) / previous_sales)
            * 100
            if previous_sales > 0
            else 0.0
        )

        evidence_parts.append(
            f"Store Sales: {format_currency(current_sales)} "
            f"for {current_month or 'the selected period'}."
        )

        if sales_decline > 0:
            factors.append(
                f"Store sales declined by "
                f"{sales_decline:.2f}% compared with "
                f"{previous_sales_month or 'the previous period'}."
            )

        category_row = get_store_category_decline(
            engine,
            store_id,
            current_month,
            previous_sales_month,
        )

        if category_row is not None:
            current_category_sales = safe_float(
                category_row["current_sales"]
            )

            previous_category_sales = safe_float(
                category_row["previous_sales"]
            )

            category_decline = (
                (
                    (previous_category_sales - current_category_sales)
                    / previous_category_sales
                )
                * 100
                if previous_category_sales > 0
                else 0.0
            )

            if category_decline > 0:
                factors.append(
                    f"{clean_text(category_row['category'])} "
                    f"was the largest declining category, falling by "
                    f"{category_decline:.2f}%."
                )

    inventory_row = get_store_inventory_summary(
        engine,
        store_id,
    )

    if inventory_row is not None:
        low_stock_items = safe_int(
            inventory_row["low_stock_items"]
        )

        reorder_soon_items = safe_int(
            inventory_row["reorder_soon_items"]
        )

        if low_stock_items > 0 or reorder_soon_items > 0:
            factors.append(
                f"The store has {low_stock_items} Low Stock and "
                f"{reorder_soon_items} Reorder Soon inventory "
                f"records."
            )

    complaint_row = get_store_complaint_summary(
        engine,
        store_id,
        selected_month,
    )

    if complaint_row is not None:
        complaint_count = safe_int(
            complaint_row["total_complaints"]
        )

        high_complaints = safe_int(
            complaint_row["high_severity_complaints"]
        )

        if complaint_count > 0:
            factors.append(
                f"{complaint_count} complaints were recorded in "
                f"{selected_month or 'the selected period'}, "
                f"including {high_complaints} High-severity cases."
            )

    return create_investigation_result(
        root_cause_category=(
            "Multi-Factor Store Performance Deterioration"
        ),
        root_cause_summary=(
            "Likely multi-factor deterioration involving sales, "
            "financial, inventory, and customer-experience "
            "conditions."
        ),
        explanation_points=factors,
        evidence_summary=" ".join(evidence_parts)
        or "Store-level finance and sales context was not available.",
        investigation_focus=(
            "Review declining categories, local sales execution, "
            "inventory availability, customer complaints, "
            "discounting practices, and operating-cost drivers."
        ),
    )


def investigate_product_availability(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Investigate stock, customer, and supplier causes."""

    store_id = get_store_id(issue)
    product_id = get_product_id(issue)

    inventory_row = get_inventory_product_context(
        engine,
        store_id,
        product_id,
    )

    if inventory_row is None:
        return create_investigation_result(
            root_cause_category=(
                "Inventory Replenishment and Supply Risk"
            ),
            root_cause_summary=(
                "The issue could not be matched to a current "
                "inventory record."
            ),
            explanation_points=[
                "Verify the store-product combination and refresh "
                "the inventory snapshot."
            ],
            evidence_summary=(
                "No matching inventory record was returned."
            ),
            investigation_focus=(
                "Verify the store-product key, recent stock "
                "movement, and replenishment records."
            ),
        )

    current_stock = safe_float(
        inventory_row["current_stock"]
    )

    reorder_level = safe_float(
        inventory_row["reorder_level"]
    )

    stock_ratio = (
        (current_stock / reorder_level) * 100
        if reorder_level > 0
        else 0.0
    )

    factors: list[str] = [
        f"Current stock is {current_stock:.0f} units against a "
        f"reorder level of {reorder_level:.0f} units "
        f"({stock_ratio:.2f}% of the reorder level)."
    ]

    related_complaints = safe_int(
        inventory_row["related_complaints"]
    )

    high_complaints = safe_int(
        inventory_row["high_severity_complaints"]
    )

    unresolved_complaints = safe_int(
        inventory_row["unresolved_complaints"]
    )

    out_of_stock_complaints = safe_int(
        inventory_row["out_of_stock_complaints"]
    )

    if related_complaints > 0:
        factors.append(
            f"The product is linked to {related_complaints} "
            f"complaints, including {high_complaints} "
            f"High-severity cases."
        )

    if unresolved_complaints > 0:
        factors.append(
            f"{unresolved_complaints} related complaints remain "
            "Open or In Progress."
        )

    if out_of_stock_complaints > 0:
        factors.append(
            f"{out_of_stock_complaints} related complaints are "
            "categorized as Out of Stock."
        )

    vendor_row = get_vendor_delivery_context(
        engine,
        clean_text(inventory_row["vendor_id"]),
    )

    if vendor_row is not None:
        average_delay = safe_float(
            vendor_row["average_delay_days"]
        )

        maximum_delay = safe_float(
            vendor_row["maximum_delay_days"]
        )

        delayed_deliveries = safe_int(
            vendor_row["delayed_deliveries"]
        )

        partial_deliveries = safe_int(
            vendor_row["partial_deliveries"]
        )

        on_time_rate = safe_float(
            vendor_row["on_time_delivery_rate"]
        )

        if average_delay >= 3 or delayed_deliveries >= 2:
            factors.append(
                f"Supplier {clean_text(inventory_row['vendor_name'])} "
                f"has an average delay of {average_delay:.2f} days "
                f"across {delayed_deliveries} delayed deliveries."
            )

        if maximum_delay >= 10:
            factors.append(
                f"The supplier's maximum observed delay is "
                f"{maximum_delay:.0f} days."
            )

        if partial_deliveries > 0:
            factors.append(
                f"The supplier has {partial_deliveries} "
                "partial deliveries."
            )

        if on_time_rate < 70:
            factors.append(
                f"Supplier on-time delivery rate is only "
                f"{on_time_rate:.2f}%."
            )

    return create_investigation_result(
        root_cause_category=(
            "Inventory Replenishment and Supply Risk"
        ),
        root_cause_summary=(
            "Likely inventory replenishment failure because "
            "available stock is materially below the operational "
            "reorder requirement."
        ),
        explanation_points=factors,
        evidence_summary=(
            f"Store: {clean_text(inventory_row['store_name'])}; "
            f"Product: {clean_text(inventory_row['product_name'])}; "
            f"Stock Status: {clean_text(inventory_row['stock_status'])}; "
            f"Current Stock: {current_stock:.0f}; "
            f"Reorder Level: {reorder_level:.0f}; "
            f"Related Complaints: {related_complaints}."
        ),
        investigation_focus=(
            "Review the latest purchase order, vendor delivery "
            "status, sales velocity, stock-transfer availability, "
            "and replenishment approval process."
        ),
    )


def investigate_vendor_performance(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Investigate delivery reliability, quantity, and quality risk."""

    vendor_id = get_vendor_id(issue)

    vendor_row = get_vendor_delivery_context(
        engine,
        vendor_id,
    )

    if vendor_row is None:
        return create_investigation_result(
            root_cause_category=(
                "Vendor Reliability and Fulfilment Risk"
            ),
            root_cause_summary=(
                "The vendor issue could not be matched to delivery "
                "records."
            ),
            explanation_points=[
                "Verify the vendor ID and current vendor-delivery "
                "records."
            ],
            evidence_summary=(
                "No matching vendor-delivery record was returned."
            ),
            investigation_focus=(
                "Validate the vendor key and inspect recent "
                "delivery records."
            ),
        )

    average_delay = safe_float(
        vendor_row["average_delay_days"]
    )

    maximum_delay = safe_float(
        vendor_row["maximum_delay_days"]
    )

    delayed_deliveries = safe_int(
        vendor_row["delayed_deliveries"]
    )

    partial_deliveries = safe_int(
        vendor_row["partial_deliveries"]
    )

    quality_rating = safe_float(
        vendor_row["average_quality_rating"]
    )

    on_time_rate = safe_float(
        vendor_row["on_time_delivery_rate"]
    )

    factors: list[str] = []

    if average_delay > 0:
        factors.append(
            f"Average delivery delay is {average_delay:.2f} days."
        )

    if maximum_delay > 0:
        factors.append(
            f"Maximum observed delivery delay is "
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

    if on_time_rate < 70:
        factors.append(
            f"On-time delivery rate is only {on_time_rate:.2f}%."
        )

    if quality_rating < 4:
        factors.append(
            f"Average quality rating is {quality_rating:.2f} out of 5."
        )

    affected_stores = get_vendor_affected_stores(
        engine,
        vendor_id,
    )

    if not affected_stores.empty:
        affected_store = affected_stores.iloc[0]

        factors.append(
            f"The most affected store is "
            f"{clean_text(affected_store['store_name'])}, "
            f"where the average delay is "
            f"{safe_float(affected_store['average_delay_days']):.2f} "
            "days."
        )

    return create_investigation_result(
        root_cause_category=(
            "Vendor Reliability and Fulfilment Risk"
        ),
        root_cause_summary=(
            "Likely supplier reliability issue involving delayed, "
            "incomplete, or inconsistent deliveries."
        ),
        explanation_points=factors,
        evidence_summary=(
            f"Vendor: {clean_text(vendor_row['vendor_name'])}; "
            f"Delivery Count: {safe_int(vendor_row['delivery_count'])}; "
            f"Average Delay: {average_delay:.2f} days; "
            f"Maximum Delay: {maximum_delay:.0f} days; "
            f"On-Time Delivery Rate: {on_time_rate:.2f}%; "
            f"Average Quality Rating: {quality_rating:.2f}."
        ),
        investigation_focus=(
            "Review service-level agreement compliance, "
            "purchase-order planning, supplier capacity, product "
            "quality checks, and backup supplier availability."
        ),
    )


def investigate_complaint_backlog(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Investigate unresolved customer-support backlog."""

    store_id = get_store_id(issue)

    summary_row = get_store_complaint_summary(
        engine,
        store_id,
    )

    type_data, product_data = get_store_complaint_breakdown(
        engine,
        store_id,
    )

    inventory_row = get_store_inventory_summary(
        engine,
        store_id,
    )

    factors: list[str] = []

    if summary_row is None:
        return create_investigation_result(
            root_cause_category=(
                "Customer Support Resolution and Escalation Backlog"
            ),
            root_cause_summary=(
                "The complaint backlog issue could not be matched "
                "to complaint records."
            ),
            explanation_points=[
                "Verify the store ID and reload complaint data."
            ],
            evidence_summary=(
                "No complaint summary was returned."
            ),
            investigation_focus=(
                "Verify the store key and current complaint records."
            ),
        )

    total_complaints = safe_int(
        summary_row["total_complaints"]
    )

    high_complaints = safe_int(
        summary_row["high_severity_complaints"]
    )

    unresolved_complaints = safe_int(
        summary_row["unresolved_complaints"]
    )

    if unresolved_complaints > 0:
        factors.append(
            f"{unresolved_complaints} complaints are Open or "
            "In Progress."
        )

    if high_complaints > 0:
        factors.append(
            f"{high_complaints} complaints are High severity."
        )

    if not type_data.empty:
        top_type = type_data.iloc[0]

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

    if inventory_row is not None:
        low_stock_items = safe_int(
            inventory_row["low_stock_items"]
        )

        reorder_soon_items = safe_int(
            inventory_row["reorder_soon_items"]
        )

        if low_stock_items > 0 or reorder_soon_items > 0:
            factors.append(
                f"The store has {low_stock_items} Low Stock and "
                f"{reorder_soon_items} Reorder Soon records, "
                "which may be contributing to service-related "
                "complaints."
            )

    return create_investigation_result(
        root_cause_category=(
            "Customer Support Resolution and Escalation Backlog"
        ),
        root_cause_summary=(
            "Likely delay in complaint resolution, escalation "
            "handling, or support-capacity management."
        ),
        explanation_points=factors,
        evidence_summary=(
            f"Total Complaints: {total_complaints}; "
            f"High-Severity Complaints: {high_complaints}; "
            f"Open or In-Progress Complaints: "
            f"{unresolved_complaints}."
        ),
        investigation_focus=(
            "Review backlog ownership, ageing cases, frontline "
            "escalation, main complaint categories, and "
            "store-manager resolution workflow."
        ),
    )


def investigate_product_complaint_risk(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Investigate product-level customer-experience risk."""

    product_id = get_product_id(issue)
    store_id = get_store_id(issue) or None

    complaint_row = get_product_complaint_context(
        engine,
        product_id,
        store_id,
    )

    factors: list[str] = []

    if complaint_row is None:
        return create_investigation_result(
            root_cause_category=(
                "Product Quality, Availability, or Service Experience Risk"
            ),
            root_cause_summary=(
                "The product complaint issue could not be matched "
                "to complaint records."
            ),
            explanation_points=[
                "Verify the product ID and refresh complaint data."
            ],
            evidence_summary=(
                "No product complaint context was returned."
            ),
            investigation_focus=(
                "Validate product mapping, complaint classification, "
                "and availability records."
            ),
        )

    total_complaints = safe_int(
        complaint_row["total_complaints"]
    )

    high_complaints = safe_int(
        complaint_row["high_severity_complaints"]
    )

    unresolved_complaints = safe_int(
        complaint_row["unresolved_complaints"]
    )

    out_of_stock_complaints = safe_int(
        complaint_row["out_of_stock_complaints"]
    )

    factors.append(
        f"The product has {total_complaints} complaints, "
        f"including {high_complaints} High-severity cases."
    )

    if unresolved_complaints > 0:
        factors.append(
            f"{unresolved_complaints} product-related complaints "
            "remain Open or In Progress."
        )

    if out_of_stock_complaints > 0:
        factors.append(
            f"{out_of_stock_complaints} cases are categorized "
            "as Out of Stock."
        )

    if store_id:
        inventory_row = get_inventory_product_context(
            engine,
            store_id,
            product_id,
        )

        if inventory_row is not None:
            current_stock = safe_float(
                inventory_row["current_stock"]
            )

            reorder_level = safe_float(
                inventory_row["reorder_level"]
            )

            stock_ratio = (
                (current_stock / reorder_level) * 100
                if reorder_level > 0
                else 0.0
            )

            if stock_ratio < 80:
                factors.append(
                    f"At the affected store, stock is only "
                    f"{stock_ratio:.2f}% of the reorder level."
                )

    return create_investigation_result(
        root_cause_category=(
            "Product Quality, Availability, or Service Experience Risk"
        ),
        root_cause_summary=(
            "Likely recurring product-level customer-experience "
            "issue requiring quality, availability, and fulfilment "
            "review."
        ),
        explanation_points=factors,
        evidence_summary=(
            f"Product: {clean_text(complaint_row['product_name'])}; "
            f"Total Complaints: {total_complaints}; "
            f"High-Severity Complaints: {high_complaints}; "
            f"Unresolved Complaints: {unresolved_complaints}."
        ),
        investigation_focus=(
            "Review product quality, packaging, store availability, "
            "fulfilment process, and recurring customer complaint "
            "categories."
        ),
    )


def investigate_product_sales_performance(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Investigate demand, commercial, and availability causes."""

    product_id = get_product_id(issue)
    store_id = get_store_id(issue) or None
    period_label = get_period_label(issue)

    sales_row = get_product_sales_context(
        engine,
        product_id,
        store_id,
        period_label,
    )

    if sales_row is None:
        return create_investigation_result(
            root_cause_category=(
                "Product Demand and Commercial Performance Risk"
            ),
            root_cause_summary=(
                "The product sales issue could not be matched to "
                "transaction history."
            ),
            explanation_points=[
                "Verify the product ID, period label, and sales "
                "data refresh."
            ],
            evidence_summary=(
                "No matching product sales history was returned."
            ),
            investigation_focus=(
                "Review product mapping, pricing, distribution, "
                "and sales data."
            ),
        )

    current_sales = safe_float(sales_row["monthly_sales"])
    previous_sales = safe_float(sales_row["previous_sales"])

    current_month = clean_text(sales_row["month"])
    previous_month = clean_text(sales_row["previous_month"])

    sales_change = (
        ((current_sales - previous_sales) / previous_sales) * 100
        if previous_sales > 0
        else 0.0
    )

    factors: list[str] = []

    if sales_change < 0:
        factors.append(
            f"Product sales declined by {abs(sales_change):.2f}% "
            f"in {current_month} compared with "
            f"{previous_month or 'the prior period'}."
        )

    if store_id:
        inventory_row = get_inventory_product_context(
            engine,
            store_id,
            product_id,
        )

        if inventory_row is not None:
            current_stock = safe_float(
                inventory_row["current_stock"]
            )

            reorder_level = safe_float(
                inventory_row["reorder_level"]
            )

            stock_ratio = (
                (current_stock / reorder_level) * 100
                if reorder_level > 0
                else 0.0
            )

            if stock_ratio < 80:
                factors.append(
                    f"Stock availability is constrained at "
                    f"{stock_ratio:.2f}% of reorder level."
                )

    return create_investigation_result(
        root_cause_category=(
            "Product Demand and Commercial Performance Risk"
        ),
        root_cause_summary=(
            "Likely weakness in product demand, pricing, assortment, "
            "local commercial execution, or availability."
        ),
        explanation_points=factors,
        evidence_summary=(
            f"Product: {clean_text(sales_row['product_name'])}; "
            f"Category: {clean_text(sales_row['category'])}; "
            f"Current Sales: {format_currency(current_sales)}; "
            f"Previous Sales: {format_currency(previous_sales)}."
        ),
        investigation_focus=(
            "Review pricing, promotions, assortment visibility, "
            "local demand, competitor activity, and product "
            "availability."
        ),
    )


def investigate_inventory_overstock(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Investigate demand-planning risk behind an overstock issue."""

    store_id = get_store_id(issue)
    product_id = get_product_id(issue)

    inventory_row = get_inventory_product_context(
        engine,
        store_id,
        product_id,
    )

    if inventory_row is None:
        return create_investigation_result(
            root_cause_category=(
                "Inventory Planning and Demand Forecast Risk"
            ),
            root_cause_summary=(
                "The overstock issue could not be matched to a "
                "current inventory record."
            ),
            explanation_points=[
                "Verify the store-product mapping and inventory "
                "snapshot."
            ],
            evidence_summary=(
                "No matching inventory record was returned."
            ),
            investigation_focus=(
                "Review inventory snapshot, replenishment quantity, "
                "and demand plan."
            ),
        )

    current_stock = safe_float(
        inventory_row["current_stock"]
    )

    reorder_level = safe_float(
        inventory_row["reorder_level"]
    )

    stock_ratio = (
        (current_stock / reorder_level) * 100
        if reorder_level > 0
        else 0.0
    )

    factors = [
        f"Current stock is {current_stock:.0f} units against a "
        f"reorder level of {reorder_level:.0f} units "
        f"({stock_ratio:.2f}% of reorder level)."
    ]

    product_sales = get_product_sales_context(
        engine,
        product_id,
        store_id or None,
        get_period_label(issue),
    )

    if product_sales is not None:
        current_sales = safe_float(
            product_sales["monthly_sales"]
        )

        previous_sales = safe_float(
            product_sales["previous_sales"]
        )

        sales_change = (
            ((current_sales - previous_sales) / previous_sales)
            * 100
            if previous_sales > 0
            else 0.0
        )

        if sales_change <= 0:
            factors.append(
                f"Product sales changed by {sales_change:.2f}% "
                "versus the previous period, suggesting inventory "
                "may be outpacing demand."
            )

    return create_investigation_result(
        root_cause_category=(
            "Inventory Planning and Demand Forecast Risk"
        ),
        root_cause_summary=(
            "Likely mismatch between replenishment planning and "
            "actual product demand."
        ),
        explanation_points=factors,
        evidence_summary=(
            f"Store: {clean_text(inventory_row['store_name'])}; "
            f"Product: {clean_text(inventory_row['product_name'])}; "
            f"Stock Status: {clean_text(inventory_row['stock_status'])}; "
            f"Current Stock: {current_stock:.0f}; "
            f"Reorder Level: {reorder_level:.0f}."
        ),
        investigation_focus=(
            "Review demand forecast accuracy, replenishment "
            "quantity, product velocity, transfer opportunities, "
            "and promotion or markdown options."
        ),
    )


def investigate_repeated_complaint_category(
    engine: Engine,
    issue: pd.Series,
) -> dict:
    """Investigate systemic failure patterns in a complaint category."""

    complaint_type = clean_text(issue.get("entity_id"))

    category_row = get_complaint_category_context(
        engine,
        complaint_type,
    )

    if category_row is None:
        return create_investigation_result(
            root_cause_category=(
                "Recurring Process or Product Failure Pattern"
            ),
            root_cause_summary=(
                "The repeated complaint category could not be "
                "matched to complaint records."
            ),
            explanation_points=[
                "Verify the complaint-category label and current "
                "complaint data."
            ],
            evidence_summary=(
                "No complaint-category summary was returned."
            ),
            investigation_focus=(
                "Review complaint classification and recurring "
                "process failures."
            ),
        )

    total_complaints = safe_int(
        category_row["total_complaints"]
    )

    high_complaints = safe_int(
        category_row["high_severity_complaints"]
    )

    unresolved_complaints = safe_int(
        category_row["unresolved_complaints"]
    )

    affected_stores = safe_int(
        category_row["affected_store_count"]
    )

    affected_products = safe_int(
        category_row["affected_product_count"]
    )

    factors = [
        f"{complaint_type} appears in {total_complaints} "
        f"complaints across {affected_stores} stores and "
        f"{affected_products} products."
    ]

    if high_complaints > 0:
        factors.append(
            f"{high_complaints} cases are High severity."
        )

    if unresolved_complaints > 0:
        factors.append(
            f"{unresolved_complaints} cases are Open or "
            "In Progress."
        )

    return create_investigation_result(
        root_cause_category=(
            "Recurring Process or Product Failure Pattern"
        ),
        root_cause_summary=(
            "Likely recurring process, product-condition, or "
            "service-delivery failure pattern."
        ),
        explanation_points=factors,
        evidence_summary=(
            f"Complaint Category: {complaint_type}; "
            f"Total Cases: {total_complaints}; "
            f"High-Severity Cases: {high_complaints}; "
            f"Unresolved Cases: {unresolved_complaints}."
        ),
        investigation_focus=(
            "Review the end-to-end process associated with this "
            "complaint category, including product handling, "
            "fulfilment, and service steps across affected stores."
        ),
    )


def investigate_generic_issue(
    issue: pd.Series,
    issue_evidence: pd.DataFrame,
) -> dict:
    """Return a safe fallback where no specialized rule exists."""

    evidence_types = unique_non_empty(
        issue_evidence["analysis_type"]
    )

    return create_investigation_result(
        root_cause_category=(
            "Cross-Functional Business Risk"
        ),
        root_cause_summary=(
            "Likely cross-functional risk requiring management "
            "review of the available supporting evidence."
        ),
        explanation_points=[
            (
                "Supporting analysis types: "
                + ", ".join(evidence_types[:5])
            )
            if evidence_types
            else "No detailed evidence type was available."
        ],
        evidence_summary=clean_text(
            issue.get("evidence_summary")
        ),
        investigation_focus=(
            "Review linked evidence, entity-level records, and "
            "relevant operational owners before confirming a "
            "root cause."
        ),
    )


def calculate_confidence_score(
    issue_evidence: pd.DataFrame,
    root_cause_category: str,
) -> float:
    """Calculate evidence-strength confidence, not certainty."""

    evidence_count = len(issue_evidence)

    evidence_types = unique_non_empty(
        issue_evidence["analysis_type"]
    )

    high_evidence_count = safe_int(
        issue_evidence["severity"]
        .astype(str)
        .str.strip()
        .eq("High")
        .sum()
    )

    confidence = 52.0
    confidence += min(evidence_count, 6) * 3.0
    confidence += min(len(evidence_types), 5) * 4.0
    confidence += min(high_evidence_count, 4) * 2.0

    if root_cause_category == (
        "Inventory Replenishment and Supply Risk"
    ):
        confidence += 5.0

    elif root_cause_category == (
        "Vendor Reliability and Fulfilment Risk"
    ):
        confidence += 4.0

    elif root_cause_category == (
        "Multi-Factor Store Performance Deterioration"
    ):
        confidence += 3.0

    return round(min(confidence, 92.0), 2)


def build_root_cause_explanation(
    issue: pd.Series,
    investigation: dict,
) -> str:
    """Build final explanation with cautious analytical wording."""

    return (
        f"Assessment for '{clean_text(issue['title'])}': "
        f"{clean_text(investigation['contributing_factors'])} "
        "This is an evidence-based likely-cause assessment and "
        "requires human review before an action is approved."
    )


def build_supporting_evidence_json(
    issue_evidence: pd.DataFrame,
) -> str:
    """Serialize strongest evidence records for PostgreSQL."""

    if issue_evidence.empty:
        return json.dumps([])

    evidence_copy = issue_evidence.copy()

    evidence_copy["severity_order"] = (
        evidence_copy["severity"]
        .map(SEVERITY_ORDER)
        .fillna(4)
    )

    evidence_copy = evidence_copy.sort_values(
        by=[
            "severity_order",
            "analysis_type",
            "detected_at",
        ],
        ascending=[
            True,
            True,
            False,
        ],
        na_position="last",
    ).head(12)

    records = []

    for _, row in evidence_copy.iterrows():
        records.append(
            {
                "source_finding_id": clean_text(
                    row["source_finding_id"]
                ),
                "source_module": clean_text(
                    row["source_module"]
                ),
                "analysis_type": clean_text(
                    row["analysis_type"]
                ),
                "business_area": clean_text(
                    row["business_area"]
                ),
                "severity": clean_text(row["severity"]),
                "summary": clean_text(row["summary"]),
                "evidence": clean_text(row["evidence"]),
                "detected_at": clean_text(
                    row["detected_at"]
                ),
            }
        )

    return json.dumps(records, ensure_ascii=False)


def run_investigation(
    engine: Engine,
    issue: pd.Series,
    issue_evidence: pd.DataFrame,
) -> dict:
    """Route each current issue type to detailed investigation logic."""

    issue_type = clean_text(issue["issue_type"])

    if issue_type == "Store Performance Risk":
        return investigate_store_performance(engine, issue)

    if issue_type == "Product Availability Risk":
        return investigate_product_availability(engine, issue)

    if issue_type == "Vendor Performance Risk":
        return investigate_vendor_performance(engine, issue)

    if issue_type == "Complaint Resolution Backlog":
        return investigate_complaint_backlog(engine, issue)

    if issue_type == "Product Complaint Risk":
        return investigate_product_complaint_risk(engine, issue)

    if issue_type == "Product Sales Performance Risk":
        return investigate_product_sales_performance(engine, issue)

    if issue_type == "Inventory Overstock Risk":
        return investigate_inventory_overstock(engine, issue)

    if issue_type == "Repeated Complaint Category Risk":
        return investigate_repeated_complaint_category(
            engine,
            issue,
        )

    return investigate_generic_issue(issue, issue_evidence)


def create_analysis_record(
    issue: pd.Series,
    issue_evidence: pd.DataFrame,
    investigation: dict,
) -> dict:
    """Create one standard root-cause output record."""

    evidence_types = unique_non_empty(
        issue_evidence["analysis_type"]
    )

    confidence_score = calculate_confidence_score(
        issue_evidence,
        clean_text(investigation["root_cause_category"]),
    )

    generated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    return {
        "analysis_id": f"RCA-{clean_text(issue['issue_id'])}",
        "executive_rank": safe_int(issue["executive_rank"]),
        "issue_id": clean_text(issue["issue_id"]),
        "title": clean_text(issue["title"]),
        "issue_type": clean_text(issue["issue_type"]),
        "business_area": clean_text(issue["business_area"]),
        "priority_level": clean_text(
            issue["priority_level"]
        ),
        "priority_score": optional_float(
            issue["priority_score"]
        ),
        "executive_score": optional_float(
            issue["executive_score"]
        ),
        "entity_type": clean_text(issue["entity_type"]),
        "entity_id": clean_text(issue["entity_id"]),
        "store_id": get_store_id(issue),
        "product_id": get_product_id(issue),
        "vendor_id": get_vendor_id(issue),
        "period_label": get_period_label(issue) or "",
        "root_cause_category": clean_text(
            investigation["root_cause_category"]
        ),
        "root_cause_summary": clean_text(
            investigation["root_cause_summary"]
        ),
        "root_cause_explanation": build_root_cause_explanation(
            issue,
            investigation,
        ),
        "contributing_factors": clean_text(
            investigation["contributing_factors"]
        ),
        "evidence_summary": clean_text(
            investigation["evidence_summary"]
        ),
        "investigation_focus": clean_text(
            investigation["investigation_focus"]
        ),
        "confidence_score": confidence_score,
        "evidence_count": len(issue_evidence),
        "evidence_types": ", ".join(evidence_types),
        "analysis_method": (
            "Rule-Based Database and Evidence Analysis"
        ),
        "analysis_status": "Generated",
        "review_status": "Pending Review",
        "generated_at": generated_at,
    }


def build_root_cause_outputs(
    engine: Engine,
    selected_issues: pd.DataFrame,
    selected_evidence: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict]]:
    """Generate report and database records for executive issues."""

    output_records = []
    database_records = []

    for _, issue in selected_issues.iterrows():
        issue_id = clean_text(issue["issue_id"])

        issue_evidence = selected_evidence[
            selected_evidence["issue_id"].eq(issue_id)
        ].copy()

        print(
            f"Analyzing {issue_id} "
            f"({clean_text(issue['issue_type'])})..."
        )

        try:
            investigation = run_investigation(
                engine,
                issue,
                issue_evidence,
            )

        except Exception as error:
            investigation = create_investigation_result(
                root_cause_category=(
                    "Technical Review Required"
                ),
                root_cause_summary=(
                    "The detailed investigation could not be "
                    "completed automatically."
                ),
                explanation_points=[
                    "A technical review is required before "
                    "confirming the root cause.",
                    f"Investigation error: {clean_text(error)}",
                ],
                evidence_summary=clean_text(
                    issue.get("evidence_summary")
                ),
                investigation_focus=(
                    "Review source data, database records, and "
                    "the rule logic for this issue."
                ),
            )

        analysis_record = create_analysis_record(
            issue,
            issue_evidence,
            investigation,
        )

        output_records.append(analysis_record)

        database_records.append(
            {
                "issue_id": analysis_record["issue_id"],
                "root_cause_category": analysis_record[
                    "root_cause_category"
                ],
                "root_cause_summary": analysis_record[
                    "root_cause_summary"
                ],
                "root_cause_explanation": analysis_record[
                    "root_cause_explanation"
                ],
                "confidence_score": analysis_record[
                    "confidence_score"
                ],
                "supporting_evidence": (
                    build_supporting_evidence_json(issue_evidence)
                ),
                "evidence_count": analysis_record[
                    "evidence_count"
                ],
            }
        )

    output_dataframe = pd.DataFrame(
        output_records,
        columns=OUTPUT_COLUMNS,
    )

    return (
        output_dataframe.sort_values(
            by="executive_rank"
        ).reset_index(drop=True),
        database_records,
    )


ROOT_CAUSE_UPSERT_SQL = text(
    """
    INSERT INTO root_cause_analyses (
        issue_id,
        root_cause_category,
        root_cause_summary,
        root_cause_explanation,
        confidence_score,
        supporting_evidence,
        evidence_count,
        analysis_status,
        review_status,
        generated_at,
        updated_at
    )
    VALUES (
        :issue_id,
        :root_cause_category,
        :root_cause_summary,
        :root_cause_explanation,
        :confidence_score,
        CAST(:supporting_evidence AS JSONB),
        :evidence_count,
        'Generated',
        'Pending Review',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (issue_id)
    DO UPDATE SET
        root_cause_category = EXCLUDED.root_cause_category,
        root_cause_summary = EXCLUDED.root_cause_summary,
        root_cause_explanation = EXCLUDED.root_cause_explanation,
        confidence_score = EXCLUDED.confidence_score,
        supporting_evidence = EXCLUDED.supporting_evidence,
        evidence_count = EXCLUDED.evidence_count,
        analysis_status = 'Generated',
        analysis_version = (
            root_cause_analyses.analysis_version + 1
        ),
        generated_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE root_cause_analyses.review_status
        IN ('Pending Review', 'Rejected');
    """
)

ISSUE_ROOT_CAUSE_STATUS_SQL = text(
    """
    UPDATE issues
    SET
        root_cause_status = CASE
            WHEN root_cause_status IN ('Accepted', 'Edited')
            THEN root_cause_status
            ELSE 'Generated'
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE issue_id = :issue_id;
    """
)


def save_root_causes_to_database(
    engine: Engine,
    database_records: list[dict],
) -> None:
    """Upsert root-cause results and preserve reviewed records."""

    if not database_records:
        print(
            "No root-cause records are available for database storage."
        )
        return

    with engine.begin() as connection:
        connection.execute(
            ROOT_CAUSE_UPSERT_SQL,
            database_records,
        )

        connection.execute(
            ISSUE_ROOT_CAUSE_STATUS_SQL,
            [
                {"issue_id": record["issue_id"]}
                for record in database_records
            ],
        )


def create_markdown_report(
    analyses: pd.DataFrame,
) -> str:
    """Create a readable Markdown root-cause report."""

    generated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    lines = [
        "# Root Cause Analysis Report",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        (
            "This report analyzes Executive Priority List issues "
            "using linked issue evidence and live PostgreSQL "
            "business data. Each result is an evidence-based "
            "likely-cause assessment and requires human review "
            "before action is approved."
        ),
        "",
        "## Analysis Scope",
        "",
        f"- Executive Issues Analyzed: {len(analyses)}",
        (
            "- Analysis Method: Rule-Based Database and Evidence "
            "Analysis"
        ),
        "- Review Status: Pending Review",
        "",
    ]

    if analyses.empty:
        lines.extend(
            [
                "No executive issues were available for root-cause "
                "analysis.",
                "",
            ]
        )

        return "\n".join(lines)

    lines.extend(
        [
            "## Root Cause Overview",
            "",
            (
                "| Rank | Issue | Root Cause Category | "
                "Confidence | Evidence Count |"
            ),
            "|---:|---|---|---:|---:|",
        ]
    )

    for row in analyses.itertuples(index=False):
        lines.append(
            f"| {safe_int(row.executive_rank)} | "
            f"{clean_text(row.title).replace('|', '/')} | "
            f"{clean_text(row.root_cause_category).replace('|', '/')} | "
            f"{safe_float(row.confidence_score):.2f}% | "
            f"{safe_int(row.evidence_count)} |"
        )

    lines.extend(
        [
            "",
            "## Detailed Root Cause Analyses",
            "",
        ]
    )

    for row in analyses.itertuples(index=False):
        lines.extend(
            [
                (
                    f"### {safe_int(row.executive_rank)}. "
                    f"{clean_text(row.title)}"
                ),
                "",
                f"**Issue ID:** {clean_text(row.issue_id)}",
                "",
                (
                    f"**Executive Score:** "
                    f"{safe_float(row.executive_score):.2f}"
                ),
                "",
                (
                    f"**Priority:** {clean_text(row.priority_level)} "
                    f"({safe_float(row.priority_score):.2f})"
                ),
                "",
                (
                    f"**Root Cause Category:** "
                    f"{clean_text(row.root_cause_category)}"
                ),
                "",
                (
                    f"**Confidence Score:** "
                    f"{safe_float(row.confidence_score):.2f}%"
                ),
                "",
                (
                    f"**Supporting Evidence Types:** "
                    f"{clean_text(row.evidence_types)}"
                ),
                "",
                (
                    f"**Root Cause Summary:** "
                    f"{clean_text(row.root_cause_summary)}"
                ),
                "",
                (
                    f"**Contributing Factors:** "
                    f"{clean_text(row.contributing_factors)}"
                ),
                "",
                (
                    f"**Evidence Summary:** "
                    f"{clean_text(row.evidence_summary)}"
                ),
                "",
                (
                    f"**Investigation Focus:** "
                    f"{clean_text(row.investigation_focus)}"
                ),
                "",
                "**Review Status:** Pending Review",
                "",
            ]
        )

    return "\n".join(lines)


def print_root_cause_preview(
    analyses: pd.DataFrame,
) -> None:
    """Print a compact terminal preview."""

    print("\nRoot Cause Analysis Preview:")

    if analyses.empty:
        print("No root-cause analyses were created.")
        return

    preview_columns = [
        "executive_rank",
        "confidence_score",
        "root_cause_category",
        "title",
    ]

    print(
        analyses[preview_columns].to_string(index=False)
    )


def main() -> None:
    """Run root-cause analysis for current executive priorities."""

    parser = argparse.ArgumentParser(
        description=(
            "Generate detailed root-cause analyses for current "
            "executive priorities."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum executive issues to analyze. Default: 10.",
    )

    arguments = parser.parse_args()

    if arguments.limit <= 0:
        raise ValueError("--limit must be greater than zero.")

    REPORTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Loading executive priority reference...")

    priority_reference = load_executive_priority_reference(
        arguments.limit
    )

    print(
        "Executive issues selected for analysis: "
        f"{len(priority_reference)}"
    )

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        print("Loading selected issues...")

        selected_issues = load_selected_issues(
            engine,
            priority_reference,
        )

        if selected_issues.empty:
            raise ValueError(
                "No active PostgreSQL issues matched the executive "
                "priority list."
            )

        print("Loading supporting issue evidence...")

        selected_evidence = load_selected_evidence(
            engine,
            selected_issues["issue_id"].tolist(),
        )

        print("Generating detailed root-cause analyses...")

        analyses_dataframe, database_records = (
            build_root_cause_outputs(
                engine,
                selected_issues,
                selected_evidence,
            )
        )

        csv_output_path = (
            REPORTS_DIRECTORY / "root_cause_analysis.csv"
        )

        markdown_output_path = (
            REPORTS_DIRECTORY / "root_cause_analysis_report.md"
        )

        analyses_dataframe.to_csv(
            csv_output_path,
            index=False,
        )

        markdown_output_path.write_text(
            create_markdown_report(analyses_dataframe),
            encoding="utf-8",
        )

        print("Saving root-cause analyses to PostgreSQL...")

        save_root_causes_to_database(
            engine,
            database_records,
        )

        print("\nRoot Cause Analysis completed successfully.")
        print(
            f"Root-cause analyses generated: "
            f"{len(analyses_dataframe)}"
        )

        print(
            "PostgreSQL table updated: root_cause_analyses"
        )

        print_root_cause_preview(analyses_dataframe)

        print(f"\nCSV report saved at: {csv_output_path}")
        print(
            f"Markdown report saved at: "
            f"{markdown_output_path}"
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
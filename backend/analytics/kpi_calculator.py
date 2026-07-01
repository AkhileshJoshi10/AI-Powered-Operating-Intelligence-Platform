from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from backend.database import get_database_engine, read_query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"


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


def format_currency(value: object) -> str:
    """Format a value as Indian currency."""

    return f"₹{safe_float(value):,.2f}"


def format_percent(value: object) -> str:
    """Format a value as a percentage."""

    return f"{safe_float(value):.2f}%"


def format_count(value: object) -> str:
    """Format a whole-number KPI."""

    return f"{safe_int(value):,}"


def create_kpi_record(
    kpi_key: str,
    kpi_name: str,
    value: float,
    display_value: str,
    unit: str,
    reference_period: str,
    description: str,
) -> dict:
    """Create one standardized KPI record."""

    return {
        "kpi_key": kpi_key,
        "kpi_name": kpi_name,
        "value": round(value, 2),
        "display_value": display_value,
        "unit": unit,
        "reference_period": reference_period,
        "description": description,
        "calculated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_sales_summary(engine: Engine) -> pd.Series:
    """Return overall sales, transaction, quantity, and AOV metrics."""

    query = """
    SELECT
        COALESCE(SUM(total_sales), 0) AS total_sales,
        COUNT(*) AS transaction_count,
        COALESCE(SUM(quantity_sold), 0) AS total_quantity_sold,
        COALESCE(
            SUM(total_sales) / NULLIF(COUNT(*), 0),
            0
        ) AS average_order_value
    FROM sales;
    """

    sales_summary = read_query(engine, query)

    return sales_summary.iloc[0]


def get_finance_summary(engine: Engine) -> pd.Series:
    """Return total revenue and operating-profit metrics."""

    query = """
    SELECT
        COALESCE(SUM(total_revenue), 0) AS total_revenue,
        COALESCE(SUM(operating_profit), 0) AS total_operating_profit
    FROM finance;
    """

    finance_summary = read_query(engine, query)

    return finance_summary.iloc[0]


def get_latest_sales_growth(engine: Engine) -> pd.Series:
    """Return the latest month-on-month overall sales growth."""

    query = """
    WITH monthly_sales AS (
        SELECT
            TO_CHAR(date, 'YYYY-MM') AS month,
            SUM(total_sales) AS monthly_sales
        FROM sales
        GROUP BY TO_CHAR(date, 'YYYY-MM')
    ),
    sales_history AS (
        SELECT
            month,
            monthly_sales,
            LAG(month) OVER (
                ORDER BY month
            ) AS previous_month,
            LAG(monthly_sales) OVER (
                ORDER BY month
            ) AS previous_month_sales
        FROM monthly_sales
    )
    SELECT
        month,
        monthly_sales,
        previous_month,
        previous_month_sales
    FROM sales_history
    ORDER BY month DESC
    LIMIT 1;
    """

    sales_growth = read_query(engine, query)

    return sales_growth.iloc[0]


def get_latest_store_target_achievement(engine: Engine) -> pd.DataFrame:
    """Return the latest target-achievement record for every store."""

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
        store_id,
        store_name,
        month,
        monthly_sales_target,
        total_revenue,
        operating_profit,
        target_achievement_percent,
        risk_status
    FROM latest_finance
    ORDER BY
        target_achievement_percent ASC,
        store_id;
    """

    return read_query(engine, query)


def get_inventory_summary(engine: Engine) -> pd.Series:
    """Return low-stock and overstock counts."""

    query = """
    SELECT
        COUNT(*) FILTER (
            WHERE stock_status = 'Low Stock'
        ) AS low_stock_count,
        COUNT(*) FILTER (
            WHERE stock_status = 'Overstock'
        ) AS overstock_count
    FROM inventory;
    """

    inventory_summary = read_query(engine, query)

    return inventory_summary.iloc[0]


def get_complaint_summary(engine: Engine) -> pd.Series:
    """Return high-severity and unresolved complaint counts."""

    query = """
    SELECT
        COUNT(*) FILTER (
            WHERE severity = 'High'
        ) AS high_severity_complaint_count,
        COUNT(*) FILTER (
            WHERE status IN ('Open', 'In Progress')
        ) AS open_complaint_count
    FROM complaints;
    """

    complaint_summary = read_query(engine, query)

    return complaint_summary.iloc[0]


def get_vendor_delivery_summary(engine: Engine) -> pd.Series:
    """Return delayed-delivery count and on-time delivery rate."""

    query = """
    SELECT
        COUNT(*) FILTER (
            WHERE delay_days > 0
        ) AS delayed_delivery_count,
        COALESCE(
            (
                COUNT(*) FILTER (
                    WHERE delay_days <= 0
                )::NUMERIC
                / NULLIF(COUNT(*), 0)
            ) * 100,
            0
        ) AS on_time_delivery_rate
    FROM vendor_deliveries;
    """

    vendor_summary = read_query(engine, query)

    return vendor_summary.iloc[0]


def build_kpi_summary(
    engine: Engine,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate all required KPIs and latest store target achievement."""

    sales_summary = get_sales_summary(engine)
    finance_summary = get_finance_summary(engine)
    sales_growth_data = get_latest_sales_growth(engine)
    store_target_data = get_latest_store_target_achievement(engine)
    inventory_summary = get_inventory_summary(engine)
    complaint_summary = get_complaint_summary(engine)
    vendor_summary = get_vendor_delivery_summary(engine)

    latest_month = str(sales_growth_data["month"])
    previous_month = str(sales_growth_data["previous_month"])

    current_month_sales = safe_float(sales_growth_data["monthly_sales"])
    previous_month_sales = safe_float(
        sales_growth_data["previous_month_sales"]
    )

    sales_growth_percent = (
        (
            (current_month_sales - previous_month_sales)
            / previous_month_sales
        )
        * 100
        if previous_month_sales > 0
        else 0
    )

    total_latest_target = safe_float(
        store_target_data["monthly_sales_target"].sum()
    )
    total_latest_revenue = safe_float(
        store_target_data["total_revenue"].sum()
    )

    overall_target_achievement = (
        (total_latest_revenue / total_latest_target) * 100
        if total_latest_target > 0
        else 0
    )

    kpi_records = [
        create_kpi_record(
            kpi_key="total_sales",
            kpi_name="Total Sales",
            value=safe_float(sales_summary["total_sales"]),
            display_value=format_currency(sales_summary["total_sales"]),
            unit="INR",
            reference_period="January 2026 to June 2026",
            description=(
                "Total value of all completed sales transactions."
            ),
        ),
        create_kpi_record(
            kpi_key="total_revenue",
            kpi_name="Total Revenue",
            value=safe_float(finance_summary["total_revenue"]),
            display_value=format_currency(finance_summary["total_revenue"]),
            unit="INR",
            reference_period="January 2026 to June 2026",
            description=(
                "Total revenue recorded in the finance reporting table."
            ),
        ),
        create_kpi_record(
            kpi_key="sales_growth",
            kpi_name="Sales Growth",
            value=sales_growth_percent,
            display_value=format_percent(sales_growth_percent),
            unit="Percent",
            reference_period=f"{latest_month} compared with {previous_month}",
            description=(
                "Month-on-month change in total sales for the latest month."
            ),
        ),
        create_kpi_record(
            kpi_key="store_target_achievement",
            kpi_name="Store Target Achievement",
            value=overall_target_achievement,
            display_value=format_percent(overall_target_achievement),
            unit="Percent",
            reference_period=(
                f"Latest finance month: "
                f"{store_target_data.iloc[0]['month']}"
            ),
            description=(
                "Weighted target achievement across all stores in the "
                "latest available finance month."
            ),
        ),
        create_kpi_record(
            kpi_key="average_order_value",
            kpi_name="Average Order Value",
            value=safe_float(sales_summary["average_order_value"]),
            display_value=format_currency(
                sales_summary["average_order_value"]
            ),
            unit="INR",
            reference_period="January 2026 to June 2026",
            description=(
                "Average sales value per transaction."
            ),
        ),
        create_kpi_record(
            kpi_key="total_operating_profit",
            kpi_name="Total Operating Profit",
            value=safe_float(finance_summary["total_operating_profit"]),
            display_value=format_currency(
                finance_summary["total_operating_profit"]
            ),
            unit="INR",
            reference_period="January 2026 to June 2026",
            description=(
                "Total operating profit after operating expenses."
            ),
        ),
        create_kpi_record(
            kpi_key="low_stock_count",
            kpi_name="Low-Stock Count",
            value=safe_float(inventory_summary["low_stock_count"]),
            display_value=format_count(
                inventory_summary["low_stock_count"]
            ),
            unit="Records",
            reference_period="Latest inventory snapshot",
            description=(
                "Number of inventory records marked as Low Stock."
            ),
        ),
        create_kpi_record(
            kpi_key="overstock_count",
            kpi_name="Overstock Count",
            value=safe_float(inventory_summary["overstock_count"]),
            display_value=format_count(
                inventory_summary["overstock_count"]
            ),
            unit="Records",
            reference_period="Latest inventory snapshot",
            description=(
                "Number of inventory records marked as Overstock."
            ),
        ),
        create_kpi_record(
            kpi_key="high_severity_complaint_count",
            kpi_name="High-Severity Complaint Count",
            value=safe_float(
                complaint_summary["high_severity_complaint_count"]
            ),
            display_value=format_count(
                complaint_summary["high_severity_complaint_count"]
            ),
            unit="Complaints",
            reference_period="January 2026 to June 2026",
            description=(
                "Total complaints classified as High severity."
            ),
        ),
        create_kpi_record(
            kpi_key="open_complaint_count",
            kpi_name="Open Complaint Count",
            value=safe_float(complaint_summary["open_complaint_count"]),
            display_value=format_count(
                complaint_summary["open_complaint_count"]
            ),
            unit="Complaints",
            reference_period="January 2026 to June 2026",
            description=(
                "Complaints that remain Open or In Progress."
            ),
        ),
        create_kpi_record(
            kpi_key="vendor_delay_count",
            kpi_name="Vendor Delay Count",
            value=safe_float(vendor_summary["delayed_delivery_count"]),
            display_value=format_count(
                vendor_summary["delayed_delivery_count"]
            ),
            unit="Deliveries",
            reference_period="January 2026 to June 2026",
            description=(
                "Number of vendor deliveries received after the scheduled "
                "delivery date."
            ),
        ),
        create_kpi_record(
            kpi_key="vendor_on_time_delivery_rate",
            kpi_name="Vendor On-Time Delivery Rate",
            value=safe_float(vendor_summary["on_time_delivery_rate"]),
            display_value=format_percent(
                vendor_summary["on_time_delivery_rate"]
            ),
            unit="Percent",
            reference_period="January 2026 to June 2026",
            description=(
                "Percentage of deliveries received on or before the "
                "scheduled delivery date."
            ),
        ),
    ]

    kpi_dataframe = pd.DataFrame(kpi_records)

    return kpi_dataframe, store_target_data


def create_markdown_report(
    kpis: pd.DataFrame,
    store_target_data: pd.DataFrame,
) -> str:
    """Create a readable Markdown KPI report."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# KPI Summary Report",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        "This report contains the core business KPIs calculated directly "
        "from the validated PostgreSQL database.",
        "",
        "## Overall KPI Summary",
        "",
        "| KPI | Value | Reference Period |",
        "|---|---:|---|",
    ]

    for row in kpis.itertuples(index=False):
        lines.append(
            f"| {row.kpi_name} | {row.display_value} | "
            f"{row.reference_period} |"
        )

    lines.extend(
        [
            "",
            "## Latest Store Target Achievement",
            "",
            "| Store ID | Store Name | Month | Target | Revenue | "
            "Achievement | Operating Profit | Risk Status |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )

    for row in store_target_data.itertuples(index=False):
        lines.append(
            f"| {row.store_id} | {row.store_name} | {row.month} | "
            f"{format_currency(row.monthly_sales_target)} | "
            f"{format_currency(row.total_revenue)} | "
            f"{format_percent(row.target_achievement_percent)} | "
            f"{format_currency(row.operating_profit)} | "
            f"{row.risk_status} |"
        )

    lines.extend(
        [
            "",
            "## KPI Definitions",
            "",
        ]
    )

    for row in kpis.itertuples(index=False):
        lines.append(f"- **{row.kpi_name}:** {row.description}")

    return "\n".join(lines)


def main() -> None:
    """Calculate KPIs and save CSV and Markdown outputs."""

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("Connecting to PostgreSQL database...")
    engine = get_database_engine()

    try:
        print("Calculating business KPIs...")

        kpi_dataframe, store_target_data = build_kpi_summary(engine)

        csv_output_path = REPORTS_DIRECTORY / "kpi_summary.csv"
        markdown_output_path = REPORTS_DIRECTORY / "kpi_summary_report.md"

        kpi_dataframe.to_csv(csv_output_path, index=False)

        markdown_report = create_markdown_report(
            kpi_dataframe,
            store_target_data,
        )

        markdown_output_path.write_text(
            markdown_report,
            encoding="utf-8",
        )

        print("\nKPI calculation completed successfully.")
        print("\nCore KPIs:")

        for row in kpi_dataframe.itertuples(index=False):
            print(f"- {row.kpi_name}: {row.display_value}")

        print(f"\nCSV report saved at: {csv_output_path}")
        print(f"Markdown report saved at: {markdown_output_path}")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
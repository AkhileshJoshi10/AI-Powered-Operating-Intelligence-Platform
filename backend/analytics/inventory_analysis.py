from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from backend.analytics.thresholds import (
    INVENTORY_COMPLAINT_THRESHOLD,
    INVENTORY_HIGH_SEVERITY_COMPLAINT_THRESHOLD,
    NEAR_EXPIRY_DAYS,
    SEVERE_OVERSTOCK_RATIO,
    SEVERE_STOCK_RATIO,
    STOCKOUT_RISK_RATIO,
    URGENT_EXPIRY_DAYS,
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
    "store_id",
    "store_name",
    "product_id",
    "product_name",
    "vendor_id",
    "vendor_name",
    "inventory_date",
    "expiry_date",
    "days_to_expiry",
    "current_stock",
    "reorder_level",
    "stock_ratio",
    "stock_status",
    "reorder_required",
    "related_complaints",
    "high_severity_complaints",
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


def create_finding(
    *,
    finding_id: str,
    analysis_type: str,
    severity: str,
    entity_type: str,
    entity_id: str,
    store_id: str,
    store_name: str,
    product_id: str,
    product_name: str,
    vendor_id: str,
    vendor_name: str,
    inventory_date: object,
    expiry_date: object,
    days_to_expiry: object,
    current_stock: float,
    reorder_level: float,
    stock_ratio: float,
    stock_status: str,
    reorder_required: str,
    related_complaints: int,
    high_severity_complaints: int,
    summary: str,
    evidence: str,
) -> dict:
    """Create one standardized inventory-analysis finding."""

    return {
        "finding_id": clean_text(finding_id),
        "analysis_type": clean_text(analysis_type),
        "business_area": "Operations",
        "severity": clean_text(severity),
        "entity_type": clean_text(entity_type),
        "entity_id": clean_text(entity_id),
        "store_id": clean_text(store_id),
        "store_name": clean_text(store_name),
        "product_id": clean_text(product_id),
        "product_name": clean_text(product_name),
        "vendor_id": clean_text(vendor_id),
        "vendor_name": clean_text(vendor_name),
        "inventory_date": clean_text(inventory_date),
        "expiry_date": clean_text(expiry_date),
        "days_to_expiry": optional_int(days_to_expiry),
        "current_stock": optional_float(current_stock),
        "reorder_level": optional_float(reorder_level),
        "stock_ratio": optional_float(stock_ratio),
        "stock_status": clean_text(stock_status),
        "reorder_required": clean_text(reorder_required),
        "related_complaints": safe_int(related_complaints),
        "high_severity_complaints": safe_int(
            high_severity_complaints
        ),
        "summary": clean_text(summary),
        "evidence": clean_text(evidence),
        "status": "Open",
        "detected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def get_inventory_snapshot(engine: Engine) -> pd.DataFrame:
    """Read inventory records with related product, vendor, and complaint data."""

    query = """
    SELECT
        i.inventory_id,
        i.date AS inventory_date,
        i.store_id,
        i.store_name,
        i.product_id,
        i.product_name,
        i.vendor_id,
        v.vendor_name,
        i.current_stock,
        i.reorder_level,
        i.stock_status,
        i.reorder_required,
        p.is_perishable,
        i.expiry_date,
        i.expiry_date - i.date AS days_to_expiry,
        COUNT(c.complaint_id) AS related_complaints,
        COUNT(*) FILTER (
            WHERE c.severity = 'High'
        ) AS high_severity_complaints
    FROM inventory AS i
    JOIN products AS p
        ON i.product_id = p.product_id
    LEFT JOIN vendors AS v
        ON i.vendor_id = v.vendor_id
    LEFT JOIN complaints AS c
        ON i.store_id = c.store_id
        AND i.product_id = c.product_id
    GROUP BY
        i.inventory_id,
        i.date,
        i.store_id,
        i.store_name,
        i.product_id,
        i.product_name,
        i.vendor_id,
        v.vendor_name,
        i.current_stock,
        i.reorder_level,
        i.stock_status,
        i.reorder_required,
        p.is_perishable,
        i.expiry_date
    ORDER BY
        i.store_id,
        i.product_id;
    """

    snapshot = read_query(engine, query)

    snapshot["stock_ratio"] = (
        snapshot["current_stock"]
        / snapshot["reorder_level"].replace(0, pd.NA)
    )

    return snapshot


def create_inventory_finding(
    row: pd.Series,
    analysis_type: str,
    severity: str,
    summary: str,
    evidence: str,
) -> dict:
    """Create an inventory finding from one inventory record."""

    return create_finding(
        finding_id=(
            f"{analysis_type.upper().replace(' ', '-')}-"
            f"{row['store_id']}-{row['product_id']}-"
            f"{row['inventory_date']}"
        ),
        analysis_type=analysis_type,
        severity=severity,
        entity_type="Store Product",
        entity_id=f"{row['store_id']}-{row['product_id']}",
        store_id=row["store_id"],
        store_name=row["store_name"],
        product_id=row["product_id"],
        product_name=row["product_name"],
        vendor_id=row["vendor_id"],
        vendor_name=row["vendor_name"],
        inventory_date=row["inventory_date"],
        expiry_date=row["expiry_date"],
        days_to_expiry=row["days_to_expiry"],
        current_stock=safe_float(row["current_stock"]),
        reorder_level=safe_float(row["reorder_level"]),
        stock_ratio=safe_float(row["stock_ratio"]),
        stock_status=row["stock_status"],
        reorder_required=row["reorder_required"],
        related_complaints=safe_int(row["related_complaints"]),
        high_severity_complaints=safe_int(
            row["high_severity_complaints"]
        ),
        summary=summary,
        evidence=evidence,
    )


def detect_low_stock(snapshot: pd.DataFrame) -> list[dict]:
    """Detect all records marked as Low Stock."""

    low_stock_data = snapshot[
        snapshot["stock_status"].eq("Low Stock")
    ].copy()

    findings = []

    for _, row in low_stock_data.iterrows():
        stock_ratio = safe_float(row["stock_ratio"])

        severity = "High" if stock_ratio <= SEVERE_STOCK_RATIO else "Medium"

        summary = (
            f"{row['product_name']} is marked as Low Stock at "
            f"{row['store_name']}."
        )

        evidence = (
            f"Current Stock: {safe_float(row['current_stock']):.0f}; "
            f"Reorder Level: {safe_float(row['reorder_level']):.0f}; "
            f"Stock Ratio: {format_percent(stock_ratio * 100)}; "
            f"Reorder Required: {clean_text(row['reorder_required'])}; "
            f"Related Complaints: {safe_int(row['related_complaints'])}"
        )

        findings.append(
            create_inventory_finding(
                row=row,
                analysis_type="Low Stock",
                severity=severity,
                summary=summary,
                evidence=evidence,
            )
        )

    return findings


def detect_reorder_soon(snapshot: pd.DataFrame) -> list[dict]:
    """Detect records marked as Reorder Soon."""

    reorder_soon_data = snapshot[
        snapshot["stock_status"].eq("Reorder Soon")
    ].copy()

    findings = []

    for _, row in reorder_soon_data.iterrows():
        stock_ratio = safe_float(row["stock_ratio"])

        summary = (
            f"{row['product_name']} is approaching its reorder level at "
            f"{row['store_name']}."
        )

        evidence = (
            f"Current Stock: {safe_float(row['current_stock']):.0f}; "
            f"Reorder Level: {safe_float(row['reorder_level']):.0f}; "
            f"Stock Ratio: {format_percent(stock_ratio * 100)}; "
            f"Vendor: {clean_text(row['vendor_name'])}"
        )

        findings.append(
            create_inventory_finding(
                row=row,
                analysis_type="Reorder Soon",
                severity="Low",
                summary=summary,
                evidence=evidence,
            )
        )

    return findings


def detect_overstock(snapshot: pd.DataFrame) -> list[dict]:
    """Detect records marked as Overstock."""

    overstock_data = snapshot[
        snapshot["stock_status"].eq("Overstock")
    ].copy()

    findings = []

    for _, row in overstock_data.iterrows():
        stock_ratio = safe_float(row["stock_ratio"])

        severity = (
            "Medium"
            if stock_ratio >= SEVERE_OVERSTOCK_RATIO
            else "Low"
        )

        summary = (
            f"{row['product_name']} has excess stock at "
            f"{row['store_name']}."
        )

        evidence = (
            f"Current Stock: {safe_float(row['current_stock']):.0f}; "
            f"Reorder Level: {safe_float(row['reorder_level']):.0f}; "
            f"Stock Ratio: {format_percent(stock_ratio * 100)}; "
            f"Stock Status: {clean_text(row['stock_status'])}"
        )

        findings.append(
            create_inventory_finding(
                row=row,
                analysis_type="Overstock",
                severity=severity,
                summary=summary,
                evidence=evidence,
            )
        )

    return findings


def detect_stockout_risk(snapshot: pd.DataFrame) -> list[dict]:
    """Detect low stock that creates a meaningful stockout risk."""

    stockout_data = snapshot[
        snapshot["stock_status"].eq("Low Stock")
        & (
            (snapshot["stock_ratio"] <= STOCKOUT_RISK_RATIO)
            | (
                snapshot["related_complaints"]
                >= INVENTORY_COMPLAINT_THRESHOLD
            )
        )
    ].copy()

    findings = []

    for _, row in stockout_data.iterrows():
        stock_ratio = safe_float(row["stock_ratio"])
        related_complaints = safe_int(row["related_complaints"])
        high_severity_complaints = safe_int(
            row["high_severity_complaints"]
        )

        severity = "Medium"

        if (
            stock_ratio <= SEVERE_STOCK_RATIO
            or (
                related_complaints >= INVENTORY_COMPLAINT_THRESHOLD
                and high_severity_complaints
                >= INVENTORY_HIGH_SEVERITY_COMPLAINT_THRESHOLD
            )
        ):
            severity = "High"

        summary = (
            f"{row['product_name']} has a stockout risk at "
            f"{row['store_name']} because stock is critically low and "
            f"may affect customer availability."
        )

        evidence = (
            f"Current Stock: {safe_float(row['current_stock']):.0f}; "
            f"Reorder Level: {safe_float(row['reorder_level']):.0f}; "
            f"Stock Ratio: {format_percent(stock_ratio * 100)}; "
            f"Related Complaints: {related_complaints}; "
            f"High-Severity Complaints: {high_severity_complaints}; "
            f"Vendor: {clean_text(row['vendor_name'])}"
        )

        findings.append(
            create_inventory_finding(
                row=row,
                analysis_type="Stockout Risk",
                severity=severity,
                summary=summary,
                evidence=evidence,
            )
        )

    return findings


def detect_near_expiry(snapshot: pd.DataFrame) -> list[dict]:
    """Detect perishable stock that will expire within the warning window."""

    perishable_rows = snapshot[
        snapshot["is_perishable"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("yes")
    ].copy()

    near_expiry_data = perishable_rows[
        perishable_rows["expiry_date"].notna()
        & (perishable_rows["days_to_expiry"] >= 0)
        & (perishable_rows["days_to_expiry"] <= NEAR_EXPIRY_DAYS)
        & (perishable_rows["current_stock"] > 0)
    ].copy()

    findings = []

    for _, row in near_expiry_data.iterrows():
        days_to_expiry = safe_int(row["days_to_expiry"])

        severity = (
            "High"
            if days_to_expiry <= URGENT_EXPIRY_DAYS
            else "Medium"
        )

        summary = (
            f"{row['product_name']} has stock nearing expiry at "
            f"{row['store_name']}."
        )

        evidence = (
            f"Inventory Date: {clean_text(row['inventory_date'])}; "
            f"Expiry Date: {clean_text(row['expiry_date'])}; "
            f"Days to Expiry: {days_to_expiry}; "
            f"Current Stock: {safe_float(row['current_stock']):.0f}; "
            f"Perishable: Yes"
        )

        findings.append(
            create_inventory_finding(
                row=row,
                analysis_type="Near Expiry Stock",
                severity=severity,
                summary=summary,
                evidence=evidence,
            )
        )

    return findings


def detect_expired_inventory(snapshot: pd.DataFrame) -> list[dict]:
    """Detect perishable inventory that was already expired on snapshot date."""

    perishable_rows = snapshot[
        snapshot["is_perishable"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("yes")
    ].copy()

    expired_data = perishable_rows[
        perishable_rows["expiry_date"].notna()
        & (perishable_rows["days_to_expiry"] < 0)
        & (perishable_rows["current_stock"] > 0)
    ].copy()

    findings = []

    for _, row in expired_data.iterrows():
        days_expired = abs(safe_int(row["days_to_expiry"]))

        summary = (
            f"{row['product_name']} has expired inventory at "
            f"{row['store_name']}."
        )

        evidence = (
            f"Inventory Date: {clean_text(row['inventory_date'])}; "
            f"Expiry Date: {clean_text(row['expiry_date'])}; "
            f"Days Expired: {days_expired}; "
            f"Current Stock: {safe_float(row['current_stock']):.0f}; "
            f"Perishable: Yes"
        )

        findings.append(
            create_inventory_finding(
                row=row,
                analysis_type="Expired Inventory",
                severity="High",
                summary=summary,
                evidence=evidence,
            )
        )

    return findings


def run_inventory_analysis(engine: Engine) -> pd.DataFrame:
    """Run all Day 11 inventory-analysis rules."""

    print("Reading inventory snapshot...")
    snapshot = get_inventory_snapshot(engine)

    findings = []

    print("Analyzing low stock...")
    findings.extend(detect_low_stock(snapshot))

    print("Analyzing reorder-soon products...")
    findings.extend(detect_reorder_soon(snapshot))

    print("Analyzing overstock...")
    findings.extend(detect_overstock(snapshot))

    print("Analyzing stockout risk...")
    findings.extend(detect_stockout_risk(snapshot))

    print("Analyzing near-expiry stock...")
    findings.extend(detect_near_expiry(snapshot))

    print("Analyzing expired inventory...")
    findings.extend(detect_expired_inventory(snapshot))

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
            "stock_ratio",
            "days_to_expiry",
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
    """Create a readable Markdown inventory-analysis report."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Inventory Analysis Report",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        "This report contains inventory findings calculated from validated "
        "PostgreSQL inventory, product, vendor, and complaint data.",
        "",
        "## Detection Rules",
        "",
        "- Low Stock: inventory records marked as `Low Stock`.",
        "- Reorder Soon: inventory records marked as `Reorder Soon`.",
        "- Overstock: inventory records marked as `Overstock`.",
        f"- Stockout Risk: stock at or below "
        f"{STOCKOUT_RISK_RATIO * 100:.0f}% of reorder level, or significant "
        "related complaint volume.",
        f"- Near Expiry: perishable stock expiring within "
        f"{NEAR_EXPIRY_DAYS} days from the inventory snapshot date.",
        "- Expired Inventory: perishable stock already expired on the "
        "inventory snapshot date.",
        "",
    ]

    if findings.empty:
        lines.extend(
            [
                "No inventory findings met the configured rules.",
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
            "## Inventory Findings",
            "",
            "| Severity | Analysis Type | Store | Product | Stock Ratio | "
            "Expiry Status |",
            "|---|---|---|---|---:|---|",
        ]
    )

    for row in findings.itertuples(index=False):
        expiry_status = "Not applicable"

        if pd.notna(row.days_to_expiry):
            expiry_status = f"{int(row.days_to_expiry)} days"

        stock_ratio = (
            format_percent(row.stock_ratio * 100)
            if pd.notna(row.stock_ratio)
            else "Not available"
        )

        lines.append(
            f"| {row.severity} | {row.analysis_type} | "
            f"{row.store_name} | {row.product_name} | "
            f"{stock_ratio} | {expiry_status} |"
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
                f"**Store:** {row.store_name} ({row.store_id})",
                "",
                f"**Product:** {row.product_name} ({row.product_id})",
                "",
                f"**Summary:** {row.summary}",
                "",
                f"**Evidence:** {row.evidence}",
                "",
            ]
        )

    return "\n".join(lines)


def print_primary_scenario_check(findings: pd.DataFrame) -> None:
    """Print the expected S003-P017 stockout scenario result."""

    scenario_finding = findings[
        (findings["analysis_type"] == "Stockout Risk")
        & (findings["store_id"] == "S003")
        & (findings["product_id"] == "P017")
    ]

    print("\nPrimary Scenario Check:")

    if scenario_finding.empty:
        print("- S003 P017 stockout risk detected: No")
        return

    stock_ratio = safe_float(scenario_finding.iloc[0]["stock_ratio"])

    print(
        "- S003 P017 stockout risk detected: Yes "
        f"({stock_ratio * 100:.2f}% of reorder level)"
    )


def main() -> None:
    """Run Day 11 inventory analytics and save output files."""

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        findings_dataframe = run_inventory_analysis(engine)

        csv_output_path = REPORTS_DIRECTORY / "inventory_analysis.csv"
        markdown_output_path = (
            REPORTS_DIRECTORY / "inventory_analysis_report.md"
        )

        findings_dataframe.to_csv(csv_output_path, index=False)

        markdown_report = create_markdown_report(findings_dataframe)

        markdown_output_path.write_text(
            markdown_report,
            encoding="utf-8",
        )

        print("\nInventory analysis completed successfully.")
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
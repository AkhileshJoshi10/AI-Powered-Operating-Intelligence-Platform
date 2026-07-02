from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.analytics.thresholds import (
    PRIORITY_ADDITIONAL_HIGH_FINDING_BONUS,
    PRIORITY_CROSS_AREA_BONUS,
    PRIORITY_FINDING_VOLUME_BONUS,
    PRIORITY_HIGH_SEVERITY_POINTS,
    PRIORITY_HIGH_THRESHOLD,
    PRIORITY_LOW_SEVERITY_POINTS,
    PRIORITY_MAX_ADDITIONAL_HIGH_BONUS,
    PRIORITY_MAX_CROSS_AREA_BONUS,
    PRIORITY_MAX_FINDING_VOLUME_BONUS,
    PRIORITY_MEDIUM_SEVERITY_POINTS,
    PRIORITY_MEDIUM_THRESHOLD,
)
from backend.database import get_database_engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"

SOURCE_REPORTS = [
    ("sales", REPORTS_DIRECTORY / "sales_analysis.csv"),
    ("inventory", REPORTS_DIRECTORY / "inventory_analysis.csv"),
    ("complaints", REPORTS_DIRECTORY / "complaint_analysis.csv"),
    ("vendor_finance", REPORTS_DIRECTORY / "vendor_finance_analysis.csv"),
]

COMMON_COLUMNS = [
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
    "vendor_id",
    "vendor_name",
    "complaint_type",
    "month",
    "summary",
    "evidence",
    "status",
    "detected_at",
]

ISSUE_COLUMNS = [
    "issue_id",
    "title",
    "issue_type",
    "business_area",
    "priority_level",
    "priority_score",
    "priority_reason",
    "status",
    "entity_type",
    "entity_id",
    "store_id",
    "product_id",
    "vendor_id",
    "period_label",
    "finding_count",
    "high_finding_count",
    "medium_finding_count",
    "low_finding_count",
    "root_cause_status",
    "summary",
    "evidence_summary",
]

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

SEVERITY_POINTS = {
    "High": PRIORITY_HIGH_SEVERITY_POINTS,
    "Medium": PRIORITY_MEDIUM_SEVERITY_POINTS,
    "Low": PRIORITY_LOW_SEVERITY_POINTS,
}

CRITICAL_SIGNAL_BONUSES = {
    "Stockout Risk": 30.0,
    "Expired Inventory": 30.0,
    "Near Expiry Stock": 25.0,
    "High Financial Risk": 30.0,
    "Loss-Making Store": 30.0,
    "Store Sales Decline": 25.0,
    "High Complaint Store": 20.0,
    "Monthly Complaint Growth": 15.0,
    "Open High-Severity Complaint": 15.0,
    "Unresolved Complaint Ageing": 15.0,
    "Repeated Vendor Delays": 25.0,
    "Low On-Time Delivery Rate": 20.0,
    "Low Vendor Quality Rating": 20.0,
    "Partial Vendor Deliveries": 15.0,
    "Low Target Achievement": 15.0,
    "Low Operating Profit": 15.0,
}


def clean_text(value: object) -> str:
    """Return a clean string and handle missing values safely."""

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass

    cleaned_value = " ".join(str(value).split())

    if cleaned_value.lower() == "nan":
        return ""

    return cleaned_value


def safe_identifier(value: object) -> str:
    """Convert a value into an uppercase identifier component."""

    identifier = clean_text(value).upper()
    identifier = re.sub(r"[^A-Z0-9]+", "-", identifier)

    return identifier.strip("-")


def first_non_empty(values: pd.Series) -> str:
    """Return the first available non-empty value from a Series."""

    for value in values:
        cleaned_value = clean_text(value)

        if cleaned_value:
            return cleaned_value

    return ""


def unique_non_empty(values: pd.Series) -> list[str]:
    """Return unique non-empty values while preserving their order."""

    unique_values: list[str] = []

    for value in values:
        cleaned_value = clean_text(value)

        if cleaned_value and cleaned_value not in unique_values:
            unique_values.append(cleaned_value)

    return unique_values


def load_all_findings() -> pd.DataFrame:
    """Load detailed finding reports created during Days 10 to 13."""

    all_frames = []

    for source_module, report_path in SOURCE_REPORTS:
        if not report_path.exists():
            raise FileNotFoundError(
                f"Required report not found: {report_path}. "
                "Run the corresponding analytics module first."
            )

        report_dataframe = pd.read_csv(report_path, dtype=object)

        for column in COMMON_COLUMNS:
            if column not in report_dataframe.columns:
                report_dataframe[column] = None

        report_dataframe = report_dataframe[COMMON_COLUMNS].copy()
        report_dataframe["source_module"] = source_module
        report_dataframe["source_report"] = report_path.name

        all_frames.append(report_dataframe)

    return pd.concat(all_frames, ignore_index=True)


def assign_issue_group(row: pd.Series) -> tuple[str, str]:
    """Map one detailed finding to a manager-facing consolidated issue."""

    analysis_type = clean_text(row["analysis_type"])
    business_area = clean_text(row["business_area"])
    store_id = clean_text(row["store_id"])
    product_id = clean_text(row["product_id"])
    vendor_id = clean_text(row["vendor_id"])
    entity_id = clean_text(row["entity_id"])

    if business_area == "Operations":
        if analysis_type == "Overstock":
            group_id = f"{store_id}-{product_id}".strip("-")
            return "Inventory Overstock Risk", group_id or entity_id

        group_id = f"{store_id}-{product_id}".strip("-")
        return "Product Availability Risk", group_id or entity_id

    if business_area == "Sales":
        if (
            analysis_type in {
                "Product Sales Decline",
                "Product Underperformance",
            }
            and product_id
        ):
            return "Product Sales Performance Risk", product_id

        return "Store Performance Risk", store_id or entity_id

    if business_area == "Finance":
        return "Store Performance Risk", store_id or entity_id

    if business_area == "Customer Support":
        if analysis_type == "High Complaint Product":
            return "Product Complaint Risk", product_id or entity_id

        if analysis_type == "Repeated Complaint Category":
            complaint_type = clean_text(row["complaint_type"])
            return "Repeated Complaint Category Risk", complaint_type or entity_id

        if analysis_type in {
            "High Complaint Store",
            "Monthly Complaint Growth",
        }:
            return "Store Performance Risk", store_id or entity_id

        return "Complaint Resolution Backlog", store_id or entity_id

    if business_area == "Procurement":
        return "Vendor Performance Risk", vendor_id or entity_id

    return "General Business Risk", entity_id or analysis_type


def get_issue_title(
    issue_type: str,
    issue_id_component: str,
    issue_group: pd.DataFrame,
) -> str:
    """Create a readable title for each consolidated issue."""

    store_name = first_non_empty(issue_group["store_name"])
    product_name = first_non_empty(issue_group["product_name"])
    vendor_name = first_non_empty(issue_group["vendor_name"])
    complaint_type = first_non_empty(issue_group["complaint_type"])

    if issue_type == "Store Performance Risk":
        return (
            f"Store performance risk at {store_name or issue_id_component}"
        )

    if issue_type == "Product Availability Risk":
        return (
            f"Product availability risk: "
            f"{product_name or issue_id_component} at "
            f"{store_name or 'store'}"
        )

    if issue_type == "Inventory Overstock Risk":
        return (
            f"Overstock risk: {product_name or issue_id_component} at "
            f"{store_name or 'store'}"
        )

    if issue_type == "Complaint Resolution Backlog":
        return (
            f"Complaint resolution backlog at "
            f"{store_name or issue_id_component}"
        )

    if issue_type == "Product Complaint Risk":
        return (
            f"High complaint risk for "
            f"{product_name or issue_id_component}"
        )

    if issue_type == "Repeated Complaint Category Risk":
        return (
            f"Repeated complaint category: "
            f"{complaint_type or issue_id_component}"
        )

    if issue_type == "Vendor Performance Risk":
        return (
            f"Vendor performance risk: "
            f"{vendor_name or issue_id_component}"
        )

    if issue_type == "Product Sales Performance Risk":
        return (
            f"Product sales performance risk: "
            f"{product_name or issue_id_component}"
        )

    return f"{issue_type}: {issue_id_component}"


def get_entity_details(
    issue_type: str,
    issue_group: pd.DataFrame,
) -> tuple[str, str, str, str, str]:
    """Return entity metadata for one consolidated issue."""

    store_id = first_non_empty(issue_group["store_id"])
    product_id = first_non_empty(issue_group["product_id"])
    vendor_id = first_non_empty(issue_group["vendor_id"])

    if issue_type in {
        "Store Performance Risk",
        "Complaint Resolution Backlog",
    }:
        return "Store", store_id, store_id, "", ""

    if issue_type in {
        "Product Availability Risk",
        "Inventory Overstock Risk",
    }:
        entity_id = "-".join(
            value for value in [store_id, product_id] if value
        )
        return "Store Product", entity_id, store_id, product_id, ""

    if issue_type in {
        "Product Complaint Risk",
        "Product Sales Performance Risk",
    }:
        return "Product", product_id, "", product_id, ""

    if issue_type == "Vendor Performance Risk":
        return "Vendor", vendor_id, "", "", vendor_id

    if issue_type == "Repeated Complaint Category Risk":
        complaint_type = first_non_empty(issue_group["complaint_type"])
        return "Complaint Category", complaint_type, "", "", ""

    entity_type = first_non_empty(issue_group["entity_type"])
    entity_id = first_non_empty(issue_group["entity_id"])

    return entity_type, entity_id, store_id, product_id, vendor_id


def get_latest_period(issue_group: pd.DataFrame) -> str:
    """Return the latest month available within the issue evidence."""

    periods = unique_non_empty(issue_group["month"])

    if not periods:
        return ""

    return sorted(periods)[-1]


def calculate_priority(issue_group: pd.DataFrame) -> tuple[float, str, str]:
    """Calculate score, level, and reason for a consolidated issue."""

    severities = unique_non_empty(issue_group["severity"])
    analysis_types = unique_non_empty(issue_group["analysis_type"])
    business_areas = unique_non_empty(issue_group["business_area"])

    severity_scores = [
        SEVERITY_POINTS.get(severity, PRIORITY_LOW_SEVERITY_POINTS)
        for severity in severities
    ]

    maximum_severity_score = max(severity_scores, default=0.0)

    high_finding_count = int(
        issue_group["severity"].astype(str).str.strip().eq("High").sum()
    )

    additional_high_bonus = min(
        max(high_finding_count - 1, 0)
        * PRIORITY_ADDITIONAL_HIGH_FINDING_BONUS,
        PRIORITY_MAX_ADDITIONAL_HIGH_BONUS,
    )

    cross_area_bonus = min(
        max(len(business_areas) - 1, 0) * PRIORITY_CROSS_AREA_BONUS,
        PRIORITY_MAX_CROSS_AREA_BONUS,
    )

    volume_bonus = min(
        max(len(issue_group) - 1, 0) * PRIORITY_FINDING_VOLUME_BONUS,
        PRIORITY_MAX_FINDING_VOLUME_BONUS,
    )

    critical_signal_bonus = max(
        (
            CRITICAL_SIGNAL_BONUSES.get(analysis_type, 0.0)
            for analysis_type in analysis_types
        ),
        default=0.0,
    )

    priority_score = (
        maximum_severity_score
        + additional_high_bonus
        + cross_area_bonus
        + volume_bonus
        + critical_signal_bonus
    )

    if "High" in severities:
        priority_score = max(priority_score, 70.0)

    elif "Medium" in severities:
        priority_score = max(priority_score, 50.0)

    priority_score = round(min(priority_score, 100.0), 2)

    if priority_score >= PRIORITY_HIGH_THRESHOLD:
        priority_level = "High"

    elif priority_score >= PRIORITY_MEDIUM_THRESHOLD:
        priority_level = "Medium"

    else:
        priority_level = "Low"

    highest_severity = (
        "High"
        if "High" in severities
        else "Medium"
        if "Medium" in severities
        else "Low"
    )

    strongest_signal = max(
        analysis_types,
        key=lambda analysis_type: CRITICAL_SIGNAL_BONUSES.get(
            analysis_type,
            0.0,
        ),
        default="General business risk",
    )

    priority_reason = (
        f"Highest Severity: {highest_severity}; "
        f"Strongest Signal: {strongest_signal}; "
        f"Supporting Findings: {len(issue_group)}; "
        f"Business Areas: {', '.join(business_areas)}"
    )

    return priority_score, priority_level, priority_reason


def build_priority_outputs(
    detailed_findings: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Consolidate detailed findings into issues and evidence records."""

    grouped_findings = detailed_findings.copy()

    issue_groups = grouped_findings.apply(
        assign_issue_group,
        axis=1,
        result_type="expand",
    )

    grouped_findings["issue_type"] = issue_groups[0]
    grouped_findings["issue_group_id"] = issue_groups[1]

    issue_records = []
    evidence_records = []

    grouped_data = grouped_findings.groupby(
        ["issue_type", "issue_group_id"],
        dropna=False,
    )

    for (issue_type, issue_id_component), issue_group in grouped_data:
        issue_id = (
            f"ISSUE-{safe_identifier(issue_type)}-"
            f"{safe_identifier(issue_id_component)}"
        )

        entity_type, entity_id, store_id, product_id, vendor_id = (
            get_entity_details(issue_type, issue_group)
        )

        priority_score, priority_level, priority_reason = (
            calculate_priority(issue_group)
        )

        business_areas = unique_non_empty(issue_group["business_area"])
        business_area = (
            "Cross-Functional"
            if len(business_areas) > 1
            else business_areas[0]
            if business_areas
            else "General"
        )

        analysis_types = unique_non_empty(issue_group["analysis_type"])

        finding_count = len(issue_group)
        high_finding_count = int(
            issue_group["severity"]
            .astype(str)
            .str.strip()
            .eq("High")
            .sum()
        )
        medium_finding_count = int(
            issue_group["severity"]
            .astype(str)
            .str.strip()
            .eq("Medium")
            .sum()
        )
        low_finding_count = int(
            issue_group["severity"]
            .astype(str)
            .str.strip()
            .eq("Low")
            .sum()
        )

        title = get_issue_title(
            issue_type,
            clean_text(issue_id_component),
            issue_group,
        )

        summary = (
            f"{finding_count} supporting findings indicate "
            f"{issue_type.lower()}. Key signals: "
            f"{', '.join(analysis_types[:4])}."
        )

        evidence_samples = unique_non_empty(issue_group["evidence"])[:3]
        evidence_summary = " | ".join(evidence_samples)

        issue_records.append(
            {
                "issue_id": issue_id,
                "title": title,
                "issue_type": issue_type,
                "business_area": business_area,
                "priority_level": priority_level,
                "priority_score": priority_score,
                "priority_reason": priority_reason,
                "status": "Open",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "store_id": store_id,
                "product_id": product_id,
                "vendor_id": vendor_id,
                "period_label": get_latest_period(issue_group),
                "finding_count": finding_count,
                "high_finding_count": high_finding_count,
                "medium_finding_count": medium_finding_count,
                "low_finding_count": low_finding_count,
                "root_cause_status": "Pending",
                "summary": summary,
                "evidence_summary": evidence_summary,
            }
        )

        for _, finding_row in issue_group.iterrows():
            evidence_records.append(
                {
                    "issue_id": issue_id,
                    "source_finding_id": clean_text(
                        finding_row["finding_id"]
                    ),
                    "source_report": clean_text(
                        finding_row["source_report"]
                    ),
                    "source_module": clean_text(
                        finding_row["source_module"]
                    ),
                    "analysis_type": clean_text(
                        finding_row["analysis_type"]
                    ),
                    "business_area": clean_text(
                        finding_row["business_area"]
                    ),
                    "severity": clean_text(finding_row["severity"]),
                    "entity_type": clean_text(
                        finding_row["entity_type"]
                    ),
                    "entity_id": clean_text(finding_row["entity_id"]),
                    "store_id": clean_text(finding_row["store_id"]),
                    "product_id": clean_text(
                        finding_row["product_id"]
                    ),
                    "vendor_id": clean_text(finding_row["vendor_id"]),
                    "summary": clean_text(finding_row["summary"]),
                    "evidence": clean_text(finding_row["evidence"]),
                    "detected_at": clean_text(
                        finding_row["detected_at"]
                    ),
                }
            )

    issues_dataframe = pd.DataFrame(
        issue_records,
        columns=ISSUE_COLUMNS,
    )

    evidence_dataframe = pd.DataFrame(
        evidence_records,
        columns=EVIDENCE_COLUMNS,
    )

    if not issues_dataframe.empty:
        priority_order = {
            "High": 1,
            "Medium": 2,
            "Low": 3,
        }

        issues_dataframe["priority_order"] = (
            issues_dataframe["priority_level"].map(priority_order)
        )

        issues_dataframe = issues_dataframe.sort_values(
            by=[
                "priority_order",
                "priority_score",
                "finding_count",
            ],
            ascending=[
                True,
                False,
                False,
            ],
        ).drop(columns=["priority_order"])

        issues_dataframe = issues_dataframe.reset_index(drop=True)

    return issues_dataframe, evidence_dataframe


def create_priority_report(
    issues_dataframe: pd.DataFrame,
    detailed_findings: pd.DataFrame,
) -> str:
    """Create a manager-facing Markdown priority-list report."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Manager Priority List",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        (
            "This report consolidates detailed sales, inventory, complaint, "
            "vendor, and finance findings into manager-facing business issues."
        ),
        "",
        "## Processing Summary",
        "",
        f"- Detailed Findings Processed: {len(detailed_findings)}",
        f"- Consolidated Manager Issues: {len(issues_dataframe)}",
        "",
    ]

    if issues_dataframe.empty:
        lines.extend(
            [
                "No business issues were created from the available findings.",
                "",
            ]
        )
        return "\n".join(lines)

    priority_summary = (
        issues_dataframe.groupby("priority_level")
        .size()
        .reset_index(name="issue_count")
    )

    lines.extend(
        [
            "## Priority Summary",
            "",
            "| Priority Level | Issue Count |",
            "|---|---:|",
        ]
    )

    for row in priority_summary.itertuples(index=False):
        lines.append(
            f"| {row.priority_level} | {row.issue_count} |"
        )

    lines.extend(
        [
            "",
            "## Prioritized Issues",
            "",
            "| Rank | Priority | Score | Business Area | Issue | Supporting Findings |",
            "|---:|---|---:|---|---|---:|",
        ]
    )

    for rank, row in enumerate(
        issues_dataframe.itertuples(index=False),
        start=1,
    ):
        lines.append(
            f"| {rank} | {row.priority_level} | "
            f"{row.priority_score:.2f} | {row.business_area} | "
            f"{row.title} | {row.finding_count} |"
        )

    lines.extend(
        [
            "",
            "## Top Priority Details",
            "",
        ]
    )

    for row in issues_dataframe.head(15).itertuples(index=False):
        lines.extend(
            [
                f"### {row.title}",
                "",
                f"**Issue ID:** {row.issue_id}",
                "",
                f"**Priority:** {row.priority_level} ({row.priority_score:.2f})",
                "",
                f"**Business Area:** {row.business_area}",
                "",
                f"**Priority Reason:** {row.priority_reason}",
                "",
                f"**Summary:** {row.summary}",
                "",
                f"**Evidence Summary:** {row.evidence_summary}",
                "",
            ]
        )

    return "\n".join(lines)


ISSUE_UPSERT_SQL = text(
    """
    INSERT INTO issues (
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
        root_cause_status,
        summary,
        evidence_summary,
        last_detected_at
    )
    VALUES (
        :issue_id,
        :title,
        :issue_type,
        :business_area,
        :priority_level,
        :priority_score,
        :priority_reason,
        :status,
        :entity_type,
        :entity_id,
        :store_id,
        :product_id,
        :vendor_id,
        :period_label,
        :finding_count,
        :high_finding_count,
        :medium_finding_count,
        :low_finding_count,
        :root_cause_status,
        :summary,
        :evidence_summary,
        CURRENT_TIMESTAMP
    )
    ON CONFLICT (issue_id)
    DO UPDATE SET
        title = EXCLUDED.title,
        issue_type = EXCLUDED.issue_type,
        business_area = EXCLUDED.business_area,
        priority_level = EXCLUDED.priority_level,
        priority_score = EXCLUDED.priority_score,
        priority_reason = EXCLUDED.priority_reason,
        entity_type = EXCLUDED.entity_type,
        entity_id = EXCLUDED.entity_id,
        store_id = EXCLUDED.store_id,
        product_id = EXCLUDED.product_id,
        vendor_id = EXCLUDED.vendor_id,
        period_label = EXCLUDED.period_label,
        finding_count = EXCLUDED.finding_count,
        high_finding_count = EXCLUDED.high_finding_count,
        medium_finding_count = EXCLUDED.medium_finding_count,
        low_finding_count = EXCLUDED.low_finding_count,
        summary = EXCLUDED.summary,
        evidence_summary = EXCLUDED.evidence_summary,
        updated_at = CURRENT_TIMESTAMP,
        last_detected_at = CURRENT_TIMESTAMP;
    """
)

EVIDENCE_UPSERT_SQL = text(
    """
    INSERT INTO issue_evidence (
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
    )
    VALUES (
        :issue_id,
        :source_finding_id,
        :source_report,
        :source_module,
        :analysis_type,
        :business_area,
        :severity,
        :entity_type,
        :entity_id,
        :store_id,
        :product_id,
        :vendor_id,
        :summary,
        :evidence,
        NULLIF(:detected_at, '')::TIMESTAMP
    )
    ON CONFLICT (issue_id, source_finding_id)
    DO UPDATE SET
        source_report = EXCLUDED.source_report,
        source_module = EXCLUDED.source_module,
        analysis_type = EXCLUDED.analysis_type,
        business_area = EXCLUDED.business_area,
        severity = EXCLUDED.severity,
        entity_type = EXCLUDED.entity_type,
        entity_id = EXCLUDED.entity_id,
        store_id = EXCLUDED.store_id,
        product_id = EXCLUDED.product_id,
        vendor_id = EXCLUDED.vendor_id,
        summary = EXCLUDED.summary,
        evidence = EXCLUDED.evidence,
        detected_at = EXCLUDED.detected_at;
    """
)


def save_to_database(
    engine: Engine,
    issues_dataframe: pd.DataFrame,
    evidence_dataframe: pd.DataFrame,
) -> None:
    """Upsert consolidated issues and their evidence into PostgreSQL."""

    if issues_dataframe.empty:
        print("No issues available for database storage.")
        return

    issue_records = issues_dataframe.to_dict(orient="records")
    evidence_records = evidence_dataframe.to_dict(orient="records")

    with engine.begin() as connection:
        connection.execute(ISSUE_UPSERT_SQL, issue_records)

        if evidence_records:
            connection.execute(EVIDENCE_UPSERT_SQL, evidence_records)


def print_primary_scenario_check(issues_dataframe: pd.DataFrame) -> None:
    """Verify the important project scenarios after consolidation."""

    expected_issue_ids = [
        "ISSUE-STORE-PERFORMANCE-RISK-S003",
        "ISSUE-PRODUCT-AVAILABILITY-RISK-S003-P017",
        "ISSUE-VENDOR-PERFORMANCE-RISK-V004",
        "ISSUE-VENDOR-PERFORMANCE-RISK-V009",
    ]

    available_issue_ids = set(issues_dataframe["issue_id"])

    print("\nPrimary Scenario Check:")

    for issue_id in expected_issue_ids:
        print(
            f"- {issue_id}: "
            f"{'Detected' if issue_id in available_issue_ids else 'Not detected'}"
        )


def main() -> None:
    """Run issue consolidation and store priority data in PostgreSQL."""

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("Loading detailed analytics findings...")

    detailed_findings = load_all_findings()

    print(
        f"Detailed findings loaded successfully: "
        f"{len(detailed_findings)}"
    )

    print("Consolidating findings into manager-facing issues...")

    issues_dataframe, evidence_dataframe = build_priority_outputs(
        detailed_findings
    )

    priority_csv_path = REPORTS_DIRECTORY / "priority_list.csv"
    evidence_csv_path = REPORTS_DIRECTORY / "priority_evidence.csv"
    priority_markdown_path = REPORTS_DIRECTORY / "priority_list_report.md"

    issues_dataframe.to_csv(priority_csv_path, index=False)
    evidence_dataframe.to_csv(evidence_csv_path, index=False)

    priority_report = create_priority_report(
        issues_dataframe,
        detailed_findings,
    )

    priority_markdown_path.write_text(
        priority_report,
        encoding="utf-8",
    )

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        print("Saving consolidated issues and evidence to PostgreSQL...")

        save_to_database(
            engine,
            issues_dataframe,
            evidence_dataframe,
        )

        print("\nPriority-engine processing completed successfully.")
        print(
            f"Manager-facing issues created: "
            f"{len(issues_dataframe)}"
        )
        print(
            f"Evidence records stored: "
            f"{len(evidence_dataframe)}"
        )

        if not issues_dataframe.empty:
            print("\nIssues by priority level:")

            print(
                issues_dataframe.groupby("priority_level")
                .size()
                .reset_index(name="issue_count")
                .to_string(index=False)
            )

        print_primary_scenario_check(issues_dataframe)

        print(f"\nPriority CSV saved at: {priority_csv_path}")
        print(f"Evidence CSV saved at: {evidence_csv_path}")
        print(
            f"Priority Markdown report saved at: "
            f"{priority_markdown_path}"
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
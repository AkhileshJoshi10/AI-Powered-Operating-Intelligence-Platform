from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from backend.database import get_database_engine, read_query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"


OUTPUT_COLUMNS = [
    "executive_rank",
    "issue_id",
    "title",
    "issue_type",
    "business_area",
    "priority_level",
    "priority_score",
    "priority_reason",
    "critical_evidence_score",
    "repetition_adjustment",
    "executive_score",
    "critical_signals",
    "minimum_stock_ratio_percent",
    "selection_reason",
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
    "summary",
    "evidence_summary",
    "last_detected_at",
]


PRIORITY_ORDER = {
    "High": 1,
    "Medium": 2,
    "Low": 3,
}

# These values reduce repetition in the executive list.
# They apply equally to every issue type and business area.
ISSUE_TYPE_REPEAT_ADJUSTMENT = 18.0
BUSINESS_AREA_REPEAT_ADJUSTMENT = 4.0

# These scores are based on evidence severity, not on any particular store,
# product, vendor, or demo scenario.
SIGNAL_BASE_SCORES = {
    "Stockout Risk": 40.0,
    "Expired Inventory": 50.0,
    "Near Expiry Stock": 25.0,
    "Loss-Making Store": 45.0,
    "High Financial Risk": 35.0,
    "Repeated Vendor Delays": 25.0,
    "Low On-Time Delivery Rate": 18.0,
    "Low Vendor Quality Rating": 15.0,
    "Partial Vendor Deliveries": 12.0,
    "Store Sales Decline": 20.0,
    "Low Target Achievement": 12.0,
    "Low Operating Profit": 12.0,
    "High Complaint Store": 12.0,
    "High Complaint Product": 10.0,
    "Monthly Complaint Growth": 10.0,
    "Open High-Severity Complaint": 15.0,
    "Unresolved Complaint Ageing": 10.0,
    "Repeated Complaint Category": 8.0,
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

    cleaned_value = " ".join(str(value).split())

    if cleaned_value.lower() == "nan":
        return ""

    return cleaned_value


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


def extract_number(pattern: str, text: object) -> float | None:
    """Extract a numeric value from evidence text using a regex pattern."""

    match = re.search(
        pattern,
        clean_text(text),
        flags=re.IGNORECASE,
    )

    if match is None:
        return None

    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


def get_evidence_signal_score(
    analysis_type: str,
    evidence: object,
    severity: str,
) -> tuple[float, str, float | None]:
    """
    Calculate evidence-based urgency for one supporting finding.

    Returns:
    - evidence score
    - readable signal label
    - stock ratio if this is a stockout finding
    """

    analysis_type = clean_text(analysis_type)
    severity = clean_text(severity)
    evidence_text = clean_text(evidence)

    base_score = SIGNAL_BASE_SCORES.get(
        analysis_type,
        0.0,
    )

    stock_ratio_percent: float | None = None
    signal_label = analysis_type

    if analysis_type == "Stockout Risk":
        stock_ratio_percent = extract_number(
            r"Stock Ratio:\s*([0-9]+(?:\.[0-9]+)?)%",
            evidence_text,
        )

        if stock_ratio_percent is None:
            return 50.0, "Stockout Risk", None

        # Lower stock ratio means greater urgency.
        # 5% stock ratio gets a much higher score than 40% stock ratio.
        stock_urgency = max(
            0.0,
            min(50.0, 50.0 - stock_ratio_percent),
        )

        score = 40.0 + (stock_urgency * 0.8)

        signal_label = (
            f"Stockout Risk "
            f"({stock_ratio_percent:.2f}% of reorder level)"
        )

        return round(score, 2), signal_label, stock_ratio_percent

    if analysis_type == "Near Expiry Stock":
        days_to_expiry = extract_number(
            r"Days to Expiry:\s*([0-9]+(?:\.[0-9]+)?)",
            evidence_text,
        )

        if days_to_expiry is not None:
            urgency_bonus = max(
                0.0,
                min(20.0, (30.0 - days_to_expiry) * 0.75),
            )

            return (
                round(base_score + urgency_bonus, 2),
                f"Near Expiry Stock ({days_to_expiry:.0f} days)",
                None,
            )

    if analysis_type == "Repeated Vendor Delays":
        maximum_delay_days = extract_number(
            r"Maximum Delay:\s*([0-9]+(?:\.[0-9]+)?)\s*days",
            evidence_text,
        )

        if maximum_delay_days is not None:
            delay_bonus = max(
                0.0,
                min(25.0, (maximum_delay_days - 5.0) * 1.5),
            )

            return (
                round(base_score + delay_bonus, 2),
                f"Repeated Vendor Delays "
                f"({maximum_delay_days:.0f} maximum delay days)",
                None,
            )

    if analysis_type == "Low On-Time Delivery Rate":
        on_time_rate = extract_number(
            r"On-Time Delivery Rate:\s*([0-9]+(?:\.[0-9]+)?)%",
            evidence_text,
        )

        if on_time_rate is not None:
            performance_gap = max(0.0, 70.0 - on_time_rate)

            rate_bonus = min(
                20.0,
                performance_gap * 0.5,
            )

            return (
                round(base_score + rate_bonus, 2),
                f"Low On-Time Delivery Rate ({on_time_rate:.2f}%)",
                None,
            )

    if analysis_type in {
        "Open High-Severity Complaint",
        "Unresolved Complaint Ageing",
    }:
        complaint_age_days = extract_number(
            r"Age Against Latest Dataset Date:\s*"
            r"([0-9]+(?:\.[0-9]+)?)\s*days",
            evidence_text,
        )

        if complaint_age_days is not None:
            age_bonus = min(
                15.0,
                max(0.0, complaint_age_days - 7.0) * 0.5,
            )

            return (
                round(base_score + age_bonus, 2),
                f"{analysis_type} ({complaint_age_days:.0f} days old)",
                None,
            )

    if base_score > 0:
        return base_score, signal_label, None

    if severity == "High":
        return 8.0, "High-Severity Supporting Evidence", None

    if severity == "Medium":
        return 3.0, "Medium-Severity Supporting Evidence", None

    return 0.0, "", None


def build_evidence_profiles(
    evidence_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert detailed issue evidence into one evidence profile per issue.

    The final score uses the strongest signal plus a small multi-signal
    bonus. It does not add every evidence row together, preventing a large
    complaint backlog from dominating solely because it has many rows.
    """

    profile_columns = [
        "issue_id",
        "critical_evidence_score",
        "critical_signals",
        "minimum_stock_ratio_percent",
    ]

    if evidence_dataframe.empty:
        return pd.DataFrame(columns=profile_columns)

    profile_records = []

    for issue_id, issue_evidence in evidence_dataframe.groupby("issue_id"):
        signal_scores: list[float] = []
        signal_labels: list[str] = []
        stock_ratios: list[float] = []
        unique_analysis_types: list[str] = []

        for row in issue_evidence.itertuples(index=False):
            analysis_type = clean_text(row.analysis_type)

            score, label, stock_ratio = get_evidence_signal_score(
                analysis_type=analysis_type,
                evidence=row.evidence,
                severity=row.severity,
            )

            if score > 0:
                signal_scores.append(score)

            if label and label not in signal_labels:
                signal_labels.append(label)

            if stock_ratio is not None:
                stock_ratios.append(stock_ratio)

            if (
                analysis_type
                and analysis_type not in unique_analysis_types
                and score > 0
            ):
                unique_analysis_types.append(analysis_type)

        strongest_signal_score = max(signal_scores, default=0.0)

        # Multiple distinct signals matter, but the bonus is capped.
        multi_signal_bonus = min(
            max(len(unique_analysis_types) - 1, 0) * 4.0,
            12.0,
        )

        critical_evidence_score = round(
            strongest_signal_score + multi_signal_bonus,
            2,
        )

        profile_records.append(
            {
                "issue_id": clean_text(issue_id),
                "critical_evidence_score": critical_evidence_score,
                "critical_signals": " | ".join(signal_labels[:4]),
                "minimum_stock_ratio_percent": (
                    round(min(stock_ratios), 2)
                    if stock_ratios
                    else None
                ),
            }
        )

    return pd.DataFrame(
        profile_records,
        columns=profile_columns,
    )


def load_active_issues(engine: Engine) -> pd.DataFrame:
    """Load active issues and their detailed supporting evidence."""

    issues_query = """
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

    evidence_query = """
    SELECT
        e.issue_id,
        e.analysis_type,
        e.severity,
        e.evidence
    FROM issue_evidence AS e
    INNER JOIN issues AS i
        ON e.issue_id = i.issue_id
    WHERE i.status IN ('Open', 'In Progress');
    """

    issues = read_query(engine, issues_query)
    evidence = read_query(engine, evidence_query)

    if issues.empty:
        return issues

    evidence_profiles = build_evidence_profiles(evidence)

    issues = issues.merge(
        evidence_profiles,
        on="issue_id",
        how="left",
    )

    issues["priority_score"] = pd.to_numeric(
        issues["priority_score"],
        errors="coerce",
    ).fillna(0.0)

    issues["critical_evidence_score"] = pd.to_numeric(
        issues["critical_evidence_score"],
        errors="coerce",
    ).fillna(0.0)

    issues["minimum_stock_ratio_percent"] = pd.to_numeric(
        issues["minimum_stock_ratio_percent"],
        errors="coerce",
    )

    issues["critical_signals"] = issues["critical_signals"].fillna("")

    issues["priority_order"] = issues["priority_level"].map(
        PRIORITY_ORDER
    ).fillna(4)

    return issues.sort_values(
        by=[
            "priority_order",
            "priority_score",
            "high_finding_count",
            "finding_count",
            "last_detected_at",
        ],
        ascending=[
            True,
            False,
            False,
            False,
            False,
        ],
    ).reset_index(drop=True)


def calculate_repetition_adjustment(
    row: pd.Series,
    issue_type_counts: Counter,
    business_area_counts: Counter,
) -> float:
    """
    Apply a generic anti-duplication adjustment.

    Every repeated issue type receives the same adjustment.
    Every repeated business area receives the same small adjustment.
    No business area or issue type is reserved, blocked, or forced.
    """

    issue_type = clean_text(row["issue_type"])
    business_area = clean_text(row["business_area"])

    issue_type_adjustment = (
        issue_type_counts[issue_type]
        * ISSUE_TYPE_REPEAT_ADJUSTMENT
    )

    business_area_adjustment = (
        business_area_counts[business_area]
        * BUSINESS_AREA_REPEAT_ADJUSTMENT
    )

    return round(
        issue_type_adjustment + business_area_adjustment,
        2,
    )


def select_executive_priorities(
    active_issues: pd.DataFrame,
    limit: int,
) -> pd.DataFrame:
    """
    Select priorities entirely by evidence-based executive score.

    Selection is iterative because repeated issue types receive a generic
    duplication adjustment after one has already been selected.
    """

    if active_issues.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    remaining_issues = active_issues.copy()
    selected_records: list[dict] = []

    issue_type_counts: Counter = Counter()
    business_area_counts: Counter = Counter()

    while (
        len(selected_records) < limit
        and not remaining_issues.empty
    ):
        candidate_records = []

        for _, row in remaining_issues.iterrows():
            repetition_adjustment = calculate_repetition_adjustment(
                row=row,
                issue_type_counts=issue_type_counts,
                business_area_counts=business_area_counts,
            )

            executive_score = round(
                safe_float(row["priority_score"])
                + safe_float(row["critical_evidence_score"])
                - repetition_adjustment,
                2,
            )

            candidate_record = row.to_dict()
            candidate_record["repetition_adjustment"] = (
                repetition_adjustment
            )
            candidate_record["executive_score"] = executive_score

            candidate_records.append(candidate_record)

        candidate_dataframe = pd.DataFrame(candidate_records)

        candidate_dataframe = candidate_dataframe.sort_values(
            by=[
                "executive_score",
                "priority_score",
                "critical_evidence_score",
                "high_finding_count",
                "finding_count",
                "last_detected_at",
            ],
            ascending=[
                False,
                False,
                False,
                False,
                False,
                False,
            ],
        ).reset_index(drop=True)

        selected_candidate = candidate_dataframe.iloc[0].to_dict()

        priority_score = safe_float(
            selected_candidate["priority_score"]
        )
        evidence_score = safe_float(
            selected_candidate["critical_evidence_score"]
        )
        repetition_adjustment = safe_float(
            selected_candidate["repetition_adjustment"]
        )

        selected_candidate["selection_reason"] = (
            "Selected by executive score: "
            f"base priority {priority_score:.2f} + "
            f"critical evidence {evidence_score:.2f} - "
            f"repetition adjustment {repetition_adjustment:.2f}."
        )

        selected_records.append(selected_candidate)

        selected_issue_id = clean_text(
            selected_candidate["issue_id"]
        )

        selected_issue_type = clean_text(
            selected_candidate["issue_type"]
        )

        selected_business_area = clean_text(
            selected_candidate["business_area"]
        )

        issue_type_counts[selected_issue_type] += 1
        business_area_counts[selected_business_area] += 1

        remaining_issues = remaining_issues[
            remaining_issues["issue_id"].ne(selected_issue_id)
        ].copy()

    selected_dataframe = pd.DataFrame(selected_records)

    if selected_dataframe.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    selected_dataframe.insert(
        0,
        "executive_rank",
        range(1, len(selected_dataframe) + 1),
    )

    return selected_dataframe[OUTPUT_COLUMNS]


def create_markdown_report(
    executive_priorities: pd.DataFrame,
    total_active_issue_count: int,
    limit: int,
) -> str:
    """Create the executive priority report."""

    generated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    lines = [
        "# Executive Priority List",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        (
            "This report ranks active issues using a fully score-driven "
            "approach. No store, product, vendor, business area, or issue "
            "type is manually reserved for the list."
        ),
        "",
        "## Ranking Method",
        "",
        (
            "Executive Score = Base Priority Score + Critical Evidence "
            "Score − Repetition Adjustment"
        ),
        "",
        "- Base Priority Score: score calculated by the priority engine.",
        (
            "- Critical Evidence Score: urgency derived from supporting "
            "evidence such as stock ratio, expired stock, delivery delays, "
            "financial risk, and unresolved high-severity complaints."
        ),
        (
            "- Repetition Adjustment: a generic adjustment applied after "
            "similar issue types or business areas have already appeared, "
            "to prevent near-identical issues from filling the full list."
        ),
        "",
        "## Scope",
        "",
        f"- Total Active Issues in Internal Register: {total_active_issue_count}",
        f"- Executive Priorities Selected: {len(executive_priorities)}",
        f"- Requested List Size: {limit}",
        "",
    ]

    if executive_priorities.empty:
        lines.extend(
            [
                "No active issues are currently available.",
                "",
            ]
        )

        return "\n".join(lines)

    lines.extend(
        [
            "## Executive Priorities",
            "",
            (
                "| Rank | Executive Score | Priority | Critical Evidence | "
                "Issue |"
            ),
            "|---:|---:|---|---:|---|",
        ]
    )

    for row in executive_priorities.itertuples(index=False):
        lines.append(
            f"| {safe_int(row.executive_rank)} | "
            f"{safe_float(row.executive_score):.2f} | "
            f"{clean_text(row.priority_level)} | "
            f"{safe_float(row.critical_evidence_score):.2f} | "
            f"{clean_text(row.title)} |"
        )

    lines.extend(
        [
            "",
            "## Priority Details",
            "",
        ]
    )

    for row in executive_priorities.itertuples(index=False):
        stock_ratio_text = "Not applicable"

        if pd.notna(row.minimum_stock_ratio_percent):
            stock_ratio_text = (
                f"{safe_float(row.minimum_stock_ratio_percent):.2f}%"
            )

        critical_signals = clean_text(row.critical_signals)

        if not critical_signals:
            critical_signals = "No additional critical signal identified"

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
                    f"**Base Priority Score:** "
                    f"{safe_float(row.priority_score):.2f}"
                ),
                "",
                (
                    f"**Critical Evidence Score:** "
                    f"{safe_float(row.critical_evidence_score):.2f}"
                ),
                "",
                (
                    f"**Repetition Adjustment:** "
                    f"{safe_float(row.repetition_adjustment):.2f}"
                ),
                "",
                f"**Critical Signals:** {critical_signals}",
                "",
                f"**Minimum Stock Ratio:** {stock_ratio_text}",
                "",
                f"**Business Area:** {clean_text(row.business_area)}",
                "",
                f"**Issue Type:** {clean_text(row.issue_type)}",
                "",
                f"**Selection Reason:** {clean_text(row.selection_reason)}",
                "",
                f"**Priority Reason:** {clean_text(row.priority_reason)}",
                "",
                f"**Summary:** {clean_text(row.summary)}",
                "",
                (
                    f"**Supporting Findings:** "
                    f"{safe_int(row.finding_count)} "
                    f"(High: {safe_int(row.high_finding_count)}, "
                    f"Medium: {safe_int(row.medium_finding_count)}, "
                    f"Low: {safe_int(row.low_finding_count)})"
                ),
                "",
                (
                    f"**Evidence Summary:** "
                    f"{clean_text(row.evidence_summary)}"
                ),
                "",
            ]
        )

    return "\n".join(lines)


def print_executive_preview(
    executive_priorities: pd.DataFrame,
) -> None:
    """Print a compact executive-priority preview in the terminal."""

    print("\nExecutive Priority Preview:")

    if executive_priorities.empty:
        print("No active issues were found.")
        return

    preview_columns = [
        "executive_rank",
        "executive_score",
        "priority_level",
        "priority_score",
        "critical_evidence_score",
        "repetition_adjustment",
        "title",
    ]

    print(
        executive_priorities[preview_columns]
        .to_string(index=False)
    )


def main() -> None:
    """Create the evidence-driven executive priority list."""

    parser = argparse.ArgumentParser(
        description=(
            "Create an evidence-driven executive priority list."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of executive priorities. Default: 10.",
    )

    arguments = parser.parse_args()
    limit = arguments.limit

    if limit <= 0:
        raise ValueError("--limit must be greater than zero.")

    REPORTS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        print("Loading active issues and supporting evidence...")

        active_issues = load_active_issues(engine)

        print(
            "Ranking issues using evidence-driven executive scores..."
        )

        executive_priorities = select_executive_priorities(
            active_issues=active_issues,
            limit=limit,
        )

        csv_output_path = (
            REPORTS_DIRECTORY / "executive_priority_list.csv"
        )

        markdown_output_path = (
            REPORTS_DIRECTORY / "executive_priority_list_report.md"
        )

        executive_priorities.to_csv(
            csv_output_path,
            index=False,
        )

        markdown_report = create_markdown_report(
            executive_priorities=executive_priorities,
            total_active_issue_count=len(active_issues),
            limit=limit,
        )

        markdown_output_path.write_text(
            markdown_report,
            encoding="utf-8",
        )

        print("\nExecutive priority list created successfully.")
        print(
            f"Executive priorities selected: "
            f"{len(executive_priorities)}"
        )

        print_executive_preview(executive_priorities)

        print(f"\nCSV report saved at: {csv_output_path}")
        print(
            f"Markdown report saved at: "
            f"{markdown_output_path}"
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
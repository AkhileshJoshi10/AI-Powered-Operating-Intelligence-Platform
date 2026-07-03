from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from backend.database import get_database_engine, read_query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIRECTORY = PROJECT_ROOT / "reports"

OUTPUT_COLUMNS = [
    "manager_rank",
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
    "summary",
    "evidence_summary",
    "last_detected_at",
]


def clean_text(value: object) -> str:
    """Return cleaned text and safely handle missing values."""

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


def load_manager_priorities(
    engine: Engine,
    limit: int,
) -> pd.DataFrame:
    """
    Load the highest-priority active issues from PostgreSQL.

    Only Open and In Progress issues are included because resolved or
    rejected issues should not appear in the manager's active priority list.
    """

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
    WHERE status IN ('Open', 'In Progress')
    ORDER BY
        CASE priority_level
            WHEN 'High' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 3
            ELSE 4
        END,
        priority_score DESC,
        high_finding_count DESC,
        finding_count DESC,
        last_detected_at DESC
    LIMIT :limit;
    """

    priorities = read_query(
        engine,
        query,
        {"limit": limit},
    )

    if priorities.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    priorities.insert(
        0,
        "manager_rank",
        range(1, len(priorities) + 1),
    )

    return priorities[OUTPUT_COLUMNS]


def load_active_issue_summary(engine: Engine) -> pd.DataFrame:
    """Load total active-issue counts for report context."""

    query = """
    SELECT
        priority_level,
        COUNT(*) AS issue_count
    FROM issues
    WHERE status IN ('Open', 'In Progress')
    GROUP BY priority_level
    ORDER BY
        CASE priority_level
            WHEN 'High' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 3
            ELSE 4
        END;
    """

    return read_query(engine, query)


def create_markdown_report(
    priorities: pd.DataFrame,
    active_issue_summary: pd.DataFrame,
    limit: int,
) -> str:
    """Create a readable manager-facing priority-list report."""

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# Manager Top Priority List",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        (
            "This report shows the highest-priority active issues that "
            "require management attention. The complete issue register "
            "remains available in the PostgreSQL `issues` table and "
            "`reports/priority_list.csv`."
        ),
        "",
        "## Active Issue Summary",
        "",
        "| Priority Level | Active Issues |",
        "|---|---:|",
    ]

    if active_issue_summary.empty:
        lines.append("| No active issues | 0 |")
    else:
        for row in active_issue_summary.itertuples(index=False):
            lines.append(
                f"| {clean_text(row.priority_level)} | "
                f"{safe_int(row.issue_count)} |"
            )

    lines.extend(
        [
            "",
            f"## Top {limit} Manager Priorities",
            "",
        ]
    )

    if priorities.empty:
        lines.extend(
            [
                "No Open or In Progress issues are currently available.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            (
                "| Rank | Priority | Score | Business Area | Issue | "
                "Supporting Findings |"
            ),
            "|---:|---|---:|---|---|---:|",
        ]
    )

    for row in priorities.itertuples(index=False):
        lines.append(
            f"| {safe_int(row.manager_rank)} | "
            f"{clean_text(row.priority_level)} | "
            f"{safe_float(row.priority_score):.2f} | "
            f"{clean_text(row.business_area)} | "
            f"{clean_text(row.title)} | "
            f"{safe_int(row.finding_count)} |"
        )

    lines.extend(
        [
            "",
            "## Priority Details",
            "",
        ]
    )

    for row in priorities.itertuples(index=False):
        lines.extend(
            [
                f"### {safe_int(row.manager_rank)}. {clean_text(row.title)}",
                "",
                f"**Issue ID:** {clean_text(row.issue_id)}",
                "",
                (
                    f"**Priority:** {clean_text(row.priority_level)} "
                    f"({safe_float(row.priority_score):.2f}/100)"
                ),
                "",
                f"**Business Area:** {clean_text(row.business_area)}",
                "",
                f"**Status:** {clean_text(row.status)}",
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
                f"**Evidence Summary:** {clean_text(row.evidence_summary)}",
                "",
            ]
        )

    return "\n".join(lines)


def print_top_priority_preview(priorities: pd.DataFrame) -> None:
    """Print a compact terminal preview of the manager priority list."""

    print("\nTop Manager Priorities:")

    if priorities.empty:
        print("No active issues were found.")
        return

    preview_columns = [
        "manager_rank",
        "priority_level",
        "priority_score",
        "business_area",
        "title",
        "finding_count",
    ]

    print(
        priorities[preview_columns]
        .head(10)
        .to_string(index=False)
    )


def main() -> None:
    """Create a manager-facing Top Priority List from active issues."""

    parser = argparse.ArgumentParser(
        description=(
            "Create a manager-facing Top Priority List from PostgreSQL issues."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=15,
        help="Maximum number of active issues to include. Default: 15.",
    )

    arguments = parser.parse_args()
    limit = arguments.limit

    if limit <= 0:
        raise ValueError("--limit must be greater than zero.")

    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        print("Loading active manager priorities...")

        priorities = load_manager_priorities(engine, limit)

        print("Loading active issue summary...")

        active_issue_summary = load_active_issue_summary(engine)

        csv_output_path = (
            REPORTS_DIRECTORY / "manager_top_priority_list.csv"
        )
        markdown_output_path = (
            REPORTS_DIRECTORY / "manager_top_priority_list_report.md"
        )

        priorities.to_csv(csv_output_path, index=False)

        markdown_report = create_markdown_report(
            priorities,
            active_issue_summary,
            limit,
        )

        markdown_output_path.write_text(
            markdown_report,
            encoding="utf-8",
        )

        print("\nManager priority list created successfully.")
        print(f"Top priorities included: {len(priorities)}")

        print_top_priority_preview(priorities)

        print(f"\nCSV report saved at: {csv_output_path}")
        print(f"Markdown report saved at: {markdown_output_path}")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
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

OUTPUT_COLUMNS = [
    "executive_rank",
    "issue_id",
    "issue_title",
    "issue_type",
    "business_area",
    "priority_level",
    "priority_score",
    "executive_score",
    "root_cause_category",
    "root_cause_summary",
    "root_cause_confidence_score",
    "recommendation_title",
    "recommendation_text",
    "suggested_owner_role",
    "suggested_deadline",
    "expected_impact",
    "confidence_score",
    "status",
    "generated_at",
]


def clean_text(value: object) -> str:
    """Return cleaned text while safely handling missing values."""

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    cleaned_value = " ".join(str(value).split())

    if cleaned_value.lower() == "nan":
        return ""

    return cleaned_value


def safe_float(value: object) -> float:
    """Convert a scalar value safely to float."""

    if value is None:
        return 0.0

    try:
        if pd.isna(value):
            return 0.0
    except (TypeError, ValueError):
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: object) -> int:
    """Convert a scalar value safely to integer."""

    return int(safe_float(value))


def optional_float(value: object) -> float | None:
    """Convert a scalar value to a rounded float or return None."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return None

    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def format_action_steps(action_steps: list[str]) -> str:
    """Convert action steps into one readable recommendation string."""

    formatted_steps = []

    for step_number, action_step in enumerate(action_steps, start=1):
        formatted_steps.append(
            f"{step_number}. {clean_text(action_step)}"
        )

    return " ".join(formatted_steps)


def load_executive_priority_reference(limit: int) -> pd.DataFrame:
    """Load the current executive-priority issue reference."""

    if not EXECUTIVE_PRIORITY_FILE.exists():
        raise FileNotFoundError(
            "Executive priority file was not found. Run this first:\n"
            "python -m backend.analytics.executive_priority_selector"
        )

    priorities = pd.read_csv(
        EXECUTIVE_PRIORITY_FILE,
        dtype=object,
    )

    required_columns = {
        "issue_id",
        "executive_rank",
        "executive_score",
    }

    missing_columns = required_columns.difference(
        priorities.columns
    )

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

    return (
        priorities.sort_values("executive_rank")
        .head(limit)[
            [
                "issue_id",
                "executive_rank",
                "executive_score",
            ]
        ]
        .copy()
    )


def load_recommendation_context(
    engine: Engine,
    priority_reference: pd.DataFrame,
) -> pd.DataFrame:
    """
    Load issue and root-cause information for executive priorities.

    Rejected and superseded root-cause analyses are excluded.
    """

    query = """
    SELECT
        i.issue_id,
        i.title AS issue_title,
        i.issue_type,
        i.business_area,
        i.priority_level,
        i.priority_score,
        i.priority_reason,
        i.status AS issue_status,
        i.entity_type,
        i.entity_id,
        i.store_id,
        i.product_id,
        i.vendor_id,
        i.period_label,
        i.summary AS issue_summary,
        i.evidence_summary,
        r.root_cause_category,
        r.root_cause_summary,
        r.root_cause_explanation,
        r.confidence_score AS root_cause_confidence_score,
        r.evidence_count AS root_cause_evidence_count,
        r.analysis_status AS root_cause_analysis_status,
        r.review_status AS root_cause_review_status,
        r.analysis_version
    FROM issues AS i
    INNER JOIN root_cause_analyses AS r
        ON i.issue_id = r.issue_id
    WHERE
        i.status IN ('Open', 'In Progress')
        AND r.analysis_status IN ('Generated', 'Reviewed')
        AND r.review_status <> 'Rejected';
    """

    context = read_query(engine, query)

    if context.empty:
        return context

    selected_context = priority_reference.merge(
        context,
        on="issue_id",
        how="inner",
    )

    return selected_context.sort_values(
        by="executive_rank"
    ).reset_index(drop=True)


def adjust_deadline_days(
    base_deadline_days: int,
    priority_level: str,
) -> int:
    """Adjust a recommendation deadline according to priority."""

    if priority_level == "High":
        return max(1, base_deadline_days - 2)

    if priority_level == "Medium":
        return base_deadline_days

    return base_deadline_days + 5


def calculate_recommendation_confidence(
    issue: pd.Series,
) -> float:
    """
    Calculate confidence in the proposed recommendation.

    The score combines root-cause evidence strength and issue priority.
    It does not guarantee that the action will produce the expected result.
    """

    root_cause_confidence = safe_float(
        issue["root_cause_confidence_score"]
    )

    priority_score = safe_float(
        issue["priority_score"]
    )

    evidence_count = safe_int(
        issue["root_cause_evidence_count"]
    )

    evidence_strength = min(
        evidence_count * 12.5,
        100.0,
    )

    confidence_score = (
        root_cause_confidence * 0.70
        + priority_score * 0.20
        + evidence_strength * 0.10
    )

    root_cause_review_status = clean_text(
        issue["root_cause_review_status"]
    )

    if root_cause_review_status == "Accepted":
        confidence_score += 3.0
    elif root_cause_review_status == "Edited":
        confidence_score += 2.0

    return round(
        max(50.0, min(confidence_score, 95.0)),
        2,
    )


def build_inventory_recommendation(
    issue: pd.Series,
) -> dict:
    """Build an action plan for product availability risk."""

    return {
        "recommendation_title": (
            f"Restore product availability: "
            f"{clean_text(issue['issue_title'])}"
        ),
        "suggested_owner_role": "Inventory Manager",
        "base_deadline_days": 3,
        "expected_impact": (
            "Reduce stockout exposure, protect product sales, and "
            "prevent additional availability-related complaints."
        ),
        "action_steps": [
            (
                "Confirm the latest physical stock and pending "
                "purchase-order quantity for the affected product."
            ),
            (
                "Arrange an urgent stock transfer from a nearby store "
                "or expedite the existing vendor order."
            ),
            (
                "Review the reorder level and recent sales velocity to "
                "determine whether the replenishment setting is too low."
            ),
            (
                "Track stock daily until inventory returns to a safe "
                "operating level."
            ),
        ],
    }


def build_store_performance_recommendation(
    issue: pd.Series,
) -> dict:
    """Build a store recovery recommendation."""

    return {
        "recommendation_title": (
            f"Launch store performance recovery plan: "
            f"{clean_text(issue['issue_title'])}"
        ),
        "suggested_owner_role": "Regional Operations Manager",
        "base_deadline_days": 7,
        "expected_impact": (
            "Improve store sales, target achievement, operating "
            "performance, and customer experience."
        ),
        "action_steps": [
            (
                "Review the largest declining categories and products "
                "with the store manager."
            ),
            (
                "Identify whether low stock, customer complaints, "
                "pricing, promotions, or local execution are reducing sales."
            ),
            (
                "Create a short recovery plan with category-level sales "
                "targets and accountable owners."
            ),
            (
                "Review progress weekly against sales, profit, inventory, "
                "and complaint indicators."
            ),
        ],
    }


def build_vendor_recommendation(
    issue: pd.Series,
) -> dict:
    """Build a vendor performance improvement recommendation."""

    return {
        "recommendation_title": (
            f"Correct vendor delivery performance: "
            f"{clean_text(issue['issue_title'])}"
        ),
        "suggested_owner_role": "Procurement Manager",
        "base_deadline_days": 5,
        "expected_impact": (
            "Improve delivery reliability, reduce replenishment delays, "
            "and lower the risk of store-level stock shortages."
        ),
        "action_steps": [
            (
                "Review recent delayed and partial deliveries against "
                "the vendor service-level agreement."
            ),
            (
                "Request a corrective delivery plan with confirmed "
                "dispatch dates and quantity commitments."
            ),
            (
                "Identify products and stores currently exposed to the "
                "vendor's delivery risk."
            ),
            (
                "Prepare a backup supplier or alternative fulfilment "
                "route if performance does not improve."
            ),
        ],
    }


def build_complaint_backlog_recommendation(
    issue: pd.Series,
) -> dict:
    """Build a complaint backlog reduction recommendation."""

    return {
        "recommendation_title": (
            f"Clear complaint resolution backlog: "
            f"{clean_text(issue['issue_title'])}"
        ),
        "suggested_owner_role": "Customer Support Manager",
        "base_deadline_days": 3,
        "expected_impact": (
            "Reduce unresolved and high-severity complaints, improve "
            "response time, and limit customer dissatisfaction."
        ),
        "action_steps": [
            (
                "Separate high-severity and aged complaints for immediate "
                "review and escalation."
            ),
            (
                "Assign a named owner and target resolution date to every "
                "open or in-progress complaint."
            ),
            (
                "Identify the leading complaint categories and address "
                "their operational causes with the relevant store team."
            ),
            (
                "Review backlog size and closure rate daily until the "
                "open-case level returns to normal."
            ),
        ],
    }


def build_product_complaint_recommendation(
    issue: pd.Series,
) -> dict:
    """Build a product-level complaint reduction recommendation."""

    return {
        "recommendation_title": (
            f"Investigate recurring product complaints: "
            f"{clean_text(issue['issue_title'])}"
        ),
        "suggested_owner_role": "Quality Assurance Manager",
        "base_deadline_days": 5,
        "expected_impact": (
            "Reduce repeated product complaints and identify whether "
            "quality, packaging, availability, or fulfilment is responsible."
        ),
        "action_steps": [
            (
                "Review the product's main complaint categories and "
                "high-severity cases."
            ),
            (
                "Inspect current inventory, packaging, handling, and "
                "supplier-quality records."
            ),
            (
                "Separate availability complaints from product-quality "
                "and service complaints."
            ),
            (
                "Define a corrective action and track complaint volume "
                "after implementation."
            ),
        ],
    }


def build_product_sales_recommendation(
    issue: pd.Series,
) -> dict:
    """Build a product commercial-performance recommendation."""

    return {
        "recommendation_title": (
            f"Improve product sales performance: "
            f"{clean_text(issue['issue_title'])}"
        ),
        "suggested_owner_role": "Category Manager",
        "base_deadline_days": 7,
        "expected_impact": (
            "Improve product revenue and identify whether demand, pricing, "
            "assortment, promotion, or availability is limiting performance."
        ),
        "action_steps": [
            (
                "Review recent product sales, margin, pricing, and "
                "promotion performance."
            ),
            (
                "Confirm whether stock availability is restricting sales."
            ),
            (
                "Compare product performance with category benchmarks and "
                "similar stores."
            ),
            (
                "Implement a targeted pricing, promotion, placement, or "
                "assortment action and measure the result."
            ),
        ],
    }


def build_overstock_recommendation(
    issue: pd.Series,
) -> dict:
    """Build an inventory overstock reduction recommendation."""

    return {
        "recommendation_title": (
            f"Reduce excess inventory exposure: "
            f"{clean_text(issue['issue_title'])}"
        ),
        "suggested_owner_role": "Inventory Planning Manager",
        "base_deadline_days": 7,
        "expected_impact": (
            "Release working capital, reduce storage pressure, and lower "
            "the risk of slow-moving or obsolete inventory."
        ),
        "action_steps": [
            (
                "Confirm current stock, recent sales velocity, and the "
                "latest replenishment orders."
            ),
            (
                "Pause or reduce additional replenishment until stock "
                "returns to the planned range."
            ),
            (
                "Evaluate stock transfer, promotion, bundling, or markdown "
                "options for excess quantity."
            ),
            (
                "Review the demand forecast and reorder parameters to "
                "prevent recurrence."
            ),
        ],
    }


def build_repeated_complaint_recommendation(
    issue: pd.Series,
) -> dict:
    """Build a systemic complaint-category recommendation."""

    return {
        "recommendation_title": (
            f"Correct recurring complaint pattern: "
            f"{clean_text(issue['issue_title'])}"
        ),
        "suggested_owner_role": "Customer Experience Manager",
        "base_deadline_days": 7,
        "expected_impact": (
            "Reduce repeated complaints by correcting the shared process, "
            "product, fulfilment, or service failure."
        ),
        "action_steps": [
            (
                "Review the affected stores, products, and customer cases "
                "linked to the complaint category."
            ),
            (
                "Map the operational process where the repeated failure "
                "is most likely occurring."
            ),
            (
                "Assign a corrective action to the responsible department "
                "and define a measurable closure target."
            ),
            (
                "Track the complaint category after implementation to "
                "confirm that recurrence is declining."
            ),
        ],
    }


def build_generic_recommendation(
    issue: pd.Series,
) -> dict:
    """Build a safe recommendation for an unsupported category."""

    return {
        "recommendation_title": (
            f"Review and address business risk: "
            f"{clean_text(issue['issue_title'])}"
        ),
        "suggested_owner_role": "Business Operations Manager",
        "base_deadline_days": 7,
        "expected_impact": (
            "Clarify the operational cause, assign accountability, and "
            "reduce the business exposure represented by the issue."
        ),
        "action_steps": [
            "Review the issue evidence and root-cause assessment.",
            "Validate the findings with the relevant business owner.",
            "Define a corrective action, accountable owner, and deadline.",
            "Track the issue until the agreed success measure is achieved.",
        ],
    }


def select_recommendation_template(
    issue: pd.Series,
) -> dict:
    """Select recommendation logic using current issue categories."""

    root_cause_category = clean_text(
        issue["root_cause_category"]
    )

    issue_type = clean_text(
        issue["issue_type"]
    )

    if (
        root_cause_category
        == "Inventory Replenishment and Supply Risk"
        or issue_type == "Product Availability Risk"
    ):
        return build_inventory_recommendation(issue)

    if (
        root_cause_category
        == "Multi-Factor Store Performance Deterioration"
        or issue_type == "Store Performance Risk"
    ):
        return build_store_performance_recommendation(issue)

    if (
        root_cause_category
        == "Vendor Reliability and Fulfilment Risk"
        or issue_type == "Vendor Performance Risk"
    ):
        return build_vendor_recommendation(issue)

    if (
        root_cause_category
        == "Customer Support Resolution and Escalation Backlog"
        or issue_type == "Complaint Resolution Backlog"
    ):
        return build_complaint_backlog_recommendation(issue)

    if (
        root_cause_category
        == "Product Quality, Availability, or Service Experience Risk"
        or issue_type == "Product Complaint Risk"
    ):
        return build_product_complaint_recommendation(issue)

    if (
        root_cause_category
        == "Product Demand and Commercial Performance Risk"
        or issue_type == "Product Sales Performance Risk"
    ):
        return build_product_sales_recommendation(issue)

    if (
        root_cause_category
        == "Inventory Planning and Demand Forecast Risk"
        or issue_type == "Inventory Overstock Risk"
    ):
        return build_overstock_recommendation(issue)

    if (
        root_cause_category
        == "Recurring Process or Product Failure Pattern"
        or issue_type == "Repeated Complaint Category Risk"
    ):
        return build_repeated_complaint_recommendation(issue)

    return build_generic_recommendation(issue)


def create_recommendation_record(
    issue: pd.Series,
) -> tuple[dict, dict]:
    """Create report and database records for one recommendation."""

    recommendation = select_recommendation_template(issue)

    priority_level = clean_text(
        issue["priority_level"]
    )

    deadline_days = adjust_deadline_days(
        recommendation["base_deadline_days"],
        priority_level,
    )

    suggested_deadline = date.today() + timedelta(
        days=deadline_days
    )

    recommendation_text = (
        f"Reason for action: "
        f"{clean_text(issue['root_cause_summary'])} "
        f"Recommended action steps: "
        f"{format_action_steps(recommendation['action_steps'])}"
    )

    confidence_score = calculate_recommendation_confidence(
        issue
    )

    generated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    output_record = {
        "executive_rank": safe_int(
            issue["executive_rank"]
        ),
        "issue_id": clean_text(
            issue["issue_id"]
        ),
        "issue_title": clean_text(
            issue["issue_title"]
        ),
        "issue_type": clean_text(
            issue["issue_type"]
        ),
        "business_area": clean_text(
            issue["business_area"]
        ),
        "priority_level": priority_level,
        "priority_score": optional_float(
            issue["priority_score"]
        ),
        "executive_score": optional_float(
            issue["executive_score"]
        ),
        "root_cause_category": clean_text(
            issue["root_cause_category"]
        ),
        "root_cause_summary": clean_text(
            issue["root_cause_summary"]
        ),
        "root_cause_confidence_score": optional_float(
            issue["root_cause_confidence_score"]
        ),
        "recommendation_title": clean_text(
            recommendation["recommendation_title"]
        ),
        "recommendation_text": recommendation_text,
        "suggested_owner_role": clean_text(
            recommendation["suggested_owner_role"]
        ),
        "suggested_deadline": suggested_deadline.isoformat(),
        "expected_impact": clean_text(
            recommendation["expected_impact"]
        ),
        "confidence_score": confidence_score,
        "status": "Pending Review",
        "generated_at": generated_at,
    }

    database_record = {
        "issue_id": output_record["issue_id"],
        "recommendation_title": output_record[
            "recommendation_title"
        ],
        "recommendation_text": output_record[
            "recommendation_text"
        ],
        "suggested_owner_role": output_record[
            "suggested_owner_role"
        ],
        "suggested_deadline": suggested_deadline,
        "expected_impact": output_record[
            "expected_impact"
        ],
        "confidence_score": confidence_score,
    }

    return output_record, database_record


def build_recommendations(
    recommendation_context: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict]]:
    """Generate recommendations for selected executive issues."""

    output_records = []
    database_records = []

    for _, issue in recommendation_context.iterrows():
        print(
            f"Generating recommendation for "
            f"{clean_text(issue['issue_id'])}..."
        )

        output_record, database_record = (
            create_recommendation_record(issue)
        )

        output_records.append(output_record)
        database_records.append(database_record)

    recommendations_dataframe = pd.DataFrame(
        output_records,
        columns=OUTPUT_COLUMNS,
    )

    return (
        recommendations_dataframe.sort_values(
            by="executive_rank"
        ).reset_index(drop=True),
        database_records,
    )


CHECK_REVIEWED_RECOMMENDATION_SQL = text(
    """
    SELECT COUNT(*)
    FROM recommendations
    WHERE
        issue_id = :issue_id
        AND status IN (
            'Accepted',
            'Edited',
            'Converted to Task'
        );
    """
)

DELETE_REGENERATABLE_RECOMMENDATIONS_SQL = text(
    """
    DELETE FROM recommendations
    WHERE
        issue_id = :issue_id
        AND status IN (
            'Pending Review',
            'Rejected'
        );
    """
)

INSERT_RECOMMENDATION_SQL = text(
    """
    INSERT INTO recommendations (
        issue_id,
        recommendation_title,
        recommendation_text,
        suggested_owner_role,
        suggested_deadline,
        expected_impact,
        confidence_score,
        status,
        created_at,
        updated_at
    )
    VALUES (
        :issue_id,
        :recommendation_title,
        :recommendation_text,
        :suggested_owner_role,
        :suggested_deadline,
        :expected_impact,
        :confidence_score,
        'Pending Review',
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP
    );
    """
)


def save_recommendations_to_database(
    engine: Engine,
    database_records: list[dict],
) -> tuple[int, int]:
    """
    Store proposed recommendations in PostgreSQL.

    Pending and rejected recommendations may be regenerated.
    Accepted, edited, and task-converted recommendations are preserved.
    """

    inserted_count = 0
    preserved_count = 0

    with engine.begin() as connection:
        for record in database_records:
            reviewed_count = connection.execute(
                CHECK_REVIEWED_RECOMMENDATION_SQL,
                {"issue_id": record["issue_id"]},
            ).scalar_one()

            if reviewed_count > 0:
                preserved_count += 1

                print(
                    "Preserving reviewed recommendation for "
                    f"{record['issue_id']}."
                )

                continue

            connection.execute(
                DELETE_REGENERATABLE_RECOMMENDATIONS_SQL,
                {"issue_id": record["issue_id"]},
            )

            connection.execute(
                INSERT_RECOMMENDATION_SQL,
                record,
            )

            inserted_count += 1

    return inserted_count, preserved_count


def create_markdown_report(
    recommendations: pd.DataFrame,
) -> str:
    """Create a readable Markdown recommendation report."""

    generated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    lines = [
        "# Executive Recommendation Report",
        "",
        "## AI-Powered Operating Intelligence Platform",
        "",
        f"**Generated At:** {generated_at}",
        "",
        (
            "This report converts current executive-priority issues and "
            "their root-cause analyses into proposed management actions. "
            "Every recommendation requires human review before being "
            "accepted, edited, rejected, or converted into a task."
        ),
        "",
        "## Recommendation Summary",
        "",
        f"- Recommendations Generated: {len(recommendations)}",
        "- Initial Status: Pending Review",
        "",
    ]

    if recommendations.empty:
        lines.extend(
            [
                "No executive recommendations were generated.",
                "",
            ]
        )

        return "\n".join(lines)

    lines.extend(
        [
            "## Executive Recommendation Overview",
            "",
            (
                "| Rank | Issue | Recommended Owner | Deadline | "
                "Confidence |"
            ),
            "|---:|---|---|---|---:|",
        ]
    )

    for row in recommendations.itertuples(index=False):
        lines.append(
            f"| {safe_int(row.executive_rank)} | "
            f"{clean_text(row.issue_title).replace('|', '/')} | "
            f"{clean_text(row.suggested_owner_role)} | "
            f"{clean_text(row.suggested_deadline)} | "
            f"{safe_float(row.confidence_score):.2f}% |"
        )

    lines.extend(
        [
            "",
            "## Detailed Recommendations",
            "",
        ]
    )

    for row in recommendations.itertuples(index=False):
        lines.extend(
            [
                (
                    f"### {safe_int(row.executive_rank)}. "
                    f"{clean_text(row.recommendation_title)}"
                ),
                "",
                f"**Issue ID:** {clean_text(row.issue_id)}",
                "",
                f"**Issue:** {clean_text(row.issue_title)}",
                "",
                (
                    f"**Priority:** {clean_text(row.priority_level)} "
                    f"({safe_float(row.priority_score):.2f})"
                ),
                "",
                (
                    f"**Root Cause:** "
                    f"{clean_text(row.root_cause_summary)}"
                ),
                "",
                (
                    f"**Recommendation:** "
                    f"{clean_text(row.recommendation_text)}"
                ),
                "",
                (
                    f"**Suggested Owner:** "
                    f"{clean_text(row.suggested_owner_role)}"
                ),
                "",
                (
                    f"**Suggested Deadline:** "
                    f"{clean_text(row.suggested_deadline)}"
                ),
                "",
                (
                    f"**Expected Impact:** "
                    f"{clean_text(row.expected_impact)}"
                ),
                "",
                (
                    f"**Recommendation Confidence:** "
                    f"{safe_float(row.confidence_score):.2f}%"
                ),
                "",
                "**Review Status:** Pending Review",
                "",
            ]
        )

    return "\n".join(lines)


def print_recommendation_preview(
    recommendations: pd.DataFrame,
) -> None:
    """Print a compact recommendation preview."""

    print("\nRecommendation Preview:")

    if recommendations.empty:
        print("No recommendations were generated.")
        return

    preview_columns = [
        "executive_rank",
        "suggested_owner_role",
        "suggested_deadline",
        "confidence_score",
        "recommendation_title",
    ]

    print(
        recommendations[preview_columns].to_string(index=False)
    )


def main() -> None:
    """Generate recommendations for current executive priorities."""

    parser = argparse.ArgumentParser(
        description=(
            "Generate management recommendations from current "
            "executive issues and root-cause analyses."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum executive issues to process. Default: 10.",
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
        "Executive issues selected for recommendations: "
        f"{len(priority_reference)}"
    )

    print("Connecting to PostgreSQL database...")

    engine = get_database_engine()

    try:
        print("Loading issues and root-cause analyses...")

        recommendation_context = load_recommendation_context(
            engine,
            priority_reference,
        )

        if recommendation_context.empty:
            raise ValueError(
                "No eligible root-cause analyses matched the "
                "executive priority list. Run root_cause_analysis first."
            )

        print("Generating management recommendations...")

        recommendations_dataframe, database_records = (
            build_recommendations(recommendation_context)
        )

        print("Saving recommendations to PostgreSQL...")

        inserted_count, preserved_count = (
            save_recommendations_to_database(
                engine,
                database_records,
            )
        )

        csv_output_path = (
            REPORTS_DIRECTORY / "recommendations.csv"
        )

        markdown_output_path = (
            REPORTS_DIRECTORY / "recommendations_report.md"
        )

        recommendations_dataframe.to_csv(
            csv_output_path,
            index=False,
        )

        markdown_output_path.write_text(
            create_markdown_report(
                recommendations_dataframe
            ),
            encoding="utf-8",
        )

        print("\nRecommendation Engine completed successfully.")

        print(
            f"Recommendations generated: "
            f"{len(recommendations_dataframe)}"
        )

        print(
            f"Recommendations inserted or refreshed: "
            f"{inserted_count}"
        )

        print(
            f"Reviewed recommendations preserved: "
            f"{preserved_count}"
        )

        print("PostgreSQL table updated: recommendations")

        print_recommendation_preview(
            recommendations_dataframe
        )

        print(f"\nCSV report saved at: {csv_output_path}")
        print(
            f"Markdown report saved at: "
            f"{markdown_output_path}"
        )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
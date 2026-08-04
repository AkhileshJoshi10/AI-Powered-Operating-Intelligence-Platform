from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

from backend.analytics.complaint_analysis import (
    run_complaint_analysis,
)
from backend.analytics.executive_priority_selector import (
    load_active_issues,
    select_executive_priorities,
)
from backend.analytics.inventory_analysis import (
    run_inventory_analysis,
)
from backend.analytics.manager_priority_list import (
    load_active_issue_summary,
    load_manager_priorities,
)
from backend.analytics.priority_engine import (
    COMMON_COLUMNS,
    build_priority_outputs,
    save_to_database,
)
from backend.analytics.sales_analysis import (
    run_sales_analysis,
)
from backend.app.agents.agent_context import AgentContext
from backend.app.agents.base_agent import BaseAgent
from backend.app.db.database import engine
from backend.app.services.vendor_finance_analytics_service import (
    run_finance_analysis,
    run_vendor_analysis,
)


DEFAULT_MANAGER_LIMIT = 15
DEFAULT_EXECUTIVE_LIMIT = 10

MAXIMUM_MANAGER_LIMIT = 100
MAXIMUM_EXECUTIVE_LIMIT = 50


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def get_positive_limit(
    context: AgentContext,
    *,
    setting_name: str,
    default_value: int,
    maximum_value: int,
) -> int:
    """Read and validate a positive integer limit."""

    configured_value = context.input_data.get(
        setting_name,
        default_value,
    )

    if isinstance(configured_value, bool):
        raise ValueError(
            f"{setting_name} must be an integer."
        )

    try:
        limit = int(configured_value)

    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{setting_name} must be an integer."
        ) from error

    if limit < 1:
        raise ValueError(
            f"{setting_name} must be at least 1."
        )

    if limit > maximum_value:
        raise ValueError(
            f"{setting_name} cannot be greater than "
            f"{maximum_value}."
        )

    return limit


def normalize_findings(
    *,
    findings: pd.DataFrame,
    source_module: str,
    source_report: str,
) -> pd.DataFrame:
    """
    Normalize one analytics DataFrame for the existing priority engine.

    Missing common columns are added without changing the underlying
    analytics findings.
    """

    if not isinstance(findings, pd.DataFrame):
        raise TypeError(
            f"{source_module} analytics must return a DataFrame."
        )

    normalized_findings = findings.copy()

    for column_name in COMMON_COLUMNS:
        if column_name not in normalized_findings.columns:
            normalized_findings[column_name] = None

    normalized_findings = normalized_findings[
        COMMON_COLUMNS
    ].copy()

    normalized_findings["source_module"] = source_module
    normalized_findings["source_report"] = source_report

    return normalized_findings


def build_detailed_findings(
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Run all deterministic analytics and build the priority input.

    This avoids depending on previously generated CSV report files.
    """

    sales_findings = normalize_findings(
        findings=run_sales_analysis(engine),
        source_module="sales",
        source_report="sales_analysis.csv",
    )

    inventory_findings = normalize_findings(
        findings=run_inventory_analysis(engine),
        source_module="inventory",
        source_report="inventory_analysis.csv",
    )

    complaint_findings = normalize_findings(
        findings=run_complaint_analysis(engine),
        source_module="complaints",
        source_report="complaint_analysis.csv",
    )

    vendor_findings = normalize_findings(
        findings=run_vendor_analysis(),
        source_module="vendors",
        source_report="vendor_finance_analysis.csv",
    )

    finance_findings = normalize_findings(
        findings=run_finance_analysis(),
        source_module="finance",
        source_report="vendor_finance_analysis.csv",
    )

    source_dataframes = {
        "sales": sales_findings,
        "inventory": inventory_findings,
        "complaints": complaint_findings,
        "vendors": vendor_findings,
        "finance": finance_findings,
    }

    source_finding_counts = {
        source_name: len(source_dataframe)
        for source_name, source_dataframe
        in source_dataframes.items()
    }

    detailed_findings = pd.concat(
        list(source_dataframes.values()),
        ignore_index=True,
    )

    return detailed_findings, source_finding_counts


def clean_scalar(value: object) -> object:
    """Convert pandas and NumPy scalar values to JSON-safe values."""

    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    try:
        missing_result = pd.isna(value)

        if isinstance(missing_result, bool) and missing_result:
            return None

    except (TypeError, ValueError):
        pass

    item_method = getattr(
        value,
        "item",
        None,
    )

    if callable(item_method):
        try:
            return item_method()
        except (TypeError, ValueError):
            pass

    return value


def dataframe_to_records(
    dataframe: pd.DataFrame,
) -> list[dict[str, object]]:
    """Convert a DataFrame into JSON-safe records."""

    records: list[dict[str, object]] = []

    for record in dataframe.to_dict(
        orient="records"
    ):
        cleaned_record = {
            str(key): clean_scalar(value)
            for key, value in record.items()
        }

        records.append(cleaned_record)

    return records


def build_priority_counts(
    issues_dataframe: pd.DataFrame,
) -> dict[str, int]:
    """Build issue counts for High, Medium, and Low priorities."""

    priority_counts = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }

    if issues_dataframe.empty:
        return priority_counts

    calculated_counts = (
        issues_dataframe.groupby(
            "priority_level"
        )
        .size()
        .to_dict()
    )

    for priority_level, issue_count in (
        calculated_counts.items()
    ):
        priority_counts[
            str(priority_level)
        ] = int(issue_count)

    return priority_counts


def build_active_issue_counts(
    active_issue_summary: pd.DataFrame,
) -> dict[str, int]:
    """Convert the active-issue summary into a dictionary."""

    active_issue_counts = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }

    if active_issue_summary.empty:
        return active_issue_counts

    for row in active_issue_summary.itertuples(
        index=False
    ):
        priority_level = str(
            row.priority_level
        )

        active_issue_counts[
            priority_level
        ] = int(row.issue_count)

    return active_issue_counts


def get_previous_monitoring_total(
    context: AgentContext,
) -> int | None:
    """Read the Monitoring Agent total when run in a sequence."""

    previous_results = context.metadata.get(
        "previous_agent_results",
        {},
    )

    if not isinstance(previous_results, dict):
        return None

    monitoring_result = previous_results.get(
        "Monitoring Agent"
    )

    if not isinstance(monitoring_result, dict):
        return None

    output_data = monitoring_result.get(
        "output_data",
        {},
    )

    if not isinstance(output_data, dict):
        return None

    finding_totals = output_data.get(
        "finding_totals",
        {},
    )

    if not isinstance(finding_totals, dict):
        return None

    total_value = finding_totals.get(
        "total"
    )

    if total_value is None:
        return None

    try:
        return int(total_value)

    except (TypeError, ValueError):
        return None


class PriorityAgent(BaseAgent):
    """
    Consolidate business findings into prioritized issues.

    The agent reuses the existing deterministic priority engine,
    PostgreSQL issue register, manager selection, and executive
    evidence-ranking logic.
    """

    name = "Priority Agent"

    description = (
        "Consolidates deterministic business findings into issues, "
        "stores supporting evidence, and selects manager and "
        "executive priorities."
    )

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        """Run the deterministic priority-management pipeline."""

        manager_limit = get_positive_limit(
            context,
            setting_name="manager_limit",
            default_value=DEFAULT_MANAGER_LIMIT,
            maximum_value=MAXIMUM_MANAGER_LIMIT,
        )

        executive_limit = get_positive_limit(
            context,
            setting_name="executive_limit",
            default_value=DEFAULT_EXECUTIVE_LIMIT,
            maximum_value=MAXIMUM_EXECUTIVE_LIMIT,
        )

        detailed_findings, source_finding_counts = (
            build_detailed_findings()
        )

        issues_dataframe, evidence_dataframe = (
            build_priority_outputs(
                detailed_findings
            )
        )

        if issues_dataframe.empty:
            raise RuntimeError(
                "The priority engine did not create any issues."
            )

        save_to_database(
            engine,
            issues_dataframe,
            evidence_dataframe,
        )

        manager_priorities = load_manager_priorities(
            engine,
            manager_limit,
        )

        active_issue_summary = (
            load_active_issue_summary(
                engine
            )
        )

        active_issues = load_active_issues(
            engine
        )

        executive_priorities = (
            select_executive_priorities(
                active_issues=active_issues,
                limit=executive_limit,
            )
        )

        total_findings = len(
            detailed_findings
        )

        total_issues = len(
            issues_dataframe
        )

        total_evidence_records = len(
            evidence_dataframe
        )

        priority_counts = build_priority_counts(
            issues_dataframe
        )

        active_issue_counts = (
            build_active_issue_counts(
                active_issue_summary
            )
        )

        previous_monitoring_total = (
            get_previous_monitoring_total(
                context
            )
        )

        monitoring_comparison = {
            "available": (
                previous_monitoring_total
                is not None
            ),
            "monitoring_finding_total": (
                previous_monitoring_total
            ),
            "priority_input_finding_total": (
                total_findings
            ),
            "totals_match": (
                previous_monitoring_total
                == total_findings
                if previous_monitoring_total
                is not None
                else None
            ),
        }

        summary = (
            f"Priority analysis consolidated "
            f"{total_findings} findings into "
            f"{total_issues} business issues: "
            f"{priority_counts['High']} High, "
            f"{priority_counts['Medium']} Medium, and "
            f"{priority_counts['Low']} Low. "
            f"{len(executive_priorities)} executive "
            "priorities were selected."
        )

        return {
            "summary": summary,
            "priority_status": "Complete",
            "generated_at": current_utc_time(),
            "database_persisted": True,
            "detailed_findings": {
                "total": total_findings,
                "by_source": source_finding_counts,
            },
            "issues": {
                "total_created": total_issues,
                "by_priority": priority_counts,
                "active_by_priority": (
                    active_issue_counts
                ),
            },
            "evidence_records": {
                "total": total_evidence_records,
            },
            "manager_priorities": {
                "requested_limit": manager_limit,
                "returned_count": len(
                    manager_priorities
                ),
                "items": dataframe_to_records(
                    manager_priorities
                ),
            },
            "executive_priorities": {
                "requested_limit": executive_limit,
                "returned_count": len(
                    executive_priorities
                ),
                "items": dataframe_to_records(
                    executive_priorities
                ),
            },
            "monitoring_comparison": (
                monitoring_comparison
            ),
        }
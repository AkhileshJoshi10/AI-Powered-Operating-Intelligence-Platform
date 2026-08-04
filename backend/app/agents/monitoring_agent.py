from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from backend.app.agents.agent_context import AgentContext
from backend.app.agents.base_agent import BaseAgent
from backend.app.services.complaint_analytics_service import (
    get_complaint_analytics,
)
from backend.app.services.inventory_analytics_service import (
    get_inventory_analytics,
)
from backend.app.services.kpi_service import get_kpi_response
from backend.app.services.sales_analytics_service import (
    get_sales_analytics,
)
from backend.app.services.vendor_finance_analytics_service import (
    get_finance_analytics,
    get_vendor_analytics,
)


DEFAULT_FINDING_LIMIT = 10
MAXIMUM_FINDING_LIMIT = 100

SEVERITY_ORDER = {
    "High": 1,
    "Medium": 2,
    "Low": 3,
}

SOURCE_ORDER = {
    "sales": 1,
    "inventory": 2,
    "complaints": 3,
    "vendors": 4,
    "finance": 5,
}


ServiceFunction = Callable[..., dict[str, Any]]


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def clean_text(value: object) -> str:
    """Convert a value into normalized text."""

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def get_finding_limit(
    context: AgentContext,
) -> int:
    """
    Read the optional finding limit from the agent context.

    The complete finding totals remain available even though only a
    controlled number of detailed records are returned per source.
    """

    configured_value = context.input_data.get(
        "finding_limit",
        DEFAULT_FINDING_LIMIT,
    )

    if isinstance(configured_value, bool):
        raise ValueError(
            "finding_limit must be an integer."
        )

    try:
        finding_limit = int(
            configured_value
        )

    except (TypeError, ValueError) as error:
        raise ValueError(
            "finding_limit must be an integer."
        ) from error

    if finding_limit < 1:
        raise ValueError(
            "finding_limit must be at least 1."
        )

    if finding_limit > MAXIMUM_FINDING_LIMIT:
        raise ValueError(
            "finding_limit cannot be greater than "
            f"{MAXIMUM_FINDING_LIMIT}."
        )

    return finding_limit


def execute_service(
    *,
    source_name: str,
    service_function: ServiceFunction,
    parameters: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    """
    Execute one monitoring service safely.

    A single service failure is returned as structured information so
    other monitoring sources can still complete.
    """

    try:
        if parameters is None:
            response = service_function()
        else:
            response = service_function(
                **parameters
            )

        if not isinstance(response, dict):
            raise TypeError(
                f"{source_name} service output must be "
                "a dictionary."
            )

        return response, None

    except Exception as error:
        error_message = clean_text(
            error
        )

        if not error_message:
            error_message = type(
                error
            ).__name__

        return (
            None,
            {
                "source": source_name,
                "error_type": type(
                    error
                ).__name__,
                "error_message": error_message,
            },
        )


def build_severity_counts(
    summary_records: list[dict[str, Any]],
) -> dict[str, int]:
    """Build severity totals from an analytics summary."""

    severity_counts = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }

    for summary_record in summary_records:
        severity = clean_text(
            summary_record.get(
                "severity"
            )
        )

        try:
            finding_count = int(
                summary_record.get(
                    "finding_count",
                    0,
                )
            )

        except (TypeError, ValueError):
            finding_count = 0

        if severity:
            severity_counts.setdefault(
                severity,
                0,
            )

            severity_counts[
                severity
            ] += finding_count

    return severity_counts


def build_compact_finding(
    *,
    source_name: str,
    finding: dict[str, Any],
) -> dict[str, Any]:
    """Create a common compact structure for one finding."""

    return {
        "source": source_name,
        "finding_id": clean_text(
            finding.get(
                "finding_id"
            )
        ),
        "analysis_type": clean_text(
            finding.get(
                "analysis_type"
            )
        ),
        "business_area": clean_text(
            finding.get(
                "business_area"
            )
        ),
        "severity": clean_text(
            finding.get(
                "severity"
            )
        ),
        "entity_type": clean_text(
            finding.get(
                "entity_type"
            )
        ),
        "entity_id": clean_text(
            finding.get(
                "entity_id"
            )
        ),
        "summary": clean_text(
            finding.get(
                "summary"
            )
        ),
        "evidence": clean_text(
            finding.get(
                "evidence"
            )
        ),
    }


def build_analytics_snapshot(
    *,
    source_name: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    """Convert one analytics service response into a snapshot."""

    raw_summary = response.get(
        "summary",
        [],
    )

    if not isinstance(
        raw_summary,
        list,
    ):
        raw_summary = []

    raw_findings = response.get(
        "findings",
        [],
    )

    if not isinstance(
        raw_findings,
        list,
    ):
        raw_findings = []

    try:
        total_findings = int(
            response.get(
                "total_findings",
                0,
            )
        )

    except (TypeError, ValueError):
        total_findings = 0

    try:
        matching_findings = int(
            response.get(
                "matching_findings",
                total_findings,
            )
        )

    except (TypeError, ValueError):
        matching_findings = total_findings

    compact_findings = [
        build_compact_finding(
            source_name=source_name,
            finding=finding,
        )
        for finding in raw_findings
        if isinstance(
            finding,
            dict,
        )
    ]

    return {
        "source": source_name,
        "status": clean_text(
            response.get(
                "status",
                "success",
            )
        ),
        "generated_at": response.get(
            "generated_at"
        ),
        "total_findings": total_findings,
        "matching_findings": matching_findings,
        "severity_counts": build_severity_counts(
            raw_summary
        ),
        "summary": raw_summary,
        "findings": compact_findings,
    }


def build_monitoring_summary(
    *,
    total_kpis: int,
    total_findings: int,
    severity_counts: dict[str, int],
    failed_sources: list[dict[str, str]],
) -> str:
    """Build the human-readable Monitoring Agent summary."""

    summary = (
        f"Monitoring completed with {total_kpis} KPIs and "
        f"{total_findings} business findings: "
        f"{severity_counts.get('High', 0)} High, "
        f"{severity_counts.get('Medium', 0)} Medium, and "
        f"{severity_counts.get('Low', 0)} Low."
    )

    if failed_sources:
        failed_source_names = ", ".join(
            failure["source"]
            for failure in failed_sources
        )

        summary += (
            " Partial monitoring was returned because these "
            f"sources failed: {failed_source_names}."
        )

    return summary


class MonitoringAgent(BaseAgent):
    """
    Monitor KPIs and deterministic business analytics.

    This agent consolidates existing services into one structured
    operational snapshot. It does not use an LLM.
    """

    name = "Monitoring Agent"

    description = (
        "Collects business KPIs and analytics findings across "
        "sales, inventory, complaints, vendors, and finance."
    )

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        """Generate the current business-monitoring snapshot."""

        finding_limit = get_finding_limit(
            context
        )

        successful_sources: list[str] = []
        failed_sources: list[
            dict[str, str]
        ] = []

        kpi_snapshot: dict[str, Any] | None = None
        analytics_snapshot: dict[
            str,
            dict[str, Any],
        ] = {}

        kpi_response, kpi_error = execute_service(
            source_name="kpis",
            service_function=get_kpi_response,
        )

        if kpi_response is not None:
            successful_sources.append(
                "kpis"
            )

            kpi_snapshot = {
                "status": clean_text(
                    kpi_response.get(
                        "status",
                        "success",
                    )
                ),
                "total_kpis": int(
                    kpi_response.get(
                        "total_kpis",
                        0,
                    )
                ),
                "kpis": kpi_response.get(
                    "kpis",
                    [],
                ),
                "latest_store_target_achievement": (
                    kpi_response.get(
                        "latest_store_target_achievement",
                        [],
                    )
                ),
            }

        elif kpi_error is not None:
            failed_sources.append(
                kpi_error
            )

        analytics_services: list[
            tuple[
                str,
                ServiceFunction,
                dict[str, Any],
            ]
        ] = [
            (
                "sales",
                get_sales_analytics,
                {
                    "severity": None,
                    "analysis_type": None,
                    "limit": finding_limit,
                    "offset": 0,
                },
            ),
            (
                "inventory",
                get_inventory_analytics,
                {
                    "severity": None,
                    "analysis_type": None,
                    "store_id": None,
                    "product_id": None,
                    "vendor_id": None,
                    "limit": finding_limit,
                    "offset": 0,
                },
            ),
            (
                "complaints",
                get_complaint_analytics,
                {
                    "severity": None,
                    "analysis_type": None,
                    "store_id": None,
                    "product_id": None,
                    "region": None,
                    "complaint_type": None,
                    "complaint_status": None,
                    "limit": finding_limit,
                    "offset": 0,
                },
            ),
            (
                "vendors",
                get_vendor_analytics,
                {
                    "severity": None,
                    "analysis_type": None,
                    "vendor_id": None,
                    "limit": finding_limit,
                    "offset": 0,
                },
            ),
            (
                "finance",
                get_finance_analytics,
                {
                    "severity": None,
                    "analysis_type": None,
                    "store_id": None,
                    "month": None,
                    "risk_status": None,
                    "limit": finding_limit,
                    "offset": 0,
                },
            ),
        ]

        for (
            source_name,
            service_function,
            service_parameters,
        ) in analytics_services:
            response, error = execute_service(
                source_name=source_name,
                service_function=service_function,
                parameters=service_parameters,
            )

            if response is not None:
                successful_sources.append(
                    source_name
                )

                analytics_snapshot[
                    source_name
                ] = build_analytics_snapshot(
                    source_name=source_name,
                    response=response,
                )

            elif error is not None:
                failed_sources.append(
                    error
                )

        if not successful_sources:
            failed_source_names = ", ".join(
                failure["source"]
                for failure in failed_sources
            )

            raise RuntimeError(
                "All monitoring sources failed: "
                f"{failed_source_names}."
            )

        finding_totals_by_source = {
            source_name: source_snapshot[
                "total_findings"
            ]
            for (
                source_name,
                source_snapshot,
            ) in analytics_snapshot.items()
        }

        total_findings = sum(
            finding_totals_by_source.values()
        )

        combined_severity_counts = {
            "High": 0,
            "Medium": 0,
            "Low": 0,
        }

        compact_findings: list[
            dict[str, Any]
        ] = []

        for source_snapshot in (
            analytics_snapshot.values()
        ):
            for (
                severity,
                finding_count,
            ) in source_snapshot[
                "severity_counts"
            ].items():
                combined_severity_counts.setdefault(
                    severity,
                    0,
                )

                combined_severity_counts[
                    severity
                ] += int(
                    finding_count
                )

            compact_findings.extend(
                source_snapshot[
                    "findings"
                ]
            )

        compact_findings.sort(
            key=lambda finding: (
                SEVERITY_ORDER.get(
                    finding.get(
                        "severity",
                        "",
                    ),
                    99,
                ),
                SOURCE_ORDER.get(
                    finding.get(
                        "source",
                        "",
                    ),
                    99,
                ),
                finding.get(
                    "analysis_type",
                    "",
                ),
                finding.get(
                    "finding_id",
                    "",
                ),
            )
        )

        total_kpis = (
            int(
                kpi_snapshot[
                    "total_kpis"
                ]
            )
            if kpi_snapshot is not None
            else 0
        )

        monitoring_status = (
            "Complete"
            if not failed_sources
            else "Partial"
        )

        summary = build_monitoring_summary(
            total_kpis=total_kpis,
            total_findings=total_findings,
            severity_counts=(
                combined_severity_counts
            ),
            failed_sources=failed_sources,
        )

        return {
            "summary": summary,
            "monitoring_status": monitoring_status,
            "snapshot_generated_at": (
                current_utc_time()
            ),
            "finding_limit_per_source": (
                finding_limit
            ),
            "successful_sources": (
                successful_sources
            ),
            "failed_sources": failed_sources,
            "kpi_snapshot": kpi_snapshot,
            "analytics_snapshot": (
                analytics_snapshot
            ),
            "finding_totals": {
                "total": total_findings,
                "by_source": (
                    finding_totals_by_source
                ),
                "by_severity": (
                    combined_severity_counts
                ),
            },
            "top_findings": compact_findings[
                :finding_limit
            ],
        }
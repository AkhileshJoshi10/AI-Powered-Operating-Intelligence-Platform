from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from backend.app.agents.agent_context import AgentContext
from backend.app.agents.base_agent import BaseAgent
from backend.app.agents.llm_enhancement import (
    MonitoringSummaryV1,
    attach_deterministic_fallback,
    build_attached_fallback_output,
    build_failed_execution_metadata,
    run_structured_enhancement,
)
from backend.app.core.config import settings
from backend.app.llm import (
    BaseLLMProvider,
    LLMError,
    get_configured_provider,
)
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

MONITORING_PROMPT_NAME = "monitoring_summary"
MONITORING_PROMPT_VERSION = "v1"

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


ServiceFunction = Callable[
    ...,
    dict[str, Any],
]


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(
        timezone.utc
    )


def clean_text(
    value: object,
) -> str:
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

    if isinstance(
        configured_value,
        bool,
    ):
        raise ValueError(
            "finding_limit must be an integer."
        )

    try:
        finding_limit = int(
            configured_value
        )

    except (
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "finding_limit must be an integer."
        ) from error

    if finding_limit < 1:
        raise ValueError(
            "finding_limit must be at least 1."
        )

    if (
        finding_limit
        > MAXIMUM_FINDING_LIMIT
    ):
        raise ValueError(
            "finding_limit cannot be greater than "
            f"{MAXIMUM_FINDING_LIMIT}."
        )

    return finding_limit


def execute_service(
    *,
    source_name: str,
    service_function: ServiceFunction,
    parameters: dict[
        str,
        Any,
    ] | None = None,
) -> tuple[
    dict[str, Any] | None,
    dict[str, str] | None,
]:
    """
    Execute one monitoring service safely.

    A single service failure is returned as structured information so
    other monitoring sources can still complete.
    """

    try:
        if parameters is None:
            response = (
                service_function()
            )
        else:
            response = (
                service_function(
                    **parameters
                )
            )

        if not isinstance(
            response,
            dict,
        ):
            raise TypeError(
                f"{source_name} service output must be "
                "a dictionary."
            )

        return (
            response,
            None,
        )

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
                "source": (
                    source_name
                ),
                "error_type": type(
                    error
                ).__name__,
                "error_message": (
                    error_message
                ),
            },
        )


def build_severity_counts(
    summary_records: list[
        dict[str, Any]
    ],
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

        except (
            TypeError,
            ValueError,
        ):
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

    except (
        TypeError,
        ValueError,
    ):
        total_findings = 0

    try:
        matching_findings = int(
            response.get(
                "matching_findings",
                total_findings,
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        matching_findings = (
            total_findings
        )

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
        "total_findings": (
            total_findings
        ),
        "matching_findings": (
            matching_findings
        ),
        "severity_counts": (
            build_severity_counts(
                raw_summary
            )
        ),
        "summary": raw_summary,
        "findings": (
            compact_findings
        ),
    }


def build_monitoring_summary(
    *,
    total_kpis: int,
    total_findings: int,
    severity_counts: dict[str, int],
    failed_sources: list[
        dict[str, str]
    ],
) -> str:
    """Build the deterministic Monitoring Agent summary."""

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


def build_deterministic_monitoring_output(
    context: AgentContext,
) -> dict[str, Any]:
    """Generate the complete deterministic monitoring snapshot."""

    finding_limit = get_finding_limit(
        context
    )

    successful_sources: list[str] = []
    failed_sources: list[
        dict[str, str]
    ] = []

    kpi_snapshot: (
        dict[str, Any]
        | None
    ) = None

    analytics_snapshot: dict[
        str,
        dict[str, Any],
    ] = {}

    (
        kpi_response,
        kpi_error,
    ) = execute_service(
        source_name="kpis",
        service_function=(
            get_kpi_response
        ),
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
        (
            response,
            error,
        ) = execute_service(
            source_name=source_name,
            service_function=(
                service_function
            ),
            parameters=(
                service_parameters
            ),
        )

        if response is not None:
            successful_sources.append(
                source_name
            )

            analytics_snapshot[
                source_name
            ] = (
                build_analytics_snapshot(
                    source_name=(
                        source_name
                    ),
                    response=response,
                )
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
        source_name: (
            source_snapshot[
                "total_findings"
            ]
        )
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
        if (
            kpi_snapshot
            is not None
        )
        else 0
    )

    monitoring_status = (
        "Complete"
        if not failed_sources
        else "Partial"
    )

    summary = build_monitoring_summary(
        total_kpis=total_kpis,
        total_findings=(
            total_findings
        ),
        severity_counts=(
            combined_severity_counts
        ),
        failed_sources=(
            failed_sources
        ),
    )

    return {
        "summary": summary,
        "monitoring_status": (
            monitoring_status
        ),
        "snapshot_generated_at": (
            current_utc_time()
        ),
        "finding_limit_per_source": (
            finding_limit
        ),
        "successful_sources": (
            successful_sources
        ),
        "failed_sources": (
            failed_sources
        ),
        "kpi_snapshot": (
            kpi_snapshot
        ),
        "analytics_snapshot": (
            analytics_snapshot
        ),
        "finding_totals": {
            "total": (
                total_findings
            ),
            "by_source": (
                finding_totals_by_source
            ),
            "by_severity": (
                combined_severity_counts
            ),
        },
        "top_findings": (
            compact_findings[
                :finding_limit
            ]
        ),
    }


def compact_kpi_record(
    kpi: dict[str, Any],
) -> dict[str, Any]:
    """Keep only validated KPI fields needed for summarization."""

    allowed_fields = (
        "kpi_key",
        "kpi_name",
        "value",
        "display_value",
        "unit",
        "reference_period",
        "description",
    )

    return {
        field_name: kpi.get(
            field_name
        )
        for field_name in allowed_fields
    }


def build_monitoring_llm_context(
    deterministic_output: dict[
        str,
        Any,
    ],
) -> dict[str, Any]:
    """Create a compact evidence-grounded context for the LLM."""

    kpi_snapshot = (
        deterministic_output.get(
            "kpi_snapshot"
        )
        or {}
    )

    raw_kpis = kpi_snapshot.get(
        "kpis",
        [],
    )

    if not isinstance(
        raw_kpis,
        list,
    ):
        raw_kpis = []

    compact_kpis = [
        compact_kpi_record(
            kpi
        )
        for kpi in raw_kpis
        if isinstance(
            kpi,
            dict,
        )
    ]

    top_findings = (
        deterministic_output.get(
            "top_findings",
            [],
        )
    )

    if not isinstance(
        top_findings,
        list,
    ):
        top_findings = []

    return {
        "deterministic_summary": (
            deterministic_output.get(
                "summary"
            )
        ),
        "monitoring_status": (
            deterministic_output.get(
                "monitoring_status"
            )
        ),
        "finding_totals": (
            deterministic_output.get(
                "finding_totals",
                {},
            )
        ),
        "kpis": compact_kpis,
        "top_findings": [
            finding
            for finding in top_findings
            if isinstance(
                finding,
                dict,
            )
        ],
        "failed_sources": (
            deterministic_output.get(
                "failed_sources",
                [],
            )
        ),
    }


def determine_business_health_status(
    deterministic_output: dict[
        str,
        Any,
    ],
) -> str:
    """Determine a controlled status for mock-provider development."""

    finding_totals = (
        deterministic_output.get(
            "finding_totals",
            {},
        )
    )

    severity_counts = (
        finding_totals.get(
            "by_severity",
            {}
        )
        if isinstance(
            finding_totals,
            dict,
        )
        else {}
    )

    high_count = int(
        severity_counts.get(
            "High",
            0,
        )
        or 0
    )

    medium_count = int(
        severity_counts.get(
            "Medium",
            0,
        )
        or 0
    )

    failed_sources = (
        deterministic_output.get(
            "failed_sources",
            [],
        )
    )

    if high_count >= 10:
        return "Critical"

    if (
        high_count > 0
        or failed_sources
    ):
        return "At Risk"

    if medium_count > 0:
        return "Watch"

    return "Stable"


def build_mock_monitoring_output(
    deterministic_output: dict[
        str,
        Any,
    ],
) -> dict[str, Any]:
    """
    Build deterministic structured output for the mock provider.

    This is used only for local development and tests. A real provider
    will generate its own response from the validated prompt context.
    """

    top_findings = (
        deterministic_output.get(
            "top_findings",
            [],
        )
    )

    if not isinstance(
        top_findings,
        list,
    ):
        top_findings = []

    attention_areas: list[
        dict[str, Any]
    ] = []

    evidence_ids: list[str] = []
    seen_business_areas: set[str] = set()

    for finding in top_findings:
        if not isinstance(
            finding,
            dict,
        ):
            continue

        finding_id = clean_text(
            finding.get(
                "finding_id"
            )
        )

        if (
            finding_id
            and finding_id
            not in evidence_ids
        ):
            evidence_ids.append(
                finding_id
            )

        business_area = (
            clean_text(
                finding.get(
                    "business_area"
                )
            )
            or clean_text(
                finding.get(
                    "source"
                )
            )
            or "Business Operations"
        )

        if (
            business_area
            in seen_business_areas
        ):
            continue

        seen_business_areas.add(
            business_area
        )

        attention_areas.append(
            {
                "business_area": (
                    business_area
                ),
                "urgency": (
                    clean_text(
                        finding.get(
                            "severity"
                        )
                    )
                    or "Medium"
                ),
                "reason": (
                    clean_text(
                        finding.get(
                            "summary"
                        )
                    )
                    or (
                        "Validated monitoring evidence "
                        "requires management attention."
                    )
                ),
                "evidence_ids": (
                    [finding_id]
                    if finding_id
                    else []
                ),
            }
        )

        if len(
            attention_areas
        ) >= 5:
            break

    failed_sources = (
        deterministic_output.get(
            "failed_sources",
            [],
        )
    )

    missing_evidence_warnings: list[
        str
    ] = []

    if failed_sources:
        failed_source_names = [
            clean_text(
                failure.get(
                    "source"
                )
            )
            for failure in failed_sources
            if isinstance(
                failure,
                dict,
            )
        ]

        failed_source_names = [
            source_name
            for source_name in (
                failed_source_names
            )
            if source_name
        ]

        if failed_source_names:
            missing_evidence_warnings.append(
                "Monitoring evidence is incomplete because "
                "these sources failed: "
                + ", ".join(
                    failed_source_names
                )
                + "."
            )

    if not evidence_ids:
        missing_evidence_warnings.append(
            "No detailed finding identifiers were available "
            "for the monitoring summary."
        )

    finding_totals = (
        deterministic_output.get(
            "finding_totals",
            {}
        )
    )

    total_findings = int(
        finding_totals.get(
            "total",
            0,
        )
        if isinstance(
            finding_totals,
            dict,
        )
        else 0
    )

    severity_counts = (
        finding_totals.get(
            "by_severity",
            {}
        )
        if isinstance(
            finding_totals,
            dict,
        )
        else {}
    )

    high_count = int(
        severity_counts.get(
            "High",
            0,
        )
        or 0
    )

    business_health_status = (
        determine_business_health_status(
            deterministic_output
        )
    )

    summary = (
        f"Business health is {business_health_status}. "
        f"Validated monitoring identified {total_findings} "
        f"findings, including {high_count} High-severity "
        "findings. Management should review the listed "
        "attention areas in evidence order."
    )

    confidence_score = (
        95.0
        if (
            evidence_ids
            and not failed_sources
        )
        else 80.0
        if evidence_ids
        else 60.0
    )

    return {
        "summary": summary,
        "business_health_status": (
            business_health_status
        ),
        "attention_areas": (
            attention_areas
        ),
        "evidence_ids": (
            evidence_ids
        ),
        "confidence_score": (
            confidence_score
        ),
        "missing_evidence_warnings": (
            missing_evidence_warnings
        ),
    }


def get_allowed_monitoring_evidence_ids(
    deterministic_output: dict[
        str,
        Any,
    ],
) -> list[str]:
    """Return finding identifiers the LLM is allowed to cite."""

    top_findings = (
        deterministic_output.get(
            "top_findings",
            [],
        )
    )

    if not isinstance(
        top_findings,
        list,
    ):
        return []

    evidence_ids: list[str] = []

    for finding in top_findings:
        if not isinstance(
            finding,
            dict,
        ):
            continue

        finding_id = clean_text(
            finding.get(
                "finding_id"
            )
        )

        if (
            finding_id
            and finding_id
            not in evidence_ids
        ):
            evidence_ids.append(
                finding_id
            )

    return evidence_ids


class MonitoringAgent(BaseAgent):
    """
    Monitor deterministic business data and optionally enhance it.

    Deterministic KPIs and analytics remain the factual foundation.
    The optional LLM may summarize validated values but cannot change
    finding totals, severity counts, KPI values, or evidence records.
    """

    name = "Monitoring Agent"
    version = "1.1.0"

    description = (
        "Collects business KPIs and analytics findings across "
        "sales, inventory, complaints, vendors, and finance, "
        "with optional evidence-grounded LLM summarization."
    )

    def __init__(
        self,
        llm_provider: (
            BaseLLMProvider
            | None
        ) = None,
    ) -> None:
        """Initialize with an optional provider for injection/testing."""

        super().__init__()

        self._llm_provider = (
            llm_provider
        )

        if (
            self._llm_provider
            is None
            and settings.llm_enabled
        ):
            self._llm_provider = (
                get_configured_provider()
            )

    async def run(
        self,
        context: AgentContext,
    ) -> dict[str, Any]:
        """Generate deterministic output and optional LLM enhancement."""

        deterministic_output = (
            build_deterministic_monitoring_output(
                context
            )
        )

        provider = (
            self._llm_provider
        )

        if (
            provider is None
            or not provider.config.enabled
        ):
            return (
                deterministic_output
            )

        validated_context = (
            build_monitoring_llm_context(
                deterministic_output
            )
        )

        allowed_evidence_ids = (
            get_allowed_monitoring_evidence_ids(
                deterministic_output
            )
        )

        mock_structured_output = (
            build_mock_monitoring_output(
                deterministic_output
            )
        )

        try:
            (
                enhancement,
                execution_metadata,
            ) = await run_structured_enhancement(
                provider=provider,
                agent_name=self.name,
                agent_version=(
                    self.version
                ),
                prompt_name=(
                    MONITORING_PROMPT_NAME
                ),
                prompt_version=(
                    MONITORING_PROMPT_VERSION
                ),
                validated_context=(
                    validated_context
                ),
                response_model=(
                    MonitoringSummaryV1
                ),
                allowed_evidence_ids=(
                    allowed_evidence_ids
                ),
                mock_structured_output=(
                    mock_structured_output
                ),
                request_metadata={
                    "run_id": (
                        context.run_id
                    ),
                    "run_type": (
                        context.run_type
                    ),
                },
            )

        except LLMError as error:
            failed_metadata = (
                build_failed_execution_metadata(
                    provider=provider,
                    prompt_name=(
                        MONITORING_PROMPT_NAME
                    ),
                    prompt_version=(
                        MONITORING_PROMPT_VERSION
                    ),
                    error=error,
                )
            )

            raise attach_deterministic_fallback(
                error=error,
                deterministic_output=(
                    deterministic_output
                ),
                execution_metadata=(
                    failed_metadata
                ),
            )

        enhanced_output = dict(
            deterministic_output
        )

        enhanced_output["summary"] = (
            enhancement.summary
        )

        enhanced_output[
            "llm_enhancement"
        ] = {
            "status": "Complete",
            "schema_name": (
                MonitoringSummaryV1.__name__
            ),
            "deterministic_summary": (
                deterministic_output[
                    "summary"
                ]
            ),
            **enhancement.model_dump(
                mode="python"
            ),
        }

        enhanced_output[
            "_execution_metadata"
        ] = execution_metadata.model_dump(
            mode="python"
        )

        return enhanced_output

    async def fallback(
        self,
        context: AgentContext,
        error: Exception,
    ) -> dict[str, Any] | None:
        """Return the already-created deterministic monitoring output."""

        del context

        return build_attached_fallback_output(
            error
        )
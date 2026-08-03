from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = PROJECT_ROOT / "tests"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))


# Importing conftest loads .env.test and performs the database
# safety checks before the application is used.
from conftest import actual_database_name, app  # noqa: E402


ANALYTICS_ENDPOINTS = {
    "Sales": "/api/analytics/sales",
    "Inventory": "/api/analytics/inventory",
    "Complaints": "/api/analytics/complaints",
    "Vendors": "/api/analytics/vendors",
    "Finance": "/api/analytics/finance",
}


def require_success(
    *,
    endpoint: str,
    response_status: int,
    response_body: Any,
) -> None:
    """Stop inspection if an endpoint does not return HTTP 200."""

    if response_status != 200:
        raise RuntimeError(
            f"Endpoint '{endpoint}' returned HTTP "
            f"{response_status}: {response_body}"
        )


def print_kpi_summary(
    client: TestClient,
) -> None:
    """Print the real KPI results calculated from the test database."""

    endpoint = "/api/kpis"
    response = client.get(endpoint)

    require_success(
        endpoint=endpoint,
        response_status=response.status_code,
        response_body=response.text,
    )

    response_data = response.json()

    print("\nKPI SUMMARY")
    print("-" * 70)
    print(
        f"Total KPIs: "
        f"{response_data.get('total_kpis', 0)}"
    )

    for kpi in response_data.get(
        "kpis",
        [],
    ):
        print(
            f"- {kpi.get('kpi_name')}: "
            f"{kpi.get('display_value')}"
        )

    store_records = response_data.get(
        "latest_store_target_achievement",
        [],
    )

    print(
        "Latest store target-achievement records: "
        f"{len(store_records)}"
    )


def build_finding_description(
    finding: dict[str, Any],
) -> str:
    """Build a compact description of one analytics finding."""

    selected_fields = [
        "finding_id",
        "analysis_type",
        "severity",
        "entity_type",
        "entity_id",
        "store_id",
        "product_id",
        "vendor_id",
        "month",
    ]

    finding_parts = []

    for field_name in selected_fields:
        field_value = finding.get(
            field_name
        )

        if field_value is not None:
            finding_parts.append(
                f"{field_name}={field_value}"
            )

    return ", ".join(
        finding_parts
    )


def print_analytics_summary(
    *,
    client: TestClient,
    analytics_name: str,
    endpoint: str,
) -> None:
    """Print counts and one sample from an analytics endpoint."""

    response = client.get(endpoint)

    require_success(
        endpoint=endpoint,
        response_status=response.status_code,
        response_body=response.text,
    )

    response_data = response.json()

    total_findings = response_data.get(
        "total_findings",
        0,
    )

    matching_findings = response_data.get(
        "matching_findings",
        0,
    )

    findings = response_data.get(
        "findings",
        [],
    )

    summary = response_data.get(
        "summary",
        [],
    )

    print(
        f"\n{analytics_name.upper()} ANALYTICS"
    )
    print("-" * 70)
    print(
        f"Total findings: {total_findings}"
    )
    print(
        f"Matching findings returned: "
        f"{matching_findings}"
    )
    print(
        f"Findings included in response: "
        f"{len(findings)}"
    )

    print("Finding summary:")

    if summary:
        for summary_item in summary:
            print(
                "- "
                f"{summary_item.get('analysis_type')} | "
                f"{summary_item.get('severity')} | "
                f"{summary_item.get('finding_count')}"
            )
    else:
        print("- No summary records returned.")

    if findings:
        first_finding = findings[0]

        print(
            "First finding: "
            + build_finding_description(
                first_finding
            )
        )

        print(
            "First finding summary: "
            f"{first_finding.get('summary')}"
        )
    else:
        print(
            "First finding: No finding returned."
        )


def main() -> None:
    """Inspect real analytics calculated from seeded test data."""

    print(
        "SEEDED TEST-DATABASE ANALYTICS INSPECTION"
    )
    print("=" * 70)
    print(
        f"Verified database: "
        f"{actual_database_name}"
    )

    if (
        actual_database_name
        != "ai_operating_intelligence_test"
    ):
        raise RuntimeError(
            "Unsafe database detected. This script may run "
            "only against ai_operating_intelligence_test."
        )

    with TestClient(app) as client:
        print_kpi_summary(
            client
        )

        for (
            analytics_name,
            endpoint,
        ) in ANALYTICS_ENDPOINTS.items():
            print_analytics_summary(
                client=client,
                analytics_name=analytics_name,
                endpoint=endpoint,
            )

    print("\n" + "=" * 70)
    print(
        "Seeded analytics inspection completed successfully."
    )


if __name__ == "__main__":
    main()
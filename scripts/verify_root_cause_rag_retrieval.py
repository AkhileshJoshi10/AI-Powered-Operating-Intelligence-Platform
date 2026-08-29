from __future__ import annotations

from datetime import date
from pathlib import Path
import runpy
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_CONFTEXT = PROJECT_ROOT / "tests" / "conftest.py"
FIXTURE_FILE = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "knowledge"
    / "root_cause_test_policy.md"
)
EXPECTED_TEST_DATABASE = "ai_operating_intelligence_test"

TEST_DOCUMENT_TITLE = (
    "SmartMart Inventory and Vendor Escalation Policy"
)
TEST_DOCUMENT_KEY = (
    "day34-root-cause-rag-test-policy"
)
TEST_METADATA = {
    "purpose": "day34-root-cause-rag-validation",
    "synthetic": True,
}

RETRIEVAL_QUERY = (
    "inventory OR replenishment OR product OR availability "
    "OR vendor OR delivery OR supplier OR reliability "
    "OR fulfilment OR procurement"
)


def load_verified_test_state(
) -> dict[str, Any]:
    """Load pytest DB configuration and require the dedicated test DB."""

    if not TEST_CONFTEXT.exists():
        raise RuntimeError(
            "tests/conftest.py was not found."
        )

    state = runpy.run_path(
        str(
            TEST_CONFTEXT
        )
    )

    actual_database_name = str(
        state.get(
            "actual_database_name",
            "",
        )
    )

    if (
        actual_database_name
        != EXPECTED_TEST_DATABASE
    ):
        raise RuntimeError(
            "Unsafe database detected. Expected "
            f"{EXPECTED_TEST_DATABASE!r}, received "
            f"{actual_database_name!r}."
        )

    if "engine" not in state:
        raise RuntimeError(
            "tests/conftest.py did not expose the test engine."
        )

    return state


def main() -> None:
    """Seed one synthetic policy and verify real agent-safe retrieval."""

    if not FIXTURE_FILE.exists():
        raise RuntimeError(
            "Missing Root-Cause RAG knowledge fixture: "
            + str(
                FIXTURE_FILE
            )
        )

    test_state = load_verified_test_state()
    test_engine = test_state[
        "engine"
    ]

    # Import only after tests/conftest.py has established and verified
    # the dedicated test database environment.
    from backend.app.services.agent_knowledge_service import (
        retrieve_agent_knowledge,
    )
    from backend.app.services.knowledge_service import (
        ingest_knowledge_document,
    )

    file_bytes = FIXTURE_FILE.read_bytes()

    ingestion = ingest_knowledge_document(
        title=TEST_DOCUMENT_TITLE,
        filename=FIXTURE_FILE.name,
        content_type="text/markdown",
        file_bytes=file_bytes,
        document_type="Policy",
        access_scope="Internal",
        source_date=date(
            2026,
            8,
            1,
        ),
        created_by="day34-rag-validation",
        metadata=dict(
            TEST_METADATA
        ),
        logical_document_key=(
            TEST_DOCUMENT_KEY
        ),
        database_engine=test_engine,
    )

    document = ingestion.get(
        "document",
        {},
    )

    if not isinstance(
        document,
        dict,
    ):
        raise RuntimeError(
            "Knowledge ingestion did not return document metadata."
        )

    if document.get(
        "status"
    ) != "Active":
        raise RuntimeError(
            "The synthetic test policy is not Active."
        )

    if bool(
        document.get(
            "prompt_injection_detected"
        )
    ):
        raise RuntimeError(
            "The synthetic test policy was unexpectedly quarantined."
        )

    retrieval = retrieve_agent_knowledge(
        query=RETRIEVAL_QUERY,
        allowed_access_scopes=(
            "Internal",
        ),
        document_types=[
            "Policy",
        ],
        metadata_filter=dict(
            TEST_METADATA
        ),
        result_limit=4,
        max_context_tokens=1200,
        database_engine=test_engine,
    )

    if retrieval.get(
        "status"
    ) != "success":
        raise RuntimeError(
            "Agent-safe knowledge retrieval did not succeed."
        )

    results = retrieval.get(
        "knowledge_context",
        [],
    )
    citations = retrieval.get(
        "citations",
        [],
    )

    if not isinstance(
        results,
        list,
    ) or not results:
        raise RuntimeError(
            "No knowledge chunks were retrieved from PostgreSQL."
        )

    if not isinstance(
        citations,
        list,
    ) or not citations:
        raise RuntimeError(
            "No stable knowledge citation IDs were returned."
        )

    matching_results = [
        result
        for result in results
        if (
            isinstance(
                result,
                dict,
            )
            and result.get(
                "title"
            )
            == TEST_DOCUMENT_TITLE
        )
    ]

    if not matching_results:
        raise RuntimeError(
            "Retrieval did not return the seeded synthetic policy."
        )

    invalid_citations = [
        str(
            citation
        )
        for citation in citations
        if not str(
            citation
        ).startswith(
            "DOC-"
        )
    ]

    if invalid_citations:
        raise RuntimeError(
            "Knowledge retrieval returned invalid citation IDs: "
            + ", ".join(
                invalid_citations
            )
        )

    print(
        "Database:",
        EXPECTED_TEST_DATABASE,
    )
    print(
        "Document:",
        document.get(
            "title"
        ),
    )
    print(
        "Document ID:",
        document.get(
            "document_id"
        ),
    )
    print(
        "Version:",
        document.get(
            "version_number"
        ),
    )
    print(
        "Status:",
        document.get(
            "status"
        ),
    )
    print(
        "Duplicate:",
        bool(
            ingestion.get(
                "duplicate"
            )
        ),
    )
    print(
        "Retrieval method:",
        retrieval.get(
            "retrieval_method"
        ),
    )
    print(
        "Retrieved chunks:",
        retrieval.get(
            "retrieved_result_count"
        ),
    )
    print(
        "Included chunks:",
        retrieval.get(
            "included_result_count"
        ),
    )
    print(
        "Context token estimate:",
        retrieval.get(
            "context_token_estimate"
        ),
    )
    print(
        "Citations:",
        ", ".join(
            str(
                citation
            )
            for citation in citations
        ),
    )
    print()
    print(
        "DAY 34 ROOT-CAUSE POSTGRESQL RAG RETRIEVAL PASSED"
    )


if __name__ == "__main__":
    main()

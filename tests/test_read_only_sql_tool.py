from __future__ import annotations

import asyncio
from typing import Any

import pytest
from sqlalchemy.engine import Engine

from backend.app.services.agent_tool_service import (
    default_tool_registry,
    list_registered_agent_tools,
)
from backend.app.tools import (
    AgentToolExecutor,
    ToolAccessMode,
    ToolExecutionContext,
    ToolExecutionStatus,
    ToolRegistry,
)
from backend.app.tools.read_only_sql_tool import (
    ALLOWED_READ_ONLY_SQL_TABLES,
    RUN_READ_ONLY_SQL_TOOL_NAME,
    ReadOnlySQLValidationError,
    build_read_only_sql_tool_definition,
    validate_read_only_sql,
)


def build_context(
    *,
    agent_name: str = "Root-Cause Agent",
) -> ToolExecutionContext:
    return ToolExecutionContext(
        run_id="RUN-SQL-TOOL-001",
        agent_name=agent_name,
        requested_by="pytest",
        allowed_tools=[
            RUN_READ_ONLY_SQL_TOOL_NAME
        ],
        allow_write_tools=False,
        approved_write_tools=[],
    )


def build_executor(
    *,
    database_engine: Engine,
    enabled: bool = True,
    maximum_rows: int = 20,
) -> AgentToolExecutor:
    registry = ToolRegistry()

    registry.register(
        build_read_only_sql_tool_definition(
            enabled=enabled,
            database_engine=database_engine,
            statement_timeout_ms=2000,
            maximum_rows=maximum_rows,
        )
    )

    return AgentToolExecutor(
        registry,
        tools_enabled=True,
        write_tools_enabled=False,
        timeout_seconds=5.0,
    )


def validate(
    sql: str,
    parameters: dict[str, Any] | None = None,
) -> list[str]:
    return validate_read_only_sql(
        sql=sql,
        parameters=parameters or {},
    )


def test_sql_tool_is_registered_but_disabled_by_default() -> None:
    assert (
        RUN_READ_ONLY_SQL_TOOL_NAME
        in list_registered_agent_tools()
    )

    definition = default_tool_registry.get(
        RUN_READ_ONLY_SQL_TOOL_NAME
    )

    assert definition.enabled is False
    assert definition.access_mode == ToolAccessMode.READ_ONLY
    assert definition.allowed_agents == (
        "Root-Cause Agent",
    )


def test_sql_table_allowlist_is_intentionally_narrow() -> None:
    assert ALLOWED_READ_ONLY_SQL_TABLES == frozenset(
        {
            "products",
            "stores",
            "vendors",
            "sales",
            "inventory",
            "complaints",
            "finance",
            "vendor_deliveries",
        }
    )

    assert "employees" not in ALLOWED_READ_ONLY_SQL_TABLES
    assert "audit_logs" not in ALLOWED_READ_ONLY_SQL_TABLES
    assert "agent_runs" not in ALLOWED_READ_ONLY_SQL_TABLES
    assert "knowledge_documents" not in ALLOWED_READ_ONLY_SQL_TABLES


@pytest.mark.parametrize(
    ("sql", "expected_fragment"),
    [
        (
            "UPDATE sales SET total_sales = 0",
            "start with SELECT or WITH",
        ),
        (
            "DELETE FROM sales",
            "start with SELECT or WITH",
        ),
        (
            "DROP TABLE sales",
            "start with SELECT or WITH",
        ),
        (
            (
                "WITH changed AS ("
                "DELETE FROM sales RETURNING sale_id"
                ") SELECT sale_id FROM changed"
            ),
            "prohibited",
        ),
        (
            "SELECT store_id INTO temp_store FROM stores",
            "prohibited",
        ),
        (
            (
                "SELECT store_id FROM stores; "
                "SELECT vendor_id FROM vendors"
            ),
            "Semicolons",
        ),
        (
            "SELECT store_id FROM stores -- comment",
            "comments",
        ),
        (
            "SELECT store_id FROM /* hidden */ stores",
            "comments",
        ),
    ],
)
def test_mutating_or_obfuscated_sql_is_rejected(
    sql: str,
    expected_fragment: str,
) -> None:
    with pytest.raises(
        ReadOnlySQLValidationError,
        match=expected_fragment,
    ):
        validate(
            sql
        )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT audit_log_id FROM audit_logs",
        "SELECT agent_run_id FROM agent_runs",
        "SELECT employee_id FROM employees",
        "SELECT document_id FROM knowledge_documents",
        "SELECT table_name FROM information_schema.tables",
        "SELECT relname FROM pg_catalog.pg_class",
    ],
)
def test_non_allowlisted_relations_are_rejected(
    sql: str,
) -> None:
    with pytest.raises(
        ReadOnlySQLValidationError
    ):
        validate(
            sql
        )


def test_safe_select_and_cte_are_accepted() -> None:
    assert validate(
        (
            "SELECT store_id, "
            "SUM(total_sales) AS sales_total "
            "FROM sales "
            "GROUP BY store_id "
            "ORDER BY sales_total DESC"
        )
    ) == [
        "sales"
    ]

    assert validate(
        (
            "WITH store_sales AS ("
            "SELECT store_id, "
            "SUM(total_sales) AS sales_total "
            "FROM sales "
            "GROUP BY store_id"
            ") "
            "SELECT store_id, sales_total "
            "FROM store_sales "
            "ORDER BY sales_total DESC"
        )
    ) == [
        "sales"
    ]


def test_count_star_is_allowed_but_wildcard_output_is_not() -> None:
    assert validate(
        "SELECT COUNT(*) AS total_rows FROM stores"
    ) == [
        "stores"
    ]

    with pytest.raises(
        ReadOnlySQLValidationError,
        match="Wildcard",
    ):
        validate(
            "SELECT * FROM stores"
        )

    with pytest.raises(
        ReadOnlySQLValidationError,
        match="Wildcard",
    ):
        validate(
            "SELECT stores.* FROM stores"
        )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT customer_id FROM complaints",
        "SELECT employee_id FROM sales",
        "SELECT manager_id FROM stores",
    ],
)
def test_sensitive_identifiers_are_rejected(
    sql: str,
) -> None:
    with pytest.raises(
        ReadOnlySQLValidationError,
        match="restricted identifier",
    ):
        validate(
            sql
        )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT pg_sleep(5) FROM stores",
        "SELECT generate_series(1, 100) FROM stores",
        (
            "SELECT current_setting('server_version') "
            "FROM stores"
        ),
    ],
)
def test_unreviewed_functions_are_rejected(
    sql: str,
) -> None:
    with pytest.raises(
        ReadOnlySQLValidationError,
        match="not allowlisted",
    ):
        validate(
            sql
        )


def test_implicit_comma_join_and_table_aliases_are_rejected() -> None:
    with pytest.raises(
        ReadOnlySQLValidationError,
        match="comma joins",
    ):
        validate(
            (
                "SELECT stores.store_id, vendors.vendor_id "
                "FROM stores, vendors"
            )
        )

    with pytest.raises(
        ReadOnlySQLValidationError,
        match="aliases",
    ):
        validate(
            "SELECT s.store_id FROM stores s"
        )


def test_exact_named_parameters_are_required() -> None:
    query = (
        "SELECT store_id, total_revenue "
        "FROM finance "
        "WHERE store_id = :store_id "
        "AND month = :month"
    )

    assert validate(
        query,
        {
            "store_id": "S003",
            "month": "2026-06",
        },
    ) == [
        "finance"
    ]

    with pytest.raises(
        ReadOnlySQLValidationError,
        match="Missing SQL parameters",
    ):
        validate(
            query,
            {
                "store_id": "S003",
            },
        )

    with pytest.raises(
        ReadOnlySQLValidationError,
        match="Unused SQL parameters",
    ):
        validate(
            query,
            {
                "store_id": "S003",
                "month": "2026-06",
                "extra": "not-used",
            },
        )


def test_disabled_sql_tool_is_denied_before_database_access(
    test_engine: Engine,
) -> None:
    executor = build_executor(
        database_engine=test_engine,
        enabled=False,
    )

    result = asyncio.run(
        executor.execute(
            tool_name=RUN_READ_ONLY_SQL_TOOL_NAME,
            arguments={
                "sql": (
                    "SELECT COUNT(*) AS total_rows "
                    "FROM stores"
                ),
                "parameters": {},
                "purpose": "Count stores for validation.",
            },
            context=build_context(),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED
    assert (
        result.call_record.permission_reason
        == (
            "Controlled read-only SQL is disabled "
            "by application configuration."
        )
    )


def test_recommendation_agent_cannot_execute_sql(
    test_engine: Engine,
) -> None:
    executor = build_executor(
        database_engine=test_engine,
        enabled=True,
    )

    result = asyncio.run(
        executor.execute(
            tool_name=RUN_READ_ONLY_SQL_TOOL_NAME,
            arguments={
                "sql": (
                    "SELECT COUNT(*) AS total_rows "
                    "FROM stores"
                ),
                "parameters": {},
                "purpose": "Count stores for validation.",
            },
            context=build_context(
                agent_name="Recommendation Agent"
            ),
        )
    )

    assert result.status == ToolExecutionStatus.DENIED


def test_controlled_sql_executes_on_verified_test_database(
    test_engine: Engine,
) -> None:
    executor = build_executor(
        database_engine=test_engine,
        enabled=True,
    )

    result = asyncio.run(
        executor.execute(
            tool_name=RUN_READ_ONLY_SQL_TOOL_NAME,
            arguments={
                "sql": (
                    "SELECT COUNT(*) AS total_rows "
                    "FROM stores"
                ),
                "parameters": {},
                "purpose": (
                    "Verify a bounded read-only aggregate "
                    "against the test database."
                ),
            },
            context=build_context(),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output is not None
    assert result.output["tables_used"] == [
        "stores"
    ]
    assert result.output["columns"] == [
        "total_rows"
    ]
    assert result.output["row_count"] == 1
    assert result.output["read_only_transaction"] is True
    assert result.output["statement_timeout_ms"] == 2000
    assert result.output["maximum_rows"] == 20
    assert (
        len(
            result.output[
                "query_fingerprint_sha256"
            ]
        )
        == 64
    )


def test_controlled_sql_uses_bound_parameters_on_test_database(
    test_engine: Engine,
) -> None:
    executor = build_executor(
        database_engine=test_engine,
        enabled=True,
    )

    result = asyncio.run(
        executor.execute(
            tool_name=RUN_READ_ONLY_SQL_TOOL_NAME,
            arguments={
                "sql": (
                    "SELECT store_id, store_name "
                    "FROM stores "
                    "WHERE store_id = :store_id "
                    "ORDER BY store_id"
                ),
                "parameters": {
                    "store_id": "S003",
                },
                "purpose": (
                    "Read one store using a bound identifier."
                ),
            },
            context=build_context(),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output is not None
    assert result.output["row_count"] <= 1

    for row in result.output["rows"]:
        assert row["store_id"] == "S003"


def test_sql_output_is_bounded_to_configured_maximum(
    test_engine: Engine,
) -> None:
    executor = build_executor(
        database_engine=test_engine,
        enabled=True,
        maximum_rows=3,
    )

    result = asyncio.run(
        executor.execute(
            tool_name=RUN_READ_ONLY_SQL_TOOL_NAME,
            arguments={
                "sql": (
                    "SELECT product_id, product_name "
                    "FROM products "
                    "ORDER BY product_id"
                ),
                "parameters": {},
                "purpose": (
                    "Verify that SQL result rows are bounded."
                ),
            },
            context=build_context(),
        )
    )

    assert result.status == ToolExecutionStatus.SUCCESS
    assert result.output is not None
    assert result.output["row_count"] <= 3
    assert result.output["maximum_rows"] == 3

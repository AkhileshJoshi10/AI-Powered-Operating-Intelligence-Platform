from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from sqlalchemy import text
from sqlalchemy.engine import Engine

from backend.app.db.database import engine
from backend.app.tools.tool_models import (
    ToolAccessMode,
    ToolDefinition,
    ToolExecutionContext,
)


RUN_READ_ONLY_SQL_TOOL_NAME = "run_read_only_sql"


ALLOWED_READ_ONLY_SQL_TABLES = frozenset(
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


PROHIBITED_SQL_KEYWORDS = frozenset(
    {
        "insert",
        "update",
        "delete",
        "merge",
        "create",
        "alter",
        "drop",
        "truncate",
        "grant",
        "revoke",
        "copy",
        "vacuum",
        "analyze",
        "cluster",
        "reindex",
        "refresh",
        "call",
        "do",
        "execute",
        "prepare",
        "deallocate",
        "set",
        "reset",
        "discard",
        "listen",
        "notify",
        "unlisten",
        "lock",
        "checkpoint",
        "comment",
        "begin",
        "commit",
        "rollback",
        "savepoint",
        "release",
        "transaction",
        "into",
        "recursive",
    }
)


SENSITIVE_SQL_IDENTIFIERS = frozenset(
    {
        "customer_id",
        "employee_id",
        "assigned_employee_id",
        "manager_id",
        "employee_name",
        "email",
        "email_address",
        "phone",
        "phone_number",
        "mobile",
        "address",
        "password",
        "api_key",
        "secret",
        "token",
        "content_text",
    }
)


SAFE_SQL_FUNCTIONS = frozenset(
    {
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "round",
        "abs",
        "ceil",
        "ceiling",
        "floor",
        "power",
        "sqrt",
        "coalesce",
        "nullif",
        "greatest",
        "least",
        "lower",
        "upper",
        "length",
        "char_length",
        "ltrim",
        "rtrim",
        "replace",
        "concat",
        "date_trunc",
        "date_part",
        "to_char",
        "cast",
    }
)


SQL_PAREN_SYNTAX_WORDS = frozenset(
    {
        "as",
        "from",
        "join",
        "on",
        "where",
        "having",
        "filter",
        "over",
        "in",
        "exists",
        "values",
    }
)


CLAUSE_END_WORDS = frozenset(
    {
        "where",
        "group",
        "having",
        "order",
        "limit",
        "offset",
        "union",
        "intersect",
        "except",
        "window",
        "fetch",
        "for",
    }
)


RELATION_PATTERN = re.compile(
    r"\b(?:from|join)\s+"
    r"(?:only\s+)?"
    r"([a-z_][a-z0-9_]*"
    r"(?:\.[a-z_][a-z0-9_]*)?)",
    re.IGNORECASE,
)


CTE_PATTERN = re.compile(
    r"(?:\bwith\b|,)\s*"
    r"([a-z_][a-z0-9_]*)"
    r"(?:\s*\([^)]*\))?"
    r"\s+as\s*\(",
    re.IGNORECASE,
)


PARAMETER_PATTERN = re.compile(
    r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)"
)


FUNCTION_PATTERN = re.compile(
    r"\b([a-z_][a-z0-9_]*)\s*\(",
    re.IGNORECASE,
)


IDENTIFIER_PATTERN = re.compile(
    r"\b[a-z_][a-z0-9_]*\b",
    re.IGNORECASE,
)


DOLLAR_QUOTE_PATTERN = re.compile(
    r"\$[A-Za-z_0-9]*\$"
)


SQL_TOKEN_PATTERN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*|[(),]"
)


MAXIMUM_SQL_QUERY_CHARACTERS = 4000
MAXIMUM_SQL_RESULT_COLUMNS = 40
MAXIMUM_SQL_CELL_CHARACTERS = 2000


class ReadOnlySQLValidationError(ValueError):
    """Raised when SQL fails the controlled read-only policy."""


class ReadOnlySQLInput(BaseModel):
    """One bounded parameterized read-only SQL request."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    sql: str = Field(
        min_length=8,
        max_length=MAXIMUM_SQL_QUERY_CHARACTERS,
    )

    parameters: dict[
        str,
        str | int | float | bool | None,
    ] = Field(
        default_factory=dict,
        max_length=30,
    )

    purpose: str = Field(
        min_length=5,
        max_length=300,
    )

    @field_validator(
        "parameters",
        mode="before",
    )
    @classmethod
    def validate_parameter_container(
        cls,
        value: object,
    ) -> object:
        if value is None:
            return {}

        if not isinstance(
            value,
            dict,
        ):
            raise ValueError(
                "SQL parameters must be supplied as an object."
            )

        for raw_name, raw_value in value.items():
            parameter_name = str(
                raw_name
            )

            if not re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*",
                parameter_name,
            ):
                raise ValueError(
                    "SQL parameter names must use letters, "
                    "numbers, and underscores."
                )

            if parameter_name.startswith(
                "__tool_"
            ):
                raise ValueError(
                    "SQL parameter names starting with "
                    "'__tool_' are reserved."
                )

            if not isinstance(
                raw_value,
                (
                    str,
                    int,
                    float,
                    bool,
                    type(None),
                ),
            ):
                raise ValueError(
                    "SQL parameter values must be JSON scalar values."
                )

        return value


class ReadOnlySQLOutput(BaseModel):
    """Bounded JSON-safe result from controlled SQL."""

    model_config = ConfigDict(
        extra="forbid",
    )

    status: Literal["success"] = "success"
    query_fingerprint_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )
    tables_used: list[str]
    columns: list[str]
    row_count: int = Field(
        ge=0,
    )
    truncated: bool
    rows: list[dict[str, Any]]
    read_only_transaction: Literal[True] = True
    statement_timeout_ms: int = Field(
        ge=100,
        le=10000,
    )
    maximum_rows: int = Field(
        ge=1,
        le=100,
    )
    truncated_cell_count: int = Field(
        default=0,
        ge=0,
    )
    redacted_cell_count: int = Field(
        default=0,
        ge=0,
    )

    @model_validator(mode="after")
    def validate_result_shape(
        self,
    ) -> "ReadOnlySQLOutput":
        if self.row_count != len(
            self.rows
        ):
            raise ValueError(
                "row_count must match returned rows."
            )

        if self.row_count > self.maximum_rows:
            raise ValueError(
                "SQL result exceeded its maximum row count."
            )

        if len(
            self.columns
        ) > MAXIMUM_SQL_RESULT_COLUMNS:
            raise ValueError(
                "SQL result exceeded its maximum column count."
            )

        return self


def mask_sql_string_literals(
    sql: str,
) -> str:
    """Mask literal contents so keywords inside strings are ignored."""

    result = list(
        sql
    )
    index = 0
    inside_string = False

    while index < len(
        sql
    ):
        character = sql[
            index
        ]

        if not inside_string:
            if character == "'":
                inside_string = True
                result[
                    index
                ] = " "
            index += 1
            continue

        result[
            index
        ] = " "

        if character == "'":
            if (
                index + 1
                < len(
                    sql
                )
                and sql[
                    index + 1
                ] == "'"
            ):
                result[
                    index + 1
                ] = " "
                index += 2
                continue

            inside_string = False

        index += 1

    if inside_string:
        raise ReadOnlySQLValidationError(
            "SQL contains an unterminated string literal."
        )

    return "".join(
        result
    )


def normalize_sql_for_fingerprint(
    sql: str,
) -> str:
    """Normalize whitespace for a stable query fingerprint."""

    return " ".join(
        sql.strip().split()
    )


def build_query_fingerprint(
    sql: str,
) -> str:
    """Return SHA-256 without logging the raw SQL."""

    return hashlib.sha256(
        normalize_sql_for_fingerprint(
            sql
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def extract_cte_names(
    sanitized_sql: str,
) -> set[str]:
    """Extract CTE names."""

    return {
        match.group(
            1
        ).casefold()
        for match in CTE_PATTERN.finditer(
            sanitized_sql
        )
    }


def extract_relation_names(
    sanitized_sql: str,
) -> set[str]:
    """Extract relation names following FROM and JOIN."""

    return {
        match.group(
            1
        ).casefold()
        for match in RELATION_PATTERN.finditer(
            sanitized_sql
        )
    }


def reject_implicit_comma_joins(
    sanitized_sql: str,
) -> None:
    """Require explicit JOIN syntax for multi-table queries."""

    tokens = SQL_TOKEN_PATTERN.findall(
        sanitized_sql
    )

    depth = 0
    from_depths: list[int] = []

    for raw_token in tokens:
        token = raw_token.casefold()

        if token == "(":
            depth += 1
            continue

        if token == ")":
            from_depths = [
                item_depth
                for item_depth in from_depths
                if item_depth < depth
            ]
            depth = max(
                0,
                depth - 1,
            )
            continue

        if token == "from":
            from_depths.append(
                depth
            )
            continue

        if (
            token in CLAUSE_END_WORDS
            and depth in from_depths
        ):
            from_depths = [
                item_depth
                for item_depth in from_depths
                if item_depth != depth
            ]
            continue

        if (
            token == ","
            and depth in from_depths
        ):
            raise ReadOnlySQLValidationError(
                "Implicit comma joins are not allowed. "
                "Use explicit JOIN syntax."
            )


def reject_relation_aliases(
    sanitized_sql: str,
) -> None:
    """Reject table aliases to keep relation inspection conservative."""

    alias_pattern = re.compile(
        r"\b(?:from|join)\s+"
        r"(?:only\s+)?"
        r"(?:public\.)?"
        r"[a-z_][a-z0-9_]*"
        r"\s+(?:as\s+)?"
        r"([a-z_][a-z0-9_]*)",
        re.IGNORECASE,
    )

    allowed_following_words = {
        "where",
        "join",
        "inner",
        "left",
        "right",
        "full",
        "cross",
        "on",
        "group",
        "having",
        "order",
        "limit",
        "offset",
        "union",
        "intersect",
        "except",
        "window",
        "fetch",
        "for",
    }

    for match in alias_pattern.finditer(
        sanitized_sql
    ):
        possible_alias = match.group(
            1
        ).casefold()

        if possible_alias not in allowed_following_words:
            raise ReadOnlySQLValidationError(
                "Table aliases are not enabled for the "
                "controlled SQL tool. Use full table names."
            )


def validate_named_parameters(
    *,
    sanitized_sql: str,
    parameters: Mapping[
        str,
        Any,
    ],
) -> None:
    """Require exact SQLAlchemy named-parameter matching."""

    referenced_parameters = {
        match.group(
            1
        )
        for match in PARAMETER_PATTERN.finditer(
            sanitized_sql
        )
    }

    supplied_parameters = set(
        parameters
    )

    missing_parameters = (
        referenced_parameters
        - supplied_parameters
    )
    extra_parameters = (
        supplied_parameters
        - referenced_parameters
    )

    if missing_parameters:
        raise ReadOnlySQLValidationError(
            "Missing SQL parameters: "
            + ", ".join(
                sorted(
                    missing_parameters
                )
            )
        )

    if extra_parameters:
        raise ReadOnlySQLValidationError(
            "Unused SQL parameters are not allowed: "
            + ", ".join(
                sorted(
                    extra_parameters
                )
            )
        )


def validate_sql_functions(
    sanitized_sql: str,
) -> None:
    """Allow only explicitly reviewed analytical functions."""

    for match in FUNCTION_PATTERN.finditer(
        sanitized_sql
    ):
        function_name = match.group(
            1
        ).casefold()

        if function_name in SQL_PAREN_SYNTAX_WORDS:
            continue

        if function_name not in SAFE_SQL_FUNCTIONS:
            raise ReadOnlySQLValidationError(
                "SQL function is not allowlisted: "
                f"{function_name}"
            )


def validate_read_only_sql(
    *,
    sql: str,
    parameters: Mapping[
        str,
        Any,
    ],
) -> list[str]:
    """Validate the intentionally narrow read-only SQL subset."""

    query = sql.strip()

    if not query:
        raise ReadOnlySQLValidationError(
            "SQL cannot be empty."
        )

    if len(
        query
    ) > MAXIMUM_SQL_QUERY_CHARACTERS:
        raise ReadOnlySQLValidationError(
            "SQL exceeds the maximum query length."
        )

    if "\x00" in query:
        raise ReadOnlySQLValidationError(
            "SQL cannot contain null bytes."
        )

    if (
        "--" in query
        or "/*" in query
        or "*/" in query
    ):
        raise ReadOnlySQLValidationError(
            "SQL comments are not allowed."
        )

    if ";" in query:
        raise ReadOnlySQLValidationError(
            "Semicolons are not allowed. "
            "Submit exactly one statement."
        )

    if DOLLAR_QUOTE_PATTERN.search(
        query
    ):
        raise ReadOnlySQLValidationError(
            "Dollar-quoted SQL is not allowed."
        )

    sanitized = mask_sql_string_literals(
        query
    )
    normalized = sanitized.casefold()

    if (
        '"' in sanitized
        or "`" in sanitized
        or "[" in sanitized
        or "]" in sanitized
    ):
        raise ReadOnlySQLValidationError(
            "Quoted or bracketed SQL identifiers are not enabled."
        )

    first_word_match = IDENTIFIER_PATTERN.search(
        normalized
    )
    first_word = (
        first_word_match.group(
            0
        ).casefold()
        if first_word_match
        else ""
    )

    if first_word not in {
        "select",
        "with",
    }:
        raise ReadOnlySQLValidationError(
            "Controlled SQL must start with SELECT or WITH."
        )

    identifier_tokens = {
        token.casefold()
        for token in IDENTIFIER_PATTERN.findall(
            normalized
        )
    }

    prohibited_tokens = (
        identifier_tokens
        & PROHIBITED_SQL_KEYWORDS
    )

    if prohibited_tokens:
        raise ReadOnlySQLValidationError(
            "SQL contains prohibited keyword(s): "
            + ", ".join(
                sorted(
                    prohibited_tokens
                )
            )
        )

    if re.search(
        r"\bfor\s+(?:update|share|no\s+key\s+update|key\s+share)\b",
        normalized,
    ):
        raise ReadOnlySQLValidationError(
            "Row-locking SELECT clauses are not allowed."
        )

    star_checked = re.sub(
        r"\bcount\s*\(\s*\*\s*\)",
        "count(1)",
        normalized,
        flags=re.IGNORECASE,
    )

    if (
        re.search(
            r"\bselect\s+(?:distinct\s+)?\*",
            star_checked,
        )
        or re.search(
            r",\s*\*",
            star_checked,
        )
        or re.search(
            r"\.\s*\*",
            star_checked,
        )
    ):
        raise ReadOnlySQLValidationError(
            "Wildcard SELECT output is not allowed. "
            "Select explicit columns. COUNT(*) is allowed."
        )

    sensitive_tokens = (
        identifier_tokens
        & SENSITIVE_SQL_IDENTIFIERS
    )

    if sensitive_tokens:
        raise ReadOnlySQLValidationError(
            "SQL references restricted identifier(s): "
            + ", ".join(
                sorted(
                    sensitive_tokens
                )
            )
        )

    reject_implicit_comma_joins(
        sanitized
    )
    reject_relation_aliases(
        sanitized
    )

    cte_names = extract_cte_names(
        sanitized
    )
    relation_names = extract_relation_names(
        sanitized
    )

    actual_tables: set[str] = set()

    for raw_relation in relation_names:
        relation_parts = raw_relation.split(
            "."
        )

        if len(
            relation_parts
        ) == 2:
            schema_name, relation_name = (
                relation_parts
            )

            if schema_name != "public":
                raise ReadOnlySQLValidationError(
                    "Only the public schema is permitted."
                )
        else:
            relation_name = relation_parts[
                0
            ]

        if relation_name in cte_names:
            continue

        if (
            relation_name
            not in ALLOWED_READ_ONLY_SQL_TABLES
        ):
            raise ReadOnlySQLValidationError(
                "SQL relation is not allowlisted: "
                f"{relation_name}"
            )

        actual_tables.add(
            relation_name
        )

    validate_sql_functions(
        sanitized
    )

    validate_named_parameters(
        sanitized_sql=sanitized,
        parameters=parameters,
    )

    return sorted(
        actual_tables
    )


def sanitize_result_value(
    value: Any,
) -> tuple[Any, int, int]:
    """Convert one result value into bounded JSON-safe data."""

    if value is None:
        return None, 0, 0

    if isinstance(
        value,
        (
            bool,
            int,
            float,
        ),
    ):
        return value, 0, 0

    if isinstance(
        value,
        Decimal,
    ):
        return float(
            value
        ), 0, 0

    if isinstance(
        value,
        (
            date,
            datetime,
        ),
    ):
        return value.isoformat(), 0, 0

    if isinstance(
        value,
        bytes,
    ):
        return "<binary omitted>", 0, 1

    if isinstance(
        value,
        Mapping,
    ):
        safe_mapping: dict[
            str,
            Any,
        ] = {}
        truncated_count = 0
        redacted_count = 0

        for raw_key, raw_item in value.items():
            key = str(
                raw_key
            )

            if key.casefold() in SENSITIVE_SQL_IDENTIFIERS:
                safe_mapping[
                    key
                ] = "<redacted>"
                redacted_count += 1
                continue

            (
                safe_item,
                item_truncated,
                item_redacted,
            ) = sanitize_result_value(
                raw_item
            )

            safe_mapping[
                key
            ] = safe_item
            truncated_count += item_truncated
            redacted_count += item_redacted

        return (
            safe_mapping,
            truncated_count,
            redacted_count,
        )

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):
        safe_items: list[
            Any
        ] = []
        truncated_count = 0
        redacted_count = 0

        for raw_item in value:
            (
                safe_item,
                item_truncated,
                item_redacted,
            ) = sanitize_result_value(
                raw_item
            )

            safe_items.append(
                safe_item
            )
            truncated_count += item_truncated
            redacted_count += item_redacted

        return (
            safe_items,
            truncated_count,
            redacted_count,
        )

    text_value = str(
        value
    )

    if len(
        text_value
    ) > MAXIMUM_SQL_CELL_CHARACTERS:
        return (
            text_value[
                :MAXIMUM_SQL_CELL_CHARACTERS
            ]
            + "…<truncated>",
            1,
            0,
        )

    return text_value, 0, 0


class ControlledReadOnlySQLExecutor:
    """Execute validated SQL inside a PostgreSQL read-only transaction."""

    def __init__(
        self,
        *,
        database_engine: Engine,
        statement_timeout_ms: int,
        maximum_rows: int,
    ) -> None:
        if not (
            100
            <= statement_timeout_ms
            <= 10000
        ):
            raise ValueError(
                "SQL statement timeout must be between "
                "100 and 10000 milliseconds."
            )

        if not (
            1
            <= maximum_rows
            <= 100
        ):
            raise ValueError(
                "SQL maximum rows must be between 1 and 100."
            )

        self.database_engine = database_engine
        self.statement_timeout_ms = int(
            statement_timeout_ms
        )
        self.maximum_rows = int(
            maximum_rows
        )

    def execute(
        self,
        request: ReadOnlySQLInput,
    ) -> ReadOnlySQLOutput:
        """Validate, execute, bound, and serialize one query."""

        tables_used = validate_read_only_sql(
            sql=request.sql,
            parameters=request.parameters,
        )

        wrapped_sql = (
            "SELECT * FROM (\n"
            + request.sql.strip()
            + "\n) AS controlled_read_only_query "
            "LIMIT :__tool_row_limit"
        )

        execution_parameters = {
            **request.parameters,
            "__tool_row_limit": (
                self.maximum_rows
                + 1
            ),
        }

        with self.database_engine.connect() as connection:
            transaction = connection.begin()

            try:
                connection.exec_driver_sql(
                    "SET TRANSACTION READ ONLY"
                )
                connection.exec_driver_sql(
                    "SET LOCAL statement_timeout = "
                    f"'{self.statement_timeout_ms}ms'"
                )

                result = connection.execute(
                    text(
                        wrapped_sql
                    ),
                    execution_parameters,
                )

                columns = [
                    str(
                        column_name
                    )
                    for column_name in result.keys()
                ]

                if len(
                    columns
                ) > MAXIMUM_SQL_RESULT_COLUMNS:
                    raise ReadOnlySQLValidationError(
                        "SQL result contains too many columns."
                    )

                raw_rows = (
                    result.mappings()
                    .fetchmany(
                        self.maximum_rows
                        + 1
                    )
                )

            finally:
                transaction.rollback()

        truncated = (
            len(
                raw_rows
            )
            > self.maximum_rows
        )

        raw_rows = raw_rows[
            :self.maximum_rows
        ]

        rows: list[
            dict[str, Any]
        ] = []
        truncated_cell_count = 0
        redacted_cell_count = 0

        for raw_row in raw_rows:
            safe_row: dict[
                str,
                Any,
            ] = {}

            for raw_key, raw_value in raw_row.items():
                key = str(
                    raw_key
                )

                if key.casefold() in SENSITIVE_SQL_IDENTIFIERS:
                    safe_row[
                        key
                    ] = "<redacted>"
                    redacted_cell_count += 1
                    continue

                (
                    safe_value,
                    cell_truncated,
                    cell_redacted,
                ) = sanitize_result_value(
                    raw_value
                )

                safe_row[
                    key
                ] = safe_value
                truncated_cell_count += cell_truncated
                redacted_cell_count += cell_redacted

            rows.append(
                safe_row
            )

        return ReadOnlySQLOutput(
            query_fingerprint_sha256=(
                build_query_fingerprint(
                    request.sql
                )
            ),
            tables_used=tables_used,
            columns=columns,
            row_count=len(
                rows
            ),
            truncated=truncated,
            rows=rows,
            read_only_transaction=True,
            statement_timeout_ms=(
                self.statement_timeout_ms
            ),
            maximum_rows=self.maximum_rows,
            truncated_cell_count=(
                truncated_cell_count
            ),
            redacted_cell_count=(
                redacted_cell_count
            ),
        )


def build_read_only_sql_tool_definition(
    *,
    enabled: bool,
    database_engine: Engine = engine,
    statement_timeout_ms: int = 2000,
    maximum_rows: int = 20,
) -> ToolDefinition:
    """Build the separately gated controlled SQL tool."""

    sql_executor = (
        ControlledReadOnlySQLExecutor(
            database_engine=database_engine,
            statement_timeout_ms=(
                statement_timeout_ms
            ),
            maximum_rows=maximum_rows,
        )
    )

    def handler(
        arguments: ReadOnlySQLInput,
        context: ToolExecutionContext,
    ) -> ReadOnlySQLOutput:
        del context

        return sql_executor.execute(
            arguments
        )

    return ToolDefinition(
        name=RUN_READ_ONLY_SQL_TOOL_NAME,
        description=(
            "Run one bounded parameterized read-only SELECT/CTE "
            "query against approved analytical source tables."
        ),
        input_model=ReadOnlySQLInput,
        output_model=ReadOnlySQLOutput,
        handler=handler,
        access_mode=ToolAccessMode.READ_ONLY,
        allowed_agents=(
            "Root-Cause Agent",
        ),
        requires_human_approval=False,
        enabled=enabled,
        disabled_reason=(
            None
            if enabled
            else (
                "Controlled read-only SQL is disabled "
                "by application configuration."
            )
        ),
    )

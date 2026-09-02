from __future__ import annotations

import os
from dataclasses import dataclass


def read_boolean(
    name: str,
    default: bool,
) -> bool:
    """Read a strict boolean environment variable."""

    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    normalized = raw_value.strip().casefold()

    if normalized in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return True

    if normalized in {
        "0",
        "false",
        "no",
        "off",
    }:
        return False

    raise ValueError(
        f"{name} must be a boolean value."
    )


def read_integer(
    name: str,
    default: int,
) -> int:
    """Read an integer environment variable."""

    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        return int(
            raw_value.strip()
        )
    except ValueError as error:
        raise ValueError(
            f"{name} must be an integer."
        ) from error


def read_float(
    name: str,
    default: float,
) -> float:
    """Read a floating-point environment variable."""

    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        return float(
            raw_value.strip()
        )
    except ValueError as error:
        raise ValueError(
            f"{name} must be numeric."
        ) from error


def read_csv_values(
    name: str,
) -> tuple[str, ...]:
    """Read a comma-separated list without duplicate values."""

    raw_value = os.getenv(
        name,
        "",
    )

    values: list[str] = []

    for item in raw_value.split(","):
        normalized = " ".join(
            item.split()
        )

        if (
            normalized
            and normalized not in values
        ):
            values.append(normalized)

    return tuple(values)


@dataclass(frozen=True)
class Settings:
    """Application, provider-independent LLM, and knowledge settings."""

    app_name: str = os.getenv(
        "APP_NAME",
        (
            "AI-Powered Operating "
            "Intelligence Platform API"
        ),
    )
    app_version: str = os.getenv(
        "APP_VERSION",
        "0.1.0",
    )
    environment: str = os.getenv(
        "APP_ENVIRONMENT",
        "development",
    )

    llm_enabled: bool = read_boolean(
        "LLM_ENABLED",
        False,
    )
    llm_provider: str = os.getenv(
        "LLM_PROVIDER",
        "mock",
    )
    llm_model: str = os.getenv(
        "LLM_MODEL",
        "mock-deterministic-v1",
    )
    llm_default_agent_version: str = os.getenv(
        "LLM_DEFAULT_AGENT_VERSION",
        "1.0.0",
    )
    llm_default_prompt_version: str = os.getenv(
        "LLM_DEFAULT_PROMPT_VERSION",
        "v1",
    )
    llm_timeout_seconds: float = read_float(
        "LLM_TIMEOUT_SECONDS",
        30.0,
    )
    llm_max_retries: int = read_integer(
        "LLM_MAX_RETRIES",
        2,
    )
    llm_retry_backoff_seconds: float = read_float(
        "LLM_RETRY_BACKOFF_SECONDS",
        0.25,
    )
    llm_max_input_tokens: int = read_integer(
        "LLM_MAX_INPUT_TOKENS",
        4000,
    )
    llm_max_output_tokens: int = read_integer(
        "LLM_MAX_OUTPUT_TOKENS",
        1000,
    )
    llm_max_estimated_cost_usd: float = read_float(
        "LLM_MAX_ESTIMATED_COST_USD",
        0.02,
    )
    llm_temperature: float = read_float(
        "LLM_TEMPERATURE",
        0.0,
    )
    llm_mask_sensitive_data: bool = read_boolean(
        "LLM_MASK_SENSITIVE_DATA",
        True,
    )
    llm_allowed_tools: tuple[str, ...] = (
        read_csv_values(
            "LLM_ALLOWED_TOOLS"
        )
    )


    groq_api_key: str = os.getenv(
        "GROQ_API_KEY",
        "",
    ).strip()

    knowledge_enabled: bool = read_boolean(
        "KNOWLEDGE_ENABLED",
        True,
    )
    knowledge_max_file_bytes: int = read_integer(
        "KNOWLEDGE_MAX_FILE_BYTES",
        5_000_000,
    )
    knowledge_chunk_size_chars: int = read_integer(
        "KNOWLEDGE_CHUNK_SIZE_CHARS",
        1800,
    )
    knowledge_chunk_overlap_chars: int = read_integer(
        "KNOWLEDGE_CHUNK_OVERLAP_CHARS",
        200,
    )
    knowledge_max_chunks_per_document: int = read_integer(
        "KNOWLEDGE_MAX_CHUNKS_PER_DOCUMENT",
        500,
    )
    knowledge_default_search_limit: int = read_integer(
        "KNOWLEDGE_DEFAULT_SEARCH_LIMIT",
        5,
    )
    knowledge_max_search_limit: int = read_integer(
        "KNOWLEDGE_MAX_SEARCH_LIMIT",
        20,
    )
    knowledge_allowed_extensions: tuple[str, ...] = (
        read_csv_values(
            "KNOWLEDGE_ALLOWED_EXTENSIONS"
        )
        or (
            ".txt",
            ".md",
            ".csv",
            ".json",
        )
    )


    agent_knowledge_enabled: bool = read_boolean(
        "AGENT_KNOWLEDGE_ENABLED",
        True,
    )
    agent_knowledge_search_limit: int = read_integer(
        "AGENT_KNOWLEDGE_SEARCH_LIMIT",
        4,
    )
    agent_knowledge_max_context_tokens: int = read_integer(
        "AGENT_KNOWLEDGE_MAX_CONTEXT_TOKENS",
        1200,
    )


    # Controlled application tool execution remains disabled until
    # explicitly enabled. Provider LLM_ALLOWED_TOOLS is a separate gate.
    agent_tools_enabled: bool = read_boolean(
        "AGENT_TOOLS_ENABLED",
        False,
    )
    agent_write_tools_enabled: bool = read_boolean(
        "AGENT_WRITE_TOOLS_ENABLED",
        False,
    )
    agent_tool_timeout_seconds: float = read_float(
        "AGENT_TOOL_TIMEOUT_SECONDS",
        5.0,
    )


    # Arbitrary SQL remains separately disabled even after general
    # read-only agent tools are enabled.
    agent_read_only_sql_enabled: bool = read_boolean(
        "AGENT_READ_ONLY_SQL_ENABLED",
        False,
    )
    agent_read_only_sql_statement_timeout_ms: int = read_integer(
        "AGENT_READ_ONLY_SQL_STATEMENT_TIMEOUT_MS",
        2000,
    )
    agent_read_only_sql_max_rows: int = read_integer(
        "AGENT_READ_ONLY_SQL_MAX_ROWS",
        20,
    )

    # Recommendation-to-task tool remains separately disabled until
    # explicitly enabled for reviewed use.
    agent_task_conversion_tool_enabled: bool = read_boolean(
        "AGENT_TASK_CONVERSION_TOOL_ENABLED",
        False,
    )


    # Controlled provider/tool orchestration limits.
    agent_llm_tool_max_rounds: int = read_integer(
        "AGENT_LLM_TOOL_MAX_ROUNDS",
        2,
    )
    agent_llm_tool_result_max_chars: int = read_integer(
        "AGENT_LLM_TOOL_RESULT_MAX_CHARS",
        20000,
    )


    # Automation / n8n integration remains opt-in. The API never sends
    # workflow requests unless this gate is explicitly enabled.
    automation_enabled: bool = read_boolean(
        "AUTOMATION_ENABLED",
        False,
    )
    automation_api_secret: str = os.getenv(
        "AUTOMATION_API_SECRET",
        "",
    ).strip()
    n8n_webhook_base_url: str = os.getenv(
        "N8N_WEBHOOK_BASE_URL",
        "",
    ).strip()
    n8n_outbound_auth_token: str = os.getenv(
        "N8N_OUTBOUND_AUTH_TOKEN",
        "",
    ).strip()
    n8n_callback_secret: str = os.getenv(
        "N8N_CALLBACK_SECRET",
        "",
    ).strip()
    n8n_timeout_seconds: float = read_float(
        "N8N_TIMEOUT_SECONDS",
        10.0,
    )
    n8n_max_retries: int = read_integer(
        "N8N_MAX_RETRIES",
        2,
    )
    n8n_retry_backoff_seconds: float = read_float(
        "N8N_RETRY_BACKOFF_SECONDS",
        0.5,
    )
    n8n_high_priority_alert_path: str = os.getenv(
        "N8N_HIGH_PRIORITY_ALERT_PATH",
        "high-priority-alert",
    ).strip()
    n8n_task_reminder_path: str = os.getenv(
        "N8N_TASK_REMINDER_PATH",
        "task-reminder",
    ).strip()
    n8n_overdue_escalation_path: str = os.getenv(
        "N8N_OVERDUE_ESCALATION_PATH",
        "overdue-escalation",
    ).strip()


settings = Settings()
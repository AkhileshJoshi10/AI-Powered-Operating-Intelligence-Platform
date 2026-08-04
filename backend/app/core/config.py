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
    """Application and provider-independent LLM settings."""

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


settings = Settings()

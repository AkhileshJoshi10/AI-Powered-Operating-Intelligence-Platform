from __future__ import annotations

from collections.abc import Callable

from backend.app.llm.base_provider import BaseLLMProvider
from backend.app.llm.llm_exceptions import (
    LLMConfigurationError,
    LLMProviderNotFoundError,
)
from backend.app.llm.llm_models import (
    LLMProviderConfig,
)


ProviderFactory = Callable[
    [LLMProviderConfig],
    BaseLLMProvider,
]


class LLMProviderRegistry:
    """Register and construct provider-independent LLM adapters."""

    def __init__(
        self,
    ) -> None:
        self._factories: dict[
            str,
            ProviderFactory,
        ] = {}

    def register(
        self,
        provider_name: str,
        factory: ProviderFactory,
    ) -> None:
        normalized_name = (
            provider_name.strip().casefold()
        )

        if not normalized_name:
            raise LLMConfigurationError(
                "Provider name cannot be empty."
            )

        if normalized_name in self._factories:
            raise LLMConfigurationError(
                f"LLM provider '{provider_name}' "
                "is already registered."
            )

        self._factories[
            normalized_name
        ] = factory

    def create(
        self,
        config: LLMProviderConfig,
    ) -> BaseLLMProvider:
        normalized_name = (
            config.provider_name.casefold()
        )

        if normalized_name not in self._factories:
            raise LLMProviderNotFoundError(
                f"LLM provider "
                f"'{config.provider_name}' "
                "is not registered."
            )

        return self._factories[
            normalized_name
        ](
            config
        )

    def list_providers(
        self,
    ) -> list[str]:
        return sorted(
            self._factories
        )


def build_default_provider_registry(
) -> LLMProviderRegistry:
    """Create the registry containing safe built-in providers."""

    from backend.app.llm.mock_provider import (
        MockLLMProvider,
    )

    registry = LLMProviderRegistry()
    registry.register(
        "mock",
        MockLLMProvider,
    )

    return registry


default_provider_registry = (
    build_default_provider_registry()
)


def build_provider_config_from_settings(
) -> LLMProviderConfig:
    """Create validated LLM configuration from app settings."""

    from backend.app.core.config import settings

    return LLMProviderConfig(
        enabled=settings.llm_enabled,
        provider_name=settings.llm_provider,
        model_name=settings.llm_model,
        timeout_seconds=(
            settings.llm_timeout_seconds
        ),
        max_retries=settings.llm_max_retries,
        retry_backoff_seconds=(
            settings.llm_retry_backoff_seconds
        ),
        max_input_tokens=(
            settings.llm_max_input_tokens
        ),
        max_output_tokens=(
            settings.llm_max_output_tokens
        ),
        max_estimated_cost_usd=(
            settings.llm_max_estimated_cost_usd
        ),
        temperature=settings.llm_temperature,
        mask_sensitive_data=(
            settings.llm_mask_sensitive_data
        ),
        allowed_tools=list(
            settings.llm_allowed_tools
        ),
    )


def get_configured_provider(
) -> BaseLLMProvider:
    """Construct the provider selected through environment settings."""

    config = (
        build_provider_config_from_settings()
    )

    return default_provider_registry.create(
        config
    )

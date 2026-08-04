from __future__ import annotations


class LLMError(Exception):
    """Base exception for provider-independent LLM failures."""

    retryable = False


class LLMConfigurationError(LLMError):
    """Raised when LLM configuration is incomplete or invalid."""


class LLMProviderNotFoundError(LLMConfigurationError):
    """Raised when a requested provider is not registered."""


class LLMProviderDisabledError(LLMConfigurationError):
    """Raised when an LLM call is attempted while LLM use is disabled."""


class LLMRequestValidationError(LLMError):
    """Raised when an LLM request violates a controlled limit."""


class LLMAuthenticationError(LLMError):
    """Raised when a provider rejects its credentials."""


class LLMTimeoutError(LLMError):
    """Raised when a provider call exceeds its timeout."""

    retryable = True


class LLMRateLimitError(LLMError):
    """Raised when a provider temporarily rate-limits a request."""

    retryable = True


class LLMProviderResponseError(LLMError):
    """Raised when a provider returns an unusable response."""

    retryable = True


class LLMCostLimitExceededError(LLMError):
    """Raised when a response exceeds the configured cost limit."""


class LLMToolPermissionError(LLMError):
    """Raised when a request asks for an unauthorized tool."""

from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from math import ceil
from typing import Any

from backend.app.llm.llm_exceptions import (
    LLMCostLimitExceededError,
    LLMProviderDisabledError,
    LLMProviderResponseError,
    LLMRequestValidationError,
    LLMTimeoutError,
    LLMToolPermissionError,
)
from backend.app.llm.llm_models import (
    LLMMessage,
    LLMProviderConfig,
    LLMRequest,
    LLMResponse,
)


SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(password|api[_-]?key|secret|token)"
    r"\b(\s*[:=]\s*)([^\s,;]+)"
)
BEARER_PATTERN = re.compile(
    r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"
)
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?\d[\d\s()-]{7,}\d)(?!\d)"
)


def mask_sensitive_text(
    value: str,
) -> str:
    """Mask common credentials and personal contact details."""

    masked = SECRET_ASSIGNMENT_PATTERN.sub(
        lambda match: (
            f"{match.group(1)}"
            f"{match.group(2)}"
            "<masked>"
        ),
        value,
    )
    masked = BEARER_PATTERN.sub(
        "Bearer <masked>",
        masked,
    )
    masked = EMAIL_PATTERN.sub(
        "<masked-email>",
        masked,
    )
    masked = PHONE_PATTERN.sub(
        "<masked-phone>",
        masked,
    )

    return masked


def mask_sensitive_value(
    value: Any,
) -> Any:
    """Recursively mask supported sensitive values."""

    if isinstance(value, str):
        return mask_sensitive_text(value)

    if isinstance(value, dict):
        return {
            str(key): mask_sensitive_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            mask_sensitive_value(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return tuple(
            mask_sensitive_value(item)
            for item in value
        )

    return value


def estimate_tokens(
    value: str,
) -> int:
    """
    Estimate tokens without a provider tokenizer.

    Real provider integrations should replace this approximation with
    provider-reported token usage whenever it is available.
    """

    if not value:
        return 0

    return max(
        1,
        ceil(len(value) / 4),
    )


class BaseLLMProvider(ABC):
    """Provider-independent LLM interface with shared guardrails."""

    provider_name = "base"

    def __init__(
        self,
        config: LLMProviderConfig,
    ) -> None:
        self.config = config

    def prepare_request(
        self,
        request: LLMRequest,
    ) -> LLMRequest:
        """Apply permissions, masking and controlled limits."""

        if not self.config.enabled:
            raise LLMProviderDisabledError(
                "LLM execution is disabled by configuration."
            )

        unauthorized_tools = [
            tool_name
            for tool_name in request.allowed_tools
            if tool_name not in self.config.allowed_tools
        ]

        if unauthorized_tools:
            raise LLMToolPermissionError(
                "Unauthorized LLM tools requested: "
                + ", ".join(unauthorized_tools)
            )

        message_text = "\n".join(
            message.content
            for message in request.messages
        )
        estimated_input_tokens = estimate_tokens(
            message_text
        )

        if (
            estimated_input_tokens
            > self.config.max_input_tokens
        ):
            raise LLMRequestValidationError(
                "Estimated input tokens exceed the "
                "configured maximum."
            )

        requested_output_tokens = (
            request.max_output_tokens
            or self.config.max_output_tokens
        )

        if (
            requested_output_tokens
            > self.config.max_output_tokens
        ):
            raise LLMRequestValidationError(
                "Requested output tokens exceed the "
                "configured maximum."
            )

        if not self.config.mask_sensitive_data:
            return request

        masked_messages = [
            LLMMessage(
                role=message.role,
                content=mask_sensitive_text(
                    message.content
                ),
                name=message.name,
                metadata=mask_sensitive_value(
                    message.metadata
                ),
            )
            for message in request.messages
        ]

        return request.model_copy(
            update={
                "messages": masked_messages,
                "metadata": mask_sensitive_value(
                    request.metadata
                ),
            }
        )

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Execute one request with timeout, retry and cost controls."""

        prepared_request = self.prepare_request(
            request
        )

        timeout_seconds = (
            prepared_request.timeout_seconds
            or self.config.timeout_seconds
        )
        max_retries = (
            prepared_request.max_retries
            if prepared_request.max_retries is not None
            else self.config.max_retries
        )
        maximum_cost = (
            prepared_request.max_estimated_cost_usd
            if (
                prepared_request
                .max_estimated_cost_usd
                is not None
            )
            else self.config.max_estimated_cost_usd
        )

        last_error: Exception | None = None

        for attempt_number in range(
            max_retries + 1
        ):
            try:
                response = await asyncio.wait_for(
                    self._generate_once(
                        prepared_request
                    ),
                    timeout=timeout_seconds,
                )

                if (
                    response.request_id
                    != prepared_request.request_id
                ):
                    raise LLMProviderResponseError(
                        "The provider response request ID "
                        "does not match the request."
                    )

                if (
                    response.usage.output_tokens
                    > self.config.max_output_tokens
                ):
                    raise LLMProviderResponseError(
                        "The provider response exceeded the "
                        "configured output-token limit."
                    )

                if (
                    response.usage.estimated_cost_usd
                    > maximum_cost
                ):
                    raise LLMCostLimitExceededError(
                        "The provider response exceeded the "
                        "configured estimated-cost limit."
                    )

                if (
                    prepared_request.require_json_object
                    and response.structured_output is None
                ):
                    raise LLMProviderResponseError(
                        "Structured JSON output was required "
                        "but not returned."
                    )

                return response

            except asyncio.TimeoutError as error:
                last_error = LLMTimeoutError(
                    "The LLM provider request timed out."
                )
                current_error: Exception = last_error

            except Exception as error:
                last_error = error
                current_error = error

            retryable = bool(
                getattr(
                    current_error,
                    "retryable",
                    False,
                )
            )

            if (
                not retryable
                or attempt_number >= max_retries
            ):
                raise current_error

            retry_delay = (
                self.config.retry_backoff_seconds
                * (2 ** attempt_number)
            )

            if retry_delay > 0:
                await asyncio.sleep(
                    retry_delay
                )

        if last_error is not None:
            raise last_error

        raise LLMProviderResponseError(
            "The LLM provider did not return a response."
        )

    @abstractmethod
    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Perform one provider-specific request attempt."""

        raise NotImplementedError

from __future__ import annotations

import json
from json import JSONDecodeError
from time import perf_counter
from typing import Any

import groq
from groq import AsyncGroq

from backend.app.llm.base_provider import (
    BaseLLMProvider,
    estimate_tokens,
)
from backend.app.llm.llm_exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMCostLimitExceededError,
    LLMProviderResponseError,
    LLMRateLimitError,
    LLMRequestValidationError,
    LLMTimeoutError,
)
from backend.app.llm.llm_models import (
    LLMProviderConfig,
    LLMRequest,
    LLMResponse,
    LLMTokenUsage,
)


GROQ_MODEL_PRICING_USD_PER_MILLION: dict[
    str,
    tuple[float, float],
] = {
    "openai/gpt-oss-20b": (
        0.075,
        0.30,
    ),
}


def normalize_text(
    value: object,
) -> str:
    """Convert one optional value to compact text."""

    if value is None:
        return ""

    return " ".join(
        str(value).split()
    )


def get_groq_model_pricing(
    model_name: str,
) -> tuple[float, float]:
    """Return reviewed input and output prices for one model."""

    normalized_model = normalize_text(
        model_name
    ).casefold()

    pricing = (
        GROQ_MODEL_PRICING_USD_PER_MILLION.get(
            normalized_model
        )
    )

    if pricing is None:
        raise LLMConfigurationError(
            "Groq pricing is not configured for model "
            f"'{model_name}'. Review and add its current "
            "pricing before enabling the model."
        )

    return pricing


def estimate_groq_cost_usd(
    *,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate request cost using reviewed public list prices."""

    (
        input_price_per_million,
        output_price_per_million,
    ) = get_groq_model_pricing(
        model_name
    )

    estimated_cost = (
        (
            max(
                0,
                int(input_tokens),
            )
            / 1_000_000
        )
        * input_price_per_million
        + (
            max(
                0,
                int(output_tokens),
            )
            / 1_000_000
        )
        * output_price_per_million
    )

    return round(
        estimated_cost,
        8,
    )


def convert_messages_for_groq(
    request: LLMRequest,
) -> list[dict[str, str]]:
    """Convert provider-independent messages to Groq messages."""

    converted_messages: list[
        dict[str, str]
    ] = []

    for message in request.messages:
        if message.role == "tool":
            raise LLMRequestValidationError(
                "Groq tool-result messages are not enabled "
                "during Day 35. Controlled tool execution "
                "will be added during the MCP stage."
            )

        converted_message = {
            "role": message.role,
            "content": message.content,
        }

        if message.name:
            converted_message[
                "name"
            ] = message.name

        converted_messages.append(
            converted_message
        )

    return converted_messages


def get_completion_usage(
    completion: Any,
) -> tuple[int, int, int]:
    """Read Groq-reported token usage safely."""

    usage = getattr(
        completion,
        "usage",
        None,
    )

    if usage is None:
        raise LLMProviderResponseError(
            "The Groq response did not include token usage."
        )

    input_tokens = int(
        getattr(
            usage,
            "prompt_tokens",
            0,
        )
        or 0
    )
    output_tokens = int(
        getattr(
            usage,
            "completion_tokens",
            0,
        )
        or 0
    )
    provider_total_tokens = int(
        getattr(
            usage,
            "total_tokens",
            input_tokens + output_tokens,
        )
        or 0
    )

    calculated_total_tokens = (
        input_tokens
        + output_tokens
    )

    if (
        provider_total_tokens
        < calculated_total_tokens
    ):
        raise LLMProviderResponseError(
            "The Groq response returned inconsistent "
            "token usage."
        )

    return (
        input_tokens,
        output_tokens,
        provider_total_tokens,
    )


def map_finish_reason(
    raw_finish_reason: object,
) -> str:
    """Map a Groq finish reason to the shared response model."""

    finish_reason = normalize_text(
        raw_finish_reason
    ).casefold()

    if finish_reason == "stop":
        return "stop"

    if finish_reason == "length":
        return "length"

    if finish_reason == "content_filter":
        return "content_filter"

    if finish_reason in {
        "tool_call",
        "tool_calls",
        "function_call",
    }:
        raise LLMProviderResponseError(
            "Groq returned a tool call while tools are "
            "disabled for Day 35."
        )

    raise LLMProviderResponseError(
        "Groq returned an unsupported finish reason: "
        f"'{finish_reason or 'missing'}'."
    )


class GroqProvider(BaseLLMProvider):
    """Groq Chat Completions adapter for the shared LLM layer."""

    provider_name = "groq"

    def __init__(
        self,
        config: LLMProviderConfig,
        *,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        super().__init__(
            config
        )

        get_groq_model_pricing(
            config.model_name
        )

        if client is not None:
            self._client = client
            return

        normalized_api_key = normalize_text(
            api_key
        )

        if not normalized_api_key:
            raise LLMConfigurationError(
                "GROQ_API_KEY is required when the Groq "
                "provider is selected."
            )

        self._client = AsyncGroq(
            api_key=normalized_api_key,
            max_retries=0,
            timeout=config.timeout_seconds,
        )

    def validate_preflight_cost(
        self,
        request: LLMRequest,
        *,
        model_name: str,
        requested_output_tokens: int,
    ) -> None:
        """Reject a request that could exceed its cost ceiling."""

        message_text = "\n".join(
            message.content
            for message in request.messages
        )
        estimated_input_tokens = estimate_tokens(
            message_text
        )

        maximum_estimated_cost = (
            estimate_groq_cost_usd(
                model_name=model_name,
                input_tokens=(
                    estimated_input_tokens
                ),
                output_tokens=(
                    requested_output_tokens
                ),
            )
        )

        maximum_allowed_cost = (
            request.max_estimated_cost_usd
            if (
                request.max_estimated_cost_usd
                is not None
            )
            else (
                self.config
                .max_estimated_cost_usd
            )
        )

        if (
            maximum_estimated_cost
            > maximum_allowed_cost
        ):
            raise LLMCostLimitExceededError(
                "The Groq request could cost up to "
                f"${maximum_estimated_cost:.8f}, which "
                "exceeds the configured estimated-cost "
                f"limit of ${maximum_allowed_cost:.8f}."
            )

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Perform one controlled Groq chat-completion request."""

        started_at = perf_counter()

        model_name = (
            normalize_text(
                request.model_name
            )
            or self.config.model_name
        )
        requested_output_tokens = (
            request.max_output_tokens
            or self.config.max_output_tokens
        )
        temperature = (
            request.temperature
            if request.temperature is not None
            else self.config.temperature
        )

        (
            input_price_per_million,
            output_price_per_million,
        ) = get_groq_model_pricing(
            model_name
        )

        self.validate_preflight_cost(
            request,
            model_name=model_name,
            requested_output_tokens=(
                requested_output_tokens
            ),
        )

        request_arguments: dict[
            str,
            Any,
        ] = {
            "model": model_name,
            "messages": (
                convert_messages_for_groq(
                    request
                )
            ),
            "temperature": temperature,
            "max_completion_tokens": (
                requested_output_tokens
            ),
            "stream": False,
        }

        if request.require_json_object:
            request_arguments[
                "response_format"
            ] = {
                "type": "json_object",
            }

        try:
            completion = (
                await self._client
                .chat
                .completions
                .create(
                    **request_arguments
                )
            )

        except groq.AuthenticationError as error:
            raise LLMAuthenticationError(
                "Groq rejected the configured API key."
            ) from error

        except groq.RateLimitError as error:
            raise LLMRateLimitError(
                "Groq rate limiting prevented the request."
            ) from error

        except groq.APITimeoutError as error:
            raise LLMTimeoutError(
                "The Groq request timed out."
            ) from error

        except groq.APIConnectionError as error:
            raise LLMTimeoutError(
                "The Groq API could not be reached."
            ) from error

        except groq.APIStatusError as error:
            status_code = int(
                getattr(
                    error,
                    "status_code",
                    0,
                )
                or 0
            )
            request_id = normalize_text(
                getattr(
                    error,
                    "request_id",
                    "",
                )
            )
            request_suffix = (
                f" Request ID: {request_id}."
                if request_id
                else ""
            )

            if status_code in {
                400,
                403,
                404,
                413,
                422,
            }:
                raise LLMRequestValidationError(
                    "Groq rejected the request with HTTP "
                    f"{status_code}.{request_suffix}"
                ) from error

            raise LLMProviderResponseError(
                "Groq returned an unsuccessful API status "
                f"({status_code}).{request_suffix}"
            ) from error

        except groq.APIError as error:
            raise LLMProviderResponseError(
                "Groq could not complete the API request."
            ) from error

        choices = (
            getattr(
                completion,
                "choices",
                None,
            )
            or []
        )

        if not choices:
            raise LLMProviderResponseError(
                "The Groq response did not contain a choice."
            )

        first_choice = choices[0]
        message = getattr(
            first_choice,
            "message",
            None,
        )

        if message is None:
            raise LLMProviderResponseError(
                "The Groq response did not contain a message."
            )

        refusal = normalize_text(
            getattr(
                message,
                "refusal",
                "",
            )
        )

        if refusal:
            raise LLMProviderResponseError(
                "Groq refused the request: "
                + refusal[:500]
            )

        tool_calls = (
            getattr(
                message,
                "tool_calls",
                None,
            )
            or []
        )

        if tool_calls:
            raise LLMProviderResponseError(
                "Groq returned tool calls while tools are "
                "disabled for Day 35."
            )

        raw_content = getattr(
            message,
            "content",
            None,
        )
        content = (
            str(raw_content).strip()
            if raw_content is not None
            else ""
        )

        if not content:
            raise LLMProviderResponseError(
                "The Groq response did not contain text."
            )

        structured_output: (
            dict[str, Any]
            | None
        ) = None

        if request.require_json_object:
            try:
                parsed_output = json.loads(
                    content
                )

            except JSONDecodeError as error:
                raise LLMProviderResponseError(
                    "The Groq response was not valid JSON."
                ) from error

            if not isinstance(
                parsed_output,
                dict,
            ):
                raise LLMProviderResponseError(
                    "The Groq structured response must be "
                    "a JSON object."
                )

            structured_output = parsed_output

        (
            input_tokens,
            output_tokens,
            provider_total_tokens,
        ) = get_completion_usage(
            completion
        )

        calculated_total_tokens = (
            input_tokens
            + output_tokens
        )
        estimated_cost_usd = (
            estimate_groq_cost_usd(
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )

        returned_model = (
            normalize_text(
                getattr(
                    completion,
                    "model",
                    "",
                )
            )
            or model_name
        )
        provider_response_id = normalize_text(
            getattr(
                completion,
                "id",
                "",
            )
        )
        provider_request_id = normalize_text(
            getattr(
                completion,
                "_request_id",
                "",
            )
        )
        finish_reason = map_finish_reason(
            getattr(
                first_choice,
                "finish_reason",
                "",
            )
        )

        return LLMResponse(
            request_id=request.request_id,
            provider_name=self.provider_name,
            model_name=returned_model,
            content=content,
            structured_output=(
                structured_output
            ),
            usage=LLMTokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=(
                    calculated_total_tokens
                ),
                estimated_cost_usd=(
                    estimated_cost_usd
                ),
            ),
            latency_ms=round(
                (
                    perf_counter()
                    - started_at
                )
                * 1000,
                2,
            ),
            finish_reason=finish_reason,
            prompt_name=request.prompt_name,
            prompt_version=(
                request.prompt_version
            ),
            agent_name=request.agent_name,
            agent_version=request.agent_version,
            provider_response_id=(
                provider_response_id
                or None
            ),
            used_mock_provider=False,
            metadata={
                "network_call": True,
                "provider_request_id": (
                    provider_request_id
                    or None
                ),
                "provider_total_tokens": (
                    provider_total_tokens
                ),
                "response_schema_name": (
                    request.response_schema_name
                ),
                "json_object_mode": (
                    request.require_json_object
                ),
                "pricing_model": model_name,
                "input_price_per_million_usd": (
                    input_price_per_million
                ),
                "output_price_per_million_usd": (
                    output_price_per_million
                ),
                "estimated_list_price_usd": (
                    estimated_cost_usd
                ),
                "actual_charge_not_verified": True,
                "tools_enabled": False,
            },
        )
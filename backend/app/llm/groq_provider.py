from __future__ import annotations

import json
from json import JSONDecodeError
import re
from time import perf_counter
from typing import Any

import groq
from groq import AsyncGroq

from backend.app.llm.base_provider import (
    BaseLLMProvider,
    estimate_request_input_tokens,
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
    LLMToolCall,
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


RESPONSE_JSON_SCHEMA_KEY = "response_json_schema"
RESPONSE_JSON_SCHEMA_NAME_KEY = "response_json_schema_name"
RESPONSE_JSON_SCHEMA_STRICT_KEY = "response_json_schema_strict"


def normalize_json_schema_name(
    value: object,
) -> str:
    """Create a provider-safe JSON Schema name."""

    normalized = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        normalize_text(value),
    ).strip("_")

    return (
        normalized[:64]
        or "structured_response"
    )


def build_groq_response_format(
    request: LLMRequest,
) -> tuple[dict[str, Any] | None, str]:
    """Resolve JSON Schema, JSON object, or normal text mode."""

    if not request.require_json_object:
        return None, "text"

    raw_schema = request.metadata.get(
        RESPONSE_JSON_SCHEMA_KEY
    )

    if isinstance(raw_schema, dict) and raw_schema:
        schema_name = normalize_json_schema_name(
            request.metadata.get(
                RESPONSE_JSON_SCHEMA_NAME_KEY
            )
            or request.response_schema_name
            or "structured_response"
        )

        strict_schema = bool(
            request.metadata.get(
                RESPONSE_JSON_SCHEMA_STRICT_KEY,
                False,
            )
        )

        return (
            {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": strict_schema,
                    "schema": raw_schema,
                },
            },
            "json_schema_strict"
            if strict_schema
            else "json_schema_best_effort",
        )

    return (
        {
            "type": "json_object",
        },
        "json_object",
    )


def get_safe_groq_error_detail(
    error: object,
) -> str:
    """Extract one bounded provider error message without request data."""

    body = getattr(
        error,
        "body",
        None,
    )
    candidate: object = ""

    if isinstance(
        body,
        dict,
    ):
        nested_error = body.get(
            "error"
        )

        if isinstance(
            nested_error,
            dict,
        ):
            candidate = nested_error.get(
                "message",
                "",
            )
        else:
            candidate = body.get(
                "message",
                "",
            )

    if not candidate:
        candidate = getattr(
            error,
            "message",
            "",
        )

    return normalize_text(
        candidate
    )[:1000]


MAXIMUM_GROQ_RETRY_AFTER_SECONDS = 300.0


def get_groq_retry_after_seconds(
    error: object,
) -> float | None:
    """Read Groq's HTTP retry-after header without exposing secrets."""

    response = getattr(
        error,
        "response",
        None,
    )
    headers = getattr(
        response,
        "headers",
        None,
    )

    if headers is None:
        return None

    raw_value: object | None = None

    try:
        raw_value = headers.get(
            "retry-after"
        )

        if raw_value is None:
            raw_value = headers.get(
                "Retry-After"
            )

    except Exception:
        return None

    if raw_value is None:
        return None

    try:
        retry_after = float(
            str(
                raw_value
            ).strip()
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    if retry_after < 0:
        return None

    return min(
        retry_after,
        MAXIMUM_GROQ_RETRY_AFTER_SECONDS,
    )


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


def convert_tool_call_for_groq(
    tool_call: LLMToolCall,
) -> dict[str, Any]:
    """Convert one shared tool call into Groq assistant history."""

    return {
        "id": tool_call.tool_call_id,
        "type": "function",
        "function": {
            "name": tool_call.tool_name,
            "arguments": json.dumps(
                tool_call.arguments,
                ensure_ascii=False,
                separators=(
                    ",",
                    ":",
                ),
            ),
        },
    }


def convert_messages_for_groq(
    request: LLMRequest,
) -> list[dict[str, Any]]:
    """Convert provider-independent messages to Groq messages."""

    converted_messages: list[
        dict[str, Any]
    ] = []

    for message in request.messages:
        converted_message: dict[
            str,
            Any,
        ] = {
            "role": message.role,
        }

        if message.role == "assistant":
            converted_message[
                "content"
            ] = (
                message.content
                if message.content
                else None
            )

            if message.tool_calls:
                converted_message[
                    "tool_calls"
                ] = [
                    convert_tool_call_for_groq(
                        tool_call
                    )
                    for tool_call in message.tool_calls
                ]

        elif message.role == "tool":
            if not message.tool_call_id:
                raise LLMRequestValidationError(
                    "Groq tool-result messages are not enabled while "
                    "controlled tool execution is disabled for "
                    "unlinked results. A tool_call_id is required."
                )

            converted_message[
                "content"
            ] = message.content
            converted_message[
                "tool_call_id"
            ] = message.tool_call_id

        else:
            converted_message[
                "content"
            ] = message.content

        if message.name:
            converted_message[
                "name"
            ] = message.name

        converted_messages.append(
            converted_message
        )

    return converted_messages


def convert_tools_for_groq(
    request: LLMRequest,
) -> list[dict[str, Any]]:
    """Convert controlled local tool definitions to Groq schemas."""

    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in request.tools
    ]


def parse_groq_tool_calls(
    *,
    raw_tool_calls: list[Any],
    request: LLMRequest,
) -> list[LLMToolCall]:
    """Validate and normalize Groq local tool-call requests."""

    if not raw_tool_calls:
        return []

    if request.tool_choice == "none":
        raise LLMProviderResponseError(
            "Groq returned tool calls while tool_choice='none'."
        )

    requested_tool_names = {
        tool.name
        for tool in request.tools
    }

    if not requested_tool_names:
        raise LLMProviderResponseError(
            "Groq returned tool calls when no tool definitions "
            "were supplied."
        )

    parsed_tool_calls: list[
        LLMToolCall
    ] = []
    seen_tool_call_ids: set[
        str
    ] = set()

    for raw_tool_call in raw_tool_calls:
        tool_call_id = normalize_text(
            getattr(
                raw_tool_call,
                "id",
                "",
            )
        )

        if not tool_call_id:
            raise LLMProviderResponseError(
                "Groq returned a tool call without an ID."
            )

        if tool_call_id in seen_tool_call_ids:
            raise LLMProviderResponseError(
                "Groq returned duplicate tool-call IDs."
            )

        call_type = normalize_text(
            getattr(
                raw_tool_call,
                "type",
                "function",
            )
        ).casefold()

        if call_type != "function":
            raise LLMProviderResponseError(
                "Groq returned an unsupported tool-call type."
            )

        function = getattr(
            raw_tool_call,
            "function",
            None,
        )

        if function is None:
            raise LLMProviderResponseError(
                "Groq returned a tool call without function data."
            )

        tool_name = normalize_text(
            getattr(
                function,
                "name",
                "",
            )
        )

        if (
            tool_name not in requested_tool_names
            or tool_name not in request.allowed_tools
        ):
            raise LLMProviderResponseError(
                "Groq requested an unapproved tool: "
                f"{tool_name or '<missing>'}."
            )

        raw_arguments = getattr(
            function,
            "arguments",
            None,
        )

        if not isinstance(
            raw_arguments,
            str,
        ):
            raise LLMProviderResponseError(
                "Groq tool-call arguments must be a JSON string."
            )

        try:
            parsed_arguments = json.loads(
                raw_arguments
            )

        except JSONDecodeError as error:
            raise LLMProviderResponseError(
                "Groq returned invalid JSON tool arguments."
            ) from error

        if not isinstance(
            parsed_arguments,
            dict,
        ):
            raise LLMProviderResponseError(
                "Groq tool-call arguments must decode to "
                "a JSON object."
            )

        parsed_tool_calls.append(
            LLMToolCall(
                tool_call_id=tool_call_id,
                tool_name=tool_name,
                arguments=parsed_arguments,
            )
        )

        seen_tool_call_ids.add(
            tool_call_id
        )

    return parsed_tool_calls


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
        return "tool_call"

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

        estimated_input_tokens = (
            estimate_request_input_tokens(
                request
            )
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

        if request.tools:
            request_arguments[
                "tools"
            ] = convert_tools_for_groq(
                request
            )
            request_arguments[
                "tool_choice"
            ] = request.tool_choice

            # Keep the provider turn deterministic. The application
            # executor/orchestration loop is added in Part 5B.
            request_arguments[
                "parallel_tool_calls"
            ] = False

        if model_name.casefold() in {
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
        }:
            # These business-language enhancement tasks do not need
            # medium/high reasoning effort. Low effort reduces avoidable
            # reasoning-token usage while retaining the GPT-OSS model.
            request_arguments[
                "reasoning_effort"
            ] = "low"
            request_arguments[
                "include_reasoning"
            ] = False

        if (
            request.tools
            and request.tool_choice != "none"
        ):
            # Tool-selection turns may legitimately return no content.
            # Final structured output is enforced after tool execution
            # with tool_choice='none' in Part 5B.
            response_format = None
            response_format_mode = "tool_call_selection"
        else:
            (
                response_format,
                response_format_mode,
            ) = build_groq_response_format(
                request
            )

        if response_format is not None:
            request_arguments[
                "response_format"
            ] = response_format

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
            retry_after_seconds = (
                get_groq_retry_after_seconds(
                    error
                )
            )

            message = (
                "Groq rate limiting prevented the request."
            )

            if retry_after_seconds is not None:
                message += (
                    " Retry after "
                    f"{retry_after_seconds:g} seconds."
                )

            controlled_error = (
                LLMRateLimitError(
                    message
                )
            )

            if retry_after_seconds is not None:
                setattr(
                    controlled_error,
                    "retry_after_seconds",
                    retry_after_seconds,
                )

            raise controlled_error from error

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
            error_detail = (
                get_safe_groq_error_detail(
                    error
                )
            )
            detail_suffix = (
                f" Provider detail: {error_detail}"
                if error_detail
                else ""
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
                    f"{status_code}.{detail_suffix}"
                    f"{request_suffix}"
                ) from error

            raise LLMProviderResponseError(
                "Groq returned an unsuccessful API status "
                f"({status_code}).{detail_suffix}"
                f"{request_suffix}"
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

        raw_tool_calls = (
            getattr(
                message,
                "tool_calls",
                None,
            )
            or []
        )

        finish_reason = map_finish_reason(
            getattr(
                first_choice,
                "finish_reason",
                "",
            )
        )

        tool_calls = parse_groq_tool_calls(
            raw_tool_calls=list(
                raw_tool_calls
            ),
            request=request,
        )

        if (
            finish_reason == "tool_call"
            and not tool_calls
        ):
            raise LLMProviderResponseError(
                "Groq returned a tool-call finish reason "
                "without tool_calls."
            )

        if (
            tool_calls
            and finish_reason != "tool_call"
        ):
            raise LLMProviderResponseError(
                "Groq returned tool_calls without a "
                "tool-call finish reason."
            )

        raw_content = getattr(
            message,
            "content",
            None,
        )
        content = (
            str(
                raw_content
            ).strip()
            if raw_content is not None
            else ""
        )

        structured_output: (
            dict[str, Any]
            | None
        ) = None

        if not tool_calls:
            if not content:
                raise LLMProviderResponseError(
                    "The Groq response did not contain text."
                )

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
        return LLMResponse(
            request_id=request.request_id,
            provider_name=self.provider_name,
            model_name=returned_model,
            content=content,
            structured_output=(
                structured_output
            ),
            tool_calls=tool_calls,
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
                    response_format_mode
                    == "json_object"
                ),
                "response_format_mode": (
                    response_format_mode
                ),
                "json_schema_strict": (
                    True
                    if response_format_mode
                    == "json_schema_strict"
                    else False
                    if response_format_mode
                    == "json_schema_best_effort"
                    else None
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
                "tools_enabled": bool(
                    request.tools
                ),
                "tool_choice": (
                    request.tool_choice
                    if request.tools
                    else None
                ),
                "tool_call_count": len(
                    tool_calls
                ),
            },
        )

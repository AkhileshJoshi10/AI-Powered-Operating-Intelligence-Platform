from __future__ import annotations

import asyncio
import json
from time import perf_counter
from typing import Any
from uuid import uuid4

from backend.app.llm.base_provider import (
    BaseLLMProvider,
    estimate_tokens,
)
from backend.app.llm.llm_exceptions import (
    LLMAuthenticationError,
    LLMProviderResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from backend.app.llm.llm_models import (
    LLMRequest,
    LLMResponse,
    LLMTokenUsage,
)


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic provider used for development and automated tests.

    It performs no network call and incurs no API cost.
    """

    provider_name = "mock"

    async def _generate_once(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        started_at = perf_counter()

        simulated_error = str(
            request.metadata.get(
                "mock_error",
                "",
            )
        ).strip().casefold()

        if simulated_error == "timeout":
            raise LLMTimeoutError(
                "Simulated mock-provider timeout."
            )

        if simulated_error == "rate_limit":
            raise LLMRateLimitError(
                "Simulated mock-provider rate limit."
            )

        if simulated_error == "authentication":
            raise LLMAuthenticationError(
                "Simulated mock-provider authentication failure."
            )

        if simulated_error == "provider_response":
            raise LLMProviderResponseError(
                "Simulated invalid provider response."
            )

        delay_seconds = float(
            request.metadata.get(
                "mock_delay_seconds",
                0.0,
            )
        )

        if delay_seconds > 0:
            await asyncio.sleep(
                delay_seconds
            )

        configured_output = request.metadata.get(
            "mock_structured_output"
        )

        if isinstance(configured_output, dict):
            structured_output: dict[str, Any] = dict(
                configured_output
            )
        else:
            structured_output = {
                "status": "success",
                "agent_name": request.agent_name,
                "prompt_name": request.prompt_name,
                "prompt_version": request.prompt_version,
                "message": (
                    "Deterministic mock LLM response."
                ),
                "evidence_warning": None,
            }

        configured_content = request.metadata.get(
            "mock_content"
        )

        if configured_content is None:
            content = json.dumps(
                structured_output,
                ensure_ascii=False,
                sort_keys=True,
            )
        else:
            content = str(
                configured_content
            )

        input_text = "\n".join(
            message.content
            for message in request.messages
        )

        input_tokens = estimate_tokens(
            input_text
        )
        output_tokens = estimate_tokens(
            content
        )

        return LLMResponse(
            request_id=request.request_id,
            provider_name=self.provider_name,
            model_name=(
                request.model_name
                or self.config.model_name
            ),
            content=content,
            structured_output=structured_output,
            usage=LLMTokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=(
                    input_tokens
                    + output_tokens
                ),
                estimated_cost_usd=0.0,
            ),
            latency_ms=round(
                (
                    perf_counter()
                    - started_at
                )
                * 1000,
                2,
            ),
            finish_reason="stop",
            prompt_name=request.prompt_name,
            prompt_version=request.prompt_version,
            agent_name=request.agent_name,
            agent_version=request.agent_version,
            provider_response_id=uuid4().hex,
            used_mock_provider=True,
            metadata={
                "network_call": False,
                "api_cost_incurred": False,
            },
        )

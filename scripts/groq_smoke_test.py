from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv


load_dotenv()


async def main(
) -> None:
    """Run one controlled live Groq call."""

    from backend.app.llm.groq_provider import (
        GroqProvider,
    )
    from backend.app.llm.llm_models import (
        LLMMessage,
        LLMProviderConfig,
        LLMRequest,
    )

    api_key = os.getenv(
        "GROQ_API_KEY",
        "",
    ).strip()

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing from .env."
        )

    model_name = os.getenv(
        "GROQ_SMOKE_MODEL",
        "openai/gpt-oss-20b",
    ).strip()

    provider = GroqProvider(
        LLMProviderConfig(
            enabled=True,
            provider_name="groq",
            model_name=model_name,
            timeout_seconds=30.0,
            max_retries=0,
            retry_backoff_seconds=0.0,
            max_input_tokens=1000,
            max_output_tokens=200,
            max_estimated_cost_usd=0.002,
            temperature=0.0,
            mask_sensitive_data=True,
            allowed_tools=[],
        ),
        api_key=api_key,
    )

    request = LLMRequest(
        agent_name="Groq Smoke Test",
        agent_version="1.0.0",
        prompt_name="groq_live_smoke",
        prompt_version="v1",
        messages=[
            LLMMessage(
                role="system",
                content=(
                    "Return exactly one JSON object. "
                    "Use exactly the requested keys and values. "
                    "Do not add commentary or use tools."
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    "Return status as ready, issue_count "
                    "as 2, and human_review_required as true."
                ),
            ),
        ],
        response_schema_name="GroqLiveSmokeV1",
        model_name=model_name,
        max_output_tokens=200,
        timeout_seconds=30.0,
        max_retries=0,
        max_estimated_cost_usd=0.002,
        allowed_tools=[],
        require_json_object=True,
    )

    response = await provider.generate(
        request
    )

    expected_output = {
        "status": "ready",
        "issue_count": 2,
        "human_review_required": True,
    }

    if (
        response.structured_output
        != expected_output
    ):
        raise RuntimeError(
            "Groq returned unexpected structured output: "
            f"{response.structured_output!r}"
        )

    print(
        "Provider:",
        response.provider_name,
    )
    print(
        "Model:",
        response.model_name,
    )
    print(
        "Structured output:",
        response.structured_output,
    )
    print(
        "Tokens:",
        response.usage.total_tokens,
    )
    print(
        "Estimated list-price cost USD:",
        response.usage.estimated_cost_usd,
    )
    print(
        "Groq request ID:",
        response.metadata.get(
            "provider_request_id"
        ),
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
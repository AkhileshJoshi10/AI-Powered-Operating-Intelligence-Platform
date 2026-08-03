from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def generate_run_id() -> str:
    """Generate a unique identifier for one agent execution flow."""

    return uuid4().hex


class AgentContext(BaseModel):
    """
    Shared input context passed to agents.

    The context is provider-independent and can carry deterministic
    analytics results, issue identifiers, earlier agent outputs, and
    request metadata.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    run_id: str = Field(
        default_factory=generate_run_id,
        min_length=1,
    )

    run_type: str = Field(
        default="manual",
        min_length=1,
        max_length=100,
    )

    requested_by: str | None = Field(
        default=None,
        max_length=150,
    )

    issue_ids: list[str] = Field(
        default_factory=list,
    )

    input_data: dict[str, Any] = Field(
        default_factory=dict,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    created_at: datetime = Field(
        default_factory=current_utc_time,
    )

    @field_validator(
        "run_id",
        "run_type",
        mode="before",
    )
    @classmethod
    def clean_required_text(
        cls,
        value: object,
    ) -> str:
        """Normalize required text fields."""

        cleaned_value = " ".join(
            str(value).split()
        )

        if not cleaned_value:
            raise ValueError(
                "The value cannot be empty."
            )

        return cleaned_value

    @field_validator(
        "requested_by",
        mode="before",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: object,
    ) -> str | None:
        """Normalize optional text fields."""

        if value is None:
            return None

        cleaned_value = " ".join(
            str(value).split()
        )

        if not cleaned_value:
            return None

        return cleaned_value

    @field_validator(
        "issue_ids",
        mode="before",
    )
    @classmethod
    def clean_issue_ids(
        cls,
        value: object,
    ) -> list[str]:
        """Normalize and deduplicate issue identifiers."""

        if value is None:
            return []

        if not isinstance(value, list):
            raise ValueError(
                "issue_ids must be provided as a list."
            )

        cleaned_issue_ids: list[str] = []

        for issue_id in value:
            cleaned_issue_id = " ".join(
                str(issue_id).split()
            )

            if (
                cleaned_issue_id
                and cleaned_issue_id
                not in cleaned_issue_ids
            ):
                cleaned_issue_ids.append(
                    cleaned_issue_id
                )

        return cleaned_issue_ids
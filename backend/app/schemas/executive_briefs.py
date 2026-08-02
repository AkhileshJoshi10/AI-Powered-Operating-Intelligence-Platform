from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel


class ExecutiveBriefItem(BaseModel):
    """One stored executive business brief."""

    brief_id: int
    brief_date: date
    brief_type: str

    summary_text: str
    brief_data: dict[str, Any]

    status: str

    created_at: datetime
    updated_at: datetime


class LatestExecutiveBriefResponse(BaseModel):
    """Response containing the latest stored executive brief."""

    status: Literal["success"] = "success"
    generated_at: datetime

    brief: ExecutiveBriefItem
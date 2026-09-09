from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


AppUserRole = Literal[
    "Admin",
    "Manager",
    "Viewer",
]


class AppUserCreateRequest(BaseModel):
    """Internal/bootstrap request for one application user."""

    model_config = ConfigDict(
        extra="forbid",
    )

    email: str = Field(
        min_length=3,
        max_length=320,
    )
    full_name: str = Field(
        min_length=2,
        max_length=150,
    )
    password: str = Field(
        min_length=12,
        max_length=128,
    )
    role: AppUserRole


class AppUserItem(BaseModel):
    """Public-safe application-user representation."""

    user_id: int
    email: str
    full_name: str
    role: AppUserRole
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

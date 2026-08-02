from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text

from backend.app.db.database import engine


def serialize_executive_brief(
    row: Any,
) -> dict[str, Any]:
    """Convert a database row into API-compatible data."""

    brief_data = row["brief_data"]

    if brief_data is None:
        brief_data = {}

    return {
        "brief_id": int(
            row["brief_id"]
        ),
        "brief_date": row["brief_date"],
        "brief_type": str(
            row["brief_type"]
        ).strip(),
        "summary_text": str(
            row["summary_text"]
        ).strip(),
        "brief_data": brief_data,
        "status": str(
            row["status"]
        ).strip(),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_latest_executive_brief() -> dict[str, Any] | None:
    """Return the latest stored executive brief."""

    query = text(
        """
        SELECT
            brief_id,
            brief_date,
            brief_type,
            summary_text,
            brief_data,
            status,
            created_at,
            updated_at
        FROM executive_briefs
        ORDER BY
            brief_date DESC,
            created_at DESC,
            brief_id DESC
        LIMIT 1;
        """
    )

    with engine.connect() as connection:
        row = (
            connection.execute(query)
            .mappings()
            .first()
        )

    if row is None:
        return None

    return {
        "status": "success",
        "generated_at": datetime.now(),
        "brief": serialize_executive_brief(
            row
        ),
    }
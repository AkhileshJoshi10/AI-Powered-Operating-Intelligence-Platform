from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.db.database import engine


def build_import_history_filters(
    *,
    dataset_name: str | None,
    import_status: str | None,
) -> tuple[str, dict[str, Any]]:
    """Build parameterized filters for import-history queries."""

    conditions: list[str] = []
    parameters: dict[str, Any] = {}

    if dataset_name is not None:
        conditions.append(
            "LOWER(TRIM(dataset_name)) = LOWER(TRIM(:dataset_name))"
        )
        parameters["dataset_name"] = dataset_name

    if import_status is not None:
        conditions.append(
            "LOWER(TRIM(import_status)) = LOWER(TRIM(:import_status))"
        )
        parameters["import_status"] = import_status

    if not conditions:
        return "", parameters

    return (
        " WHERE " + " AND ".join(conditions),
        parameters,
    )


def serialize_import_history_row(
    row: Any,
) -> dict[str, Any]:
    """Convert one database row into API-compatible data."""

    return {
        "import_id": int(row["import_id"]),
        "dataset_name": str(
            row["dataset_name"]
        ).strip(),
        "source_file_name": str(
            row["source_file_name"]
        ).strip(),
        "total_rows": int(
            row["total_rows"] or 0
        ),
        "successful_rows": int(
            row["successful_rows"] or 0
        ),
        "failed_rows": int(
            row["failed_rows"] or 0
        ),
        "import_status": str(
            row["import_status"]
        ).strip(),
        "error_message": (
            str(row["error_message"]).strip()
            if row["error_message"] is not None
            else None
        ),
        "imported_at": row["imported_at"],
    }


def get_import_history(
    *,
    dataset_name: str | None,
    import_status: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """Return filtered and paginated dataset-import history."""

    (
        where_clause,
        parameters,
    ) = build_import_history_filters(
        dataset_name=dataset_name,
        import_status=import_status,
    )

    total_count_query = text(
        """
        SELECT COUNT(*)
        FROM data_import_logs;
        """
    )

    matching_count_query = text(
        f"""
        SELECT COUNT(*)
        FROM data_import_logs
        {where_clause};
        """
    )

    history_query = text(
        f"""
        SELECT
            import_id,
            dataset_name,
            source_file_name,
            total_rows,
            successful_rows,
            failed_rows,
            import_status,
            error_message,
            imported_at
        FROM data_import_logs
        {where_clause}
        ORDER BY
            imported_at DESC,
            import_id DESC
        LIMIT :limit
        OFFSET :offset;
        """
    )

    query_parameters = {
        **parameters,
        "limit": limit,
        "offset": offset,
    }

    try:
        with engine.connect() as connection:
            total_records = int(
                connection.execute(
                    total_count_query
                ).scalar_one()
            )

            matching_records = int(
                connection.execute(
                    matching_count_query,
                    parameters,
                ).scalar_one()
            )

            rows = (
                connection.execute(
                    history_query,
                    query_parameters,
                )
                .mappings()
                .all()
            )

    except SQLAlchemyError:
        raise

    import_records = [
        serialize_import_history_row(row)
        for row in rows
    ]

    return {
        "status": "success",
        "generated_at": datetime.now(),
        "total_records": total_records,
        "matching_records": matching_records,
        "limit": limit,
        "offset": offset,
        "imports": import_records,
    }
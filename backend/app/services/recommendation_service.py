from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from backend.app.db.database import engine


RECOMMENDATION_LIST_COLUMNS = """
    r.recommendation_id,
    r.issue_id,
    r.recommendation_title,
    r.suggested_owner_role,
    r.suggested_deadline,
    r.expected_impact,
    r.confidence_score,
    r.status,
    i.title AS issue_title,
    i.business_area,
    i.priority_level,
    i.priority_score,
    r.created_at,
    r.updated_at
"""


EDITABLE_RECOMMENDATION_COLUMNS = {
    "recommendation_title": "recommendation_title",
    "recommendation_text": "recommendation_text",
    "suggested_owner_role": "suggested_owner_role",
    "suggested_deadline": "suggested_deadline",
    "expected_impact": "expected_impact",
}


REVIEWABLE_STATUSES = {
    "Pending Review",
    "Edited",
}


def get_recommendation_list(
    *,
    recommendation_status: str | None,
    owner_role: str | None,
    business_area: str | None,
    limit: int,
    offset: int,
) -> dict:
    """Return filtered and paginated recommendations."""

    count_query = text(
        """
        SELECT COUNT(*)
        FROM recommendations AS r
        INNER JOIN issues AS i
            ON i.issue_id = r.issue_id
        WHERE
            (
                :recommendation_status IS NULL
                OR r.status = :recommendation_status
            )
            AND (
                :owner_role IS NULL
                OR r.suggested_owner_role = :owner_role
            )
            AND (
                :business_area IS NULL
                OR i.business_area = :business_area
            );
        """
    )

    recommendations_query = text(
        f"""
        SELECT
            {RECOMMENDATION_LIST_COLUMNS}
        FROM recommendations AS r
        INNER JOIN issues AS i
            ON i.issue_id = r.issue_id
        WHERE
            (
                :recommendation_status IS NULL
                OR r.status = :recommendation_status
            )
            AND (
                :owner_role IS NULL
                OR r.suggested_owner_role = :owner_role
            )
            AND (
                :business_area IS NULL
                OR i.business_area = :business_area
            )
        ORDER BY
            CASE i.priority_level
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            i.priority_score DESC,
            r.confidence_score DESC NULLS LAST,
            r.recommendation_id
        LIMIT :limit
        OFFSET :offset;
        """
    )

    parameters = {
        "recommendation_status": recommendation_status,
        "owner_role": owner_role,
        "business_area": business_area,
        "limit": limit,
        "offset": offset,
    }

    with engine.connect() as connection:
        total_items = connection.execute(
            count_query,
            parameters,
        ).scalar_one()

        rows = connection.execute(
            recommendations_query,
            parameters,
        ).mappings().all()

    return {
        "status": "success",
        "total_items": int(total_items),
        "limit": limit,
        "offset": offset,
        "items": [dict(row) for row in rows],
    }


def get_recommendation_detail(
    recommendation_id: int,
) -> dict | None:
    """Return one recommendation with issue and root-cause context."""

    recommendation_query = text(
        """
        SELECT
            r.recommendation_id,
            r.issue_id,
            r.recommendation_title,
            r.recommendation_text,
            r.suggested_owner_role,
            r.suggested_deadline,
            r.expected_impact,
            r.confidence_score,
            r.status,

            i.title AS issue_title,
            i.issue_type,
            i.business_area,
            i.priority_level,
            i.priority_score,
            i.status AS issue_status,

            rc.root_cause_category,
            rc.root_cause_summary,
            rc.root_cause_explanation,
            rc.confidence_score AS root_cause_confidence,
            rc.review_status AS root_cause_review_status,

            r.created_at,
            r.updated_at

        FROM recommendations AS r

        INNER JOIN issues AS i
            ON i.issue_id = r.issue_id

        LEFT JOIN root_cause_analyses AS rc
            ON rc.issue_id = r.issue_id

        WHERE r.recommendation_id = :recommendation_id

        ORDER BY
            rc.analysis_version DESC NULLS LAST,
            rc.updated_at DESC NULLS LAST

        LIMIT 1;
        """
    )

    parameters = {
        "recommendation_id": recommendation_id,
    }

    with engine.connect() as connection:
        row = connection.execute(
            recommendation_query,
            parameters,
        ).mappings().one_or_none()

    if row is None:
        return None

    return {
        "status": "success",
        "recommendation": dict(row),
    }


def get_locked_recommendation_status(
    connection: Connection,
    recommendation_id: int,
) -> str | None:
    """Lock and return the current status of one recommendation."""

    query = text(
        """
        SELECT status
        FROM recommendations
        WHERE recommendation_id = :recommendation_id
        FOR UPDATE;
        """
    )

    row = connection.execute(
        query,
        {
            "recommendation_id": recommendation_id,
        },
    ).mappings().one_or_none()

    if row is None:
        return None

    return str(row["status"])


def change_recommendation_status(
    recommendation_id: int,
    target_status: str,
) -> dict:
    """Accept or reject a reviewable recommendation."""

    with engine.begin() as connection:
        current_status = get_locked_recommendation_status(
            connection,
            recommendation_id,
        )

        if current_status is None:
            return {
                "outcome": "not_found",
            }

        if current_status not in REVIEWABLE_STATUSES:
            return {
                "outcome": "conflict",
                "current_status": current_status,
            }

        update_query = text(
            """
            UPDATE recommendations
            SET
                status = :target_status,
                updated_at = CURRENT_TIMESTAMP
            WHERE recommendation_id = :recommendation_id;
            """
        )

        connection.execute(
            update_query,
            {
                "target_status": target_status,
                "recommendation_id": recommendation_id,
            },
        )

    updated_recommendation = get_recommendation_detail(
        recommendation_id
    )

    return {
        "outcome": "success",
        "response": updated_recommendation,
    }


def edit_recommendation(
    recommendation_id: int,
    update_data: dict,
) -> dict:
    """Update manager-editable fields and mark the record as Edited."""

    valid_updates = {
        field_name: field_value
        for field_name, field_value in update_data.items()
        if field_name in EDITABLE_RECOMMENDATION_COLUMNS
    }

    set_fragments = [
        (
            f"{EDITABLE_RECOMMENDATION_COLUMNS[field_name]} "
            f"= :{field_name}"
        )
        for field_name in valid_updates
    ]

    set_fragments.extend(
        [
            "status = 'Edited'",
            "updated_at = CURRENT_TIMESTAMP",
        ]
    )

    set_clause = ",\n                ".join(set_fragments)

    update_query = text(
        f"""
        UPDATE recommendations
        SET
            {set_clause}
        WHERE recommendation_id = :recommendation_id;
        """
    )

    parameters = {
        **valid_updates,
        "recommendation_id": recommendation_id,
    }

    with engine.begin() as connection:
        current_status = get_locked_recommendation_status(
            connection,
            recommendation_id,
        )

        if current_status is None:
            return {
                "outcome": "not_found",
            }

        if current_status not in REVIEWABLE_STATUSES:
            return {
                "outcome": "conflict",
                "current_status": current_status,
            }

        connection.execute(
            update_query,
            parameters,
        )

    updated_recommendation = get_recommendation_detail(
        recommendation_id
    )

    return {
        "outcome": "success",
        "response": updated_recommendation,
    }
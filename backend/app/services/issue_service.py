from __future__ import annotations

from sqlalchemy import text

from backend.app.db.database import engine


ISSUE_COLUMNS = """
    issue_id,
    title,
    issue_type,
    business_area,
    priority_level,
    priority_score,
    priority_reason,
    status,
    entity_type,
    entity_id,
    store_id,
    product_id,
    vendor_id,
    period_label,
    finding_count,
    high_finding_count,
    medium_finding_count,
    low_finding_count,
    root_cause_status,
    summary,
    evidence_summary,
    created_at,
    updated_at,
    last_detected_at
"""


def get_issue_list(
    *,
    priority: str | None,
    business_area: str | None,
    issue_status: str | None,
    limit: int,
    offset: int,
) -> dict:
    """Return filtered and paginated issues from PostgreSQL."""

    count_query = text(
        """
        SELECT COUNT(*)
        FROM issues
        WHERE
            (:priority IS NULL OR priority_level = :priority)
            AND (
                :business_area IS NULL
                OR business_area = :business_area
            )
            AND (
                :issue_status IS NULL
                OR status = :issue_status
            );
        """
    )

    issues_query = text(
        f"""
        SELECT
            {ISSUE_COLUMNS}
        FROM issues
        WHERE
            (:priority IS NULL OR priority_level = :priority)
            AND (
                :business_area IS NULL
                OR business_area = :business_area
            )
            AND (
                :issue_status IS NULL
                OR status = :issue_status
            )
        ORDER BY
            CASE priority_level
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            priority_score DESC,
            last_detected_at DESC
        LIMIT :limit
        OFFSET :offset;
        """
    )

    parameters = {
        "priority": priority,
        "business_area": business_area,
        "issue_status": issue_status,
        "limit": limit,
        "offset": offset,
    }

    with engine.connect() as connection:
        total_items = connection.execute(
            count_query,
            parameters,
        ).scalar_one()

        rows = connection.execute(
            issues_query,
            parameters,
        ).mappings().all()

    return {
        "status": "success",
        "total_items": int(total_items),
        "limit": limit,
        "offset": offset,
        "items": [dict(row) for row in rows],
    }


def get_issue_detail(issue_id: str) -> dict | None:
    """Return one issue with its evidence and root-cause analysis."""

    issue_query = text(
        f"""
        SELECT
            {ISSUE_COLUMNS}
        FROM issues
        WHERE issue_id = :issue_id;
        """
    )

    evidence_query = text(
        """
        SELECT
            evidence_id,
            source_finding_id,
            source_report,
            source_module,
            analysis_type,
            business_area,
            severity,
            entity_type,
            entity_id,
            store_id,
            product_id,
            vendor_id,
            summary,
            evidence,
            detected_at,
            created_at
        FROM issue_evidence
        WHERE issue_id = :issue_id
        ORDER BY
            CASE severity
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            detected_at DESC NULLS LAST,
            evidence_id;
        """
    )

    root_cause_query = text(
        """
        SELECT
            root_cause_analysis_id,
            root_cause_category,
            root_cause_summary,
            root_cause_explanation,
            confidence_score,
            evidence_count,
            analysis_status,
            review_status,
            analysis_version,
            generated_at,
            reviewed_at,
            updated_at
        FROM root_cause_analyses
        WHERE issue_id = :issue_id;
        """
    )

    parameters = {"issue_id": issue_id}

    with engine.connect() as connection:
        issue_row = connection.execute(
            issue_query,
            parameters,
        ).mappings().one_or_none()

        if issue_row is None:
            return None

        evidence_rows = connection.execute(
            evidence_query,
            parameters,
        ).mappings().all()

        root_cause_row = connection.execute(
            root_cause_query,
            parameters,
        ).mappings().one_or_none()

    return {
        "status": "success",
        "issue": dict(issue_row),
        "evidence_count": len(evidence_rows),
        "evidence": [
            dict(evidence_row)
            for evidence_row in evidence_rows
        ],
        "root_cause": (
            dict(root_cause_row)
            if root_cause_row is not None
            else None
        ),
    }
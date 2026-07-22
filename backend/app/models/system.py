from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base


class Issue(Base):
    """Consolidated business issue detected by the analytics pipeline."""

    __tablename__ = "issues"

    __table_args__ = (
        CheckConstraint(
            "priority_level IN ('High', 'Medium', 'Low')",
            name="issues_priority_level_check",
        ),
        CheckConstraint(
            "status IN ('Open', 'In Progress', 'Resolved', 'Rejected')",
            name="issues_status_check",
        ),
    )

    issue_id: Mapped[str] = mapped_column(
        String(220),
        primary_key=True,
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    issue_type: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    business_area: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    priority_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    priority_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    priority_reason: Mapped[str | None] = mapped_column(
        Text,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Open'"),
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(100),
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(150),
    )
    store_id: Mapped[str | None] = mapped_column(
        String(20),
    )
    product_id: Mapped[str | None] = mapped_column(
        String(20),
    )
    vendor_id: Mapped[str | None] = mapped_column(
        String(20),
    )
    period_label: Mapped[str | None] = mapped_column(
        String(30),
    )

    finding_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    high_finding_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    medium_finding_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    low_finding_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    root_cause_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Pending'"),
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
    )
    evidence_summary: Mapped[str | None] = mapped_column(
        Text,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class IssueEvidence(Base):
    """Analytical evidence supporting a consolidated issue."""

    __tablename__ = "issue_evidence"

    __table_args__ = (
        UniqueConstraint(
            "issue_id",
            "source_finding_id",
            name="unique_issue_evidence",
        ),
    )

    evidence_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    issue_id: Mapped[str] = mapped_column(
        String(220),
        ForeignKey(
            "issues.issue_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    source_finding_id: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )
    source_report: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    source_module: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    analysis_type: Mapped[str | None] = mapped_column(
        String(150),
    )
    business_area: Mapped[str | None] = mapped_column(
        String(150),
    )
    severity: Mapped[str | None] = mapped_column(
        String(20),
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(100),
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(150),
    )
    store_id: Mapped[str | None] = mapped_column(
        String(20),
    )
    product_id: Mapped[str | None] = mapped_column(
        String(20),
    )
    vendor_id: Mapped[str | None] = mapped_column(
        String(20),
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
    )
    evidence: Mapped[str | None] = mapped_column(
        Text,
    )
    detected_at: Mapped[datetime | None] = mapped_column(
        DateTime,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class RootCauseAnalysis(Base):
    """Root-cause analysis generated for one business issue."""

    __tablename__ = "root_cause_analyses"

    __table_args__ = (
        CheckConstraint(
            "analysis_status IN "
            "('Generated', 'Reviewed', 'Superseded')",
            name="root_cause_analysis_status_check",
        ),
        CheckConstraint(
            "review_status IN "
            "('Pending Review', 'Accepted', 'Edited', 'Rejected')",
            name="root_cause_review_status_check",
        ),
    )

    root_cause_analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    issue_id: Mapped[str] = mapped_column(
        String(220),
        ForeignKey(
            "issues.issue_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        unique=True,
    )

    root_cause_category: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    root_cause_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    root_cause_explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
    )
    supporting_evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    analysis_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Generated'"),
    )
    review_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Pending Review'"),
    )
    reviewer_name: Mapped[str | None] = mapped_column(
        String(150),
    )
    review_notes: Mapped[str | None] = mapped_column(
        Text,
    )

    analysis_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class Recommendation(Base):
    """Management recommendation linked to a business issue."""

    __tablename__ = "recommendations"

    recommendation_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    issue_id: Mapped[str] = mapped_column(
        String(220),
        ForeignKey(
            "issues.issue_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    recommendation_title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    recommendation_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    suggested_owner_role: Mapped[str | None] = mapped_column(
        String(100),
    )
    suggested_deadline: Mapped[date | None] = mapped_column(
        Date,
    )
    expected_impact: Mapped[str | None] = mapped_column(
        Text,
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Pending Review'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class Task(Base):
    """Actionable task created from an accepted recommendation."""

    __tablename__ = "tasks"

    task_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    issue_id: Mapped[str | None] = mapped_column(
        String(220),
        ForeignKey(
            "issues.issue_id",
            ondelete="SET NULL",
        ),
    )
    recommendation_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "recommendations.recommendation_id",
            ondelete="SET NULL",
        ),
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
    )
    assigned_to: Mapped[str | None] = mapped_column(
        String(150),
    )
    assigned_role: Mapped[str | None] = mapped_column(
        String(100),
    )
    due_date: Mapped[date | None] = mapped_column(
        Date,
    )
    priority_level: Mapped[str | None] = mapped_column(
        String(20),
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Unassigned'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class AutomationLog(Base):
    """Execution history for automated workflows."""

    __tablename__ = "automation_logs"

    automation_log_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    task_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "tasks.task_id",
            ondelete="SET NULL",
        ),
    )
    workflow_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    execution_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    message: Mapped[str | None] = mapped_column(
        Text,
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class ExecutiveBrief(Base):
    """Daily or scheduled executive business brief."""

    __tablename__ = "executive_briefs"

    brief_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    brief_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    brief_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    brief_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'Draft'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )


class AgentRun(Base):
    """Execution history for an AI agent."""

    __tablename__ = "agent_runs"

    agent_run_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    run_type: Mapped[str | None] = mapped_column(
        String(100),
    )
    execution_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    input_summary: Mapped[str | None] = mapped_column(
        Text,
    )
    output_summary: Mapped[str | None] = mapped_column(
        Text,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
    )


class AuditLog(Base):
    """Audit history for important user and system actions."""

    __tablename__ = "audit_logs"

    audit_log_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(220),
    )
    action_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    actor_name: Mapped[str | None] = mapped_column(
        String(150),
    )
    old_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
    )
    new_value: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
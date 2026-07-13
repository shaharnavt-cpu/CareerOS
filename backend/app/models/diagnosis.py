"""Career Diagnosis and lightweight feedback persistence models."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DiagnosisSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One persisted diagnosis request and its current execution status."""

    __tablename__ = "diagnosis_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('RUNNING', 'COMPLETE', 'NEEDS_MEMORY', 'FAILED')",
            name="diagnosis_session_status_values",
        ),
        Index("idx_diagnosis_sessions_user_id", "user_id"),
        Index("idx_diagnosis_sessions_user_status", "user_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    target_role: Mapped[str | None] = mapped_column(Text)
    target_context: Mapped[str | None] = mapped_column(Text)
    frustration_context: Mapped[str | None] = mapped_column(Text)
    selected_focus: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="RUNNING", server_default="RUNNING"
    )


class DiagnosisResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Structured, inspectable output for one diagnosis session."""

    __tablename__ = "diagnosis_results"
    __table_args__ = (
        UniqueConstraint("session_id"),
        Index("idx_diagnosis_results_user_id", "user_id"),
        Index("idx_diagnosis_results_session_id", "session_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnosis_sessions.id"), nullable=False
    )
    career_identity: Mapped[str] = mapped_column(Text, nullable=False)
    identity_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_map: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    recognition_gap: Mapped[str] = mapped_column(Text, nullable=False)
    missing_proof: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    proof_sprint: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    do_not_waste_time: Mapped[str] = mapped_column(Text, nullable=False)
    exact_next_actions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    exact_messages: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    feedback_event_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    diagnosis_version: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="local-deterministic-v0",
        server_default="local-deterministic-v0",
    )


class CareerFeedbackEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User-authored learning input kept distinct from canonical Career Memory."""

    __tablename__ = "career_feedback_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('ARTIFACT_SUCCESS', 'APPLICATION_OUTCOME', "
            "'DRAFT_FEEDBACK', 'POSITIONING_RULE', 'MEMORY_USAGE_RULE', "
            "'GENERAL_LEARNING', 'UNKNOWN')",
            name="career_feedback_event_type_values",
        ),
        CheckConstraint(
            "status IN ('PROPOSED', 'APPROVED', 'ARCHIVED')",
            name="career_feedback_status_values",
        ),
        Index("idx_career_feedback_user_id", "user_id"),
        Index("idx_career_feedback_user_status", "user_id", "status"),
        Index("idx_career_feedback_opportunity_id", "related_opportunity_id"),
        Index("idx_career_feedback_draft_id", "related_draft_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    raw_note: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    structured_summary: Mapped[str] = mapped_column(Text, nullable=False)
    related_memory_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    related_opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_opportunities.id")
    )
    related_draft_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_drafts.id")
    )
    suggested_future_use: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="PROPOSED", server_default="PROPOSED"
    )

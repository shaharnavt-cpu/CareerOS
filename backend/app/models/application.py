"""Application Intelligence persistence models."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ApplicationOpportunity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A pasted job, internship, or application prompt analyzed by CareerOS."""

    __tablename__ = "application_opportunities"
    __table_args__ = (
        Index("idx_application_opportunities_user_id", "user_id"),
        Index("idx_application_opportunities_user_status", "user_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    organization: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    detected_role_type: Mapped[str | None] = mapped_column(Text)
    detected_skills: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    detected_keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    detected_responsibilities: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    detected_questions: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="ANALYZED", server_default="ANALYZED"
    )


class ApplicationQuestion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A specific application question linked to an opportunity."""

    __tablename__ = "application_questions"
    __table_args__ = (
        Index("idx_application_questions_user_id", "user_id"),
        Index("idx_application_questions_opportunity_id", "opportunity_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_opportunities.id"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(Text, nullable=False)
    detected_intent: Mapped[str] = mapped_column(Text, nullable=False)
    required_themes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="OPEN", server_default="OPEN"
    )


class ApplicationMemoryMatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Ranked relevance of approved Career Memory for an opportunity/question."""

    __tablename__ = "application_memory_matches"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id",
            "question_id",
            "canonical_memory_id",
            name="uq_application_memory_matches_scope_memory",
        ),
        Index("idx_application_matches_user_id", "user_id"),
        Index("idx_application_matches_opportunity_id", "opportunity_id"),
        Index("idx_application_matches_question_id", "question_id"),
        Index("idx_application_matches_canonical_memory_id", "canonical_memory_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_opportunities.id"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_questions.id")
    )
    canonical_memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("canonical_memory_records.id"), nullable=False
    )
    match_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    match_reason: Mapped[str] = mapped_column(Text, nullable=False)
    # Legacy rows contain a flat evidence-ID list. Sprint 13.1 stores a versioned
    # JSONB provenance envelope so ListeningEvidence and enrichment UUIDs remain
    # distinct without a destructive data migration.
    evidence_ids: Mapped[list[str] | dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    themes_matched: Mapped[list[str]] = mapped_column(JSONB, nullable=False)


class ApplicationDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An editable, evidence-backed application draft."""

    __tablename__ = "application_drafts"
    __table_args__ = (
        Index("idx_application_drafts_user_id", "user_id"),
        Index("idx_application_drafts_opportunity_id", "opportunity_id"),
        Index("idx_application_drafts_question_id", "question_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_opportunities.id"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_questions.id")
    )
    draft_type: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="DRAFT", server_default="DRAFT"
    )
    draft_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

"""Durable review lifecycle and dashboard-ready canonical memory projection."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReviewProposal(TimestampMixin, Base):
    __tablename__ = "review_proposals"
    __table_args__ = (Index("idx_review_proposals_user_status", "user_id", "decision"),)

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    proposal_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    identity_key: Mapped[str] = mapped_column(Text, nullable=False)
    proposal_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    decision: Mapped[str] = mapped_column(
        Text, nullable=False, default="PENDING_REVIEW", server_default="PENDING_REVIEW"
    )
    edited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    canonical_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CanonicalMemoryRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "canonical_memory_records"
    __table_args__ = (
        UniqueConstraint("user_id", "identity_key"),
        Index("idx_canonical_memory_user_type", "user_id", "memory_type"),
        Index(
            "idx_canonical_memory_review_proposal_id",
            "review_proposal_id",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    identity_key: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    structured_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    review_proposal_id: Mapped[str] = mapped_column(
        Text, ForeignKey("review_proposals.id"), nullable=False
    )
    typed_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

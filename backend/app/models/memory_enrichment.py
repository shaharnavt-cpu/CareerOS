"""Reviewed enrichment records attached to approved Career Memory."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CareerMemoryEnrichment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Durable review history for deeper evidence about one canonical memory."""

    __tablename__ = "career_memory_enrichments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'ARCHIVED')",
            name="career_memory_enrichment_status_values",
        ),
        CheckConstraint(
            "enrichment_type IN ('PROJECT_CONTEXT', 'PROJECT_METHOD', "
            "'PROJECT_RESULT', 'PROJECT_LIMITATION', 'PROJECT_OUTPUT', "
            "'PROJECT_ROLE_RELEVANCE', 'PROJECT_FULL_ENRICHMENT', "
            "'MEMORY_MERGE_SUGGESTION')",
            name="career_memory_enrichment_type_values",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="career_memory_enrichment_confidence_range",
        ),
        Index("idx_memory_enrichments_user_status", "user_id", "status"),
        Index(
            "idx_memory_enrichments_memory_id",
            "canonical_memory_id",
        ),
        Index("idx_memory_enrichments_source_id", "source_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    canonical_memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canonical_memory_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listening_sources.id", ondelete="SET NULL"),
    )
    source_label: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="PROPOSED", server_default="PROPOSED"
    )
    enrichment_type: Mapped[str] = mapped_column(Text, nullable=False)
    structured_enrichment: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    evidence_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    identity_resolution: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    warnings: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )

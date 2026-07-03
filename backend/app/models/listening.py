"""Non-canonical persistence for the Multi-Source Listening Engine."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

SOURCE_TYPES = (
    "'RESUME', 'CONVERSATION', 'MANUAL', 'TRANSCRIPT', 'LINKEDIN', "
    "'PORTFOLIO', 'GITHUB', 'CERTIFICATE', 'GENERIC_DOCUMENT'"
)
EVIDENCE_CATEGORIES = (
    "'EDUCATION', 'PROGRAM', 'EXPERIENCE', 'PROJECT', 'SKILL', "
    "'ACHIEVEMENT', 'ORGANIZATION', 'DATE', 'ROLE', 'CONTACT', 'LINK', 'UNKNOWN'"
)


class ListeningSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Durable staging record for a user-provided source."""

    __tablename__ = "listening_sources"
    __table_args__ = (
        CheckConstraint(f"source_type IN ({SOURCE_TYPES})", name="source_type_values"),
        CheckConstraint(
            "status IN ('RECEIVED', 'LISTENING', 'READY', 'FAILED')",
            name="status_values",
        ),
        UniqueConstraint("user_id", "source_type", "content_hash"),
        Index("idx_listening_sources_user_id", "user_id"),
        Index("idx_listening_sources_user_received", "user_id", "received_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text)
    media_type: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    adapter_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="RECEIVED", server_default="RECEIVED"
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ListeningEvidence(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only evidence extracted before semantic reasoning."""

    __tablename__ = "listening_evidence"
    __table_args__ = (
        CheckConstraint(f"source_type IN ({SOURCE_TYPES})", name="source_type_values"),
        CheckConstraint(f"category IN ({EVIDENCE_CATEGORIES})", name="category_values"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        UniqueConstraint("source_id", "excerpt_hash"),
        Index("idx_listening_evidence_user_id", "user_id"),
        Index("idx_listening_evidence_source_id", "source_id"),
        Index("idx_listening_evidence_user_category", "user_id", "category"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listening_sources.id"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    raw_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_excerpt: Mapped[str | None] = mapped_column(Text)
    excerpt_hash: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    location: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    provenance: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ListeningEvidenceCluster(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A durable grouping of supporting and conflicting evidence."""

    __tablename__ = "listening_evidence_clusters"
    __table_args__ = (
        CheckConstraint(f"category IN ({EVIDENCE_CATEGORIES})", name="category_values"),
        UniqueConstraint("user_id", "category", "normalized_key"),
        Index("idx_listening_clusters_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_key: Mapped[str] = mapped_column(Text, nullable=False)
    has_conflicts: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    conflicting_claims: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )


class ListeningClusterMember(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Retain every observation and how it relates to its evidence cluster."""

    __tablename__ = "listening_cluster_members"
    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('SUPPORTING', 'DUPLICATE', 'CONFLICTING')",
            name="relationship_type_values",
        ),
        UniqueConstraint("cluster_id", "evidence_id"),
        Index("idx_listening_members_user_id", "user_id"),
        Index("idx_listening_members_cluster_id", "cluster_id"),
        Index("idx_listening_members_evidence_id", "evidence_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listening_evidence_clusters.id"),
        nullable=False,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listening_evidence.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(Text, nullable=False)


class ListeningProposalEvidenceLink(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Durable provenance from a Sprint 4 proposal to staged evidence."""

    __tablename__ = "listening_proposal_evidence_links"
    __table_args__ = (
        UniqueConstraint("proposal_id", "evidence_id"),
        Index("idx_listening_proposal_links_user_id", "user_id"),
        Index("idx_listening_proposal_links_proposal_id", "proposal_id"),
        Index("idx_listening_proposal_links_cluster_id", "cluster_id"),
        Index("idx_listening_proposal_links_evidence_id", "evidence_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    proposal_id: Mapped[str] = mapped_column(Text, nullable=False)
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listening_evidence_clusters.id"),
        nullable=False,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listening_evidence.id"), nullable=False
    )

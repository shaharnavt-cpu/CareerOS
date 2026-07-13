"""Durable proof artifacts and their editable generated versions."""

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


class ProofArtifact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """User-owned proof package grounded in one canonical memory."""

    __tablename__ = "proof_artifacts"
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('CASE_STUDY', 'GITHUB_README', 'PORTFOLIO_PAGE', "
            "'APPLICATION_UPLOAD', 'OUTREACH_SUMMARY', 'INTERVIEW_STORY', "
            "'RESUME_BULLETS')",
            name="proof_artifact_type_values",
        ),
        CheckConstraint(
            "target_audience IN ('APPLICATION_UPLOAD', 'PORTFOLIO', 'GITHUB', "
            "'OUTREACH', 'INTERVIEW_PREP', 'GENERAL')",
            name="proof_artifact_audience_values",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'REVIEWED', 'READY', 'ARCHIVED')",
            name="proof_artifact_status_values",
        ),
        Index("idx_proof_artifacts_user_id", "user_id"),
        Index("idx_proof_artifacts_user_status", "user_id", "status"),
        Index("idx_proof_artifacts_source_memory_id", "source_memory_id"),
        Index(
            "idx_proof_artifacts_source_diagnosis_result_id",
            "source_diagnosis_result_id",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_role: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, nullable=False)
    source_memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canonical_memory_records.id"),
        nullable=False,
    )
    source_diagnosis_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("diagnosis_results.id", ondelete="SET NULL"),
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="DRAFT", server_default="DRAFT"
    )


class ProofArtifactVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One generated or user-edited version of a proof artifact."""

    __tablename__ = "proof_artifact_versions"
    __table_args__ = (
        CheckConstraint(
            "version_number > 0",
            name="proof_artifact_version_number_positive",
        ),
        CheckConstraint(
            "readiness_score >= 0 AND readiness_score <= 1",
            name="proof_artifact_readiness_score_range",
        ),
        CheckConstraint(
            "readiness_label IN ('NEEDS_EVIDENCE', 'DRAFTABLE', "
            "'STRONG_DRAFT', 'READY_TO_SHARE')",
            name="proof_artifact_readiness_values",
        ),
        UniqueConstraint(
            "artifact_id",
            "version_number",
            name="uq_proof_artifact_versions_artifact_version",
        ),
        Index("idx_proof_artifact_versions_user_id", "user_id"),
        Index("idx_proof_artifact_versions_artifact_id", "artifact_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proof_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_sections: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    outcome_signal_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    readiness_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    readiness_label: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_variants: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

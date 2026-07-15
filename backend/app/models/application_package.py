"""Durable, versioned application packages built from approved Career Memory."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ApplicationPackage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A mutable package workspace whose saved output lives in immutable versions."""

    __tablename__ = "application_packages"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'READY', 'ARCHIVED')",
            name="application_package_status_values",
        ),
        Index("idx_application_packages_user_id", "user_id"),
        Index("idx_application_packages_user_status", "user_id", "status"),
        Index("idx_application_packages_opportunity_id", "opportunity_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_opportunities.id", ondelete="SET NULL"),
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    role_title: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    job_type: Mapped[str | None] = mapped_column(Text)
    target_description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    preferred_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    responsibilities: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    selected_memory_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="DRAFT", server_default="DRAFT"
    )


class ApplicationPackageVersion(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """An append-only snapshot of package inputs, output, and provenance."""

    __tablename__ = "application_package_versions"
    __table_args__ = (
        CheckConstraint(
            "version_number > 0",
            name="application_package_version_number_positive",
        ),
        CheckConstraint(
            "generation_reason IN ('GENERATED', 'REGENERATED', 'USER_EDIT')",
            name="application_package_version_reason_values",
        ),
        UniqueConstraint(
            "package_id",
            "version_number",
            name="uq_application_package_versions_package_version",
        ),
        Index("idx_application_package_versions_user_id", "user_id"),
        Index("idx_application_package_versions_package_id", "package_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("application_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    target_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    selected_memory_ids_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    compiled_profile_snapshots_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    generated_outputs_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    evidence_trace_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    warnings_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    claim_ledger_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )
    memory_ids_used_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    enrichment_ids_used_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    outcome_signal_ids_used_json: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False
    )
    user_edits_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    generator_version: Mapped[str] = mapped_column(Text, nullable=False)
    generation_reason: Mapped[str] = mapped_column(Text, nullable=False)

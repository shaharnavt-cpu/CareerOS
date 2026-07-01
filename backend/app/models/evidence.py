"""Evidence-domain persistence models."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import (
    Base,
    CreatedAtMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.user import User


class EvidenceItem(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Proof supporting one or more professional claims."""

    __tablename__ = "evidence_items"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('GITHUB_REPOSITORY', 'PUBLICATION', "
            "'RESEARCH_ARTIFACT', 'CERTIFICATE', 'AWARD', 'TRANSCRIPT', "
            "'PRESENTATION', 'SCREENSHOT', 'PORTFOLIO', 'VIDEO', 'LETTER', "
            "'PERFORMANCE_REVIEW', 'USER_NOTE', 'OTHER')",
            name="evidence_type_values",
        ),
        CheckConstraint(
            "verification_status IN ('UNVERIFIED', 'SELF_VERIFIED', "
            "'EXTERNALLY_VERIFIED', 'OFFICIAL')",
            name="verification_status_values",
        ),
        Index("idx_evidence_items_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    storage_key: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="UNVERIFIED", server_default="UNVERIFIED"
    )
    evidence_date: Mapped[date | None] = mapped_column(Date)

    user: Mapped[User] = relationship(back_populates="evidence_items")
    links: Mapped[list[EvidenceLink]] = relationship(back_populates="evidence_item")


class EvidenceLink(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Polymorphic link from evidence to a supported entity."""

    __tablename__ = "evidence_links"
    __table_args__ = (
        Index(
            "idx_evidence_links_user_entity",
            "user_id",
            "entity_type",
            "entity_id",
        ),
        Index("idx_evidence_links_evidence_item", "evidence_item_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence_items.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_type: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="evidence_links")
    evidence_item: Mapped[EvidenceItem] = relationship(back_populates="links")

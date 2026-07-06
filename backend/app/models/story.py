"""First-class Career Story persistence models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
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
    from app.models.evidence import EvidenceItem
    from app.models.user import User


STORY_ENTITY_TYPES = (
    "'PROGRAM', 'EDUCATION', 'EXPERIENCE', 'PROJECT', 'ACHIEVEMENT', 'SKILL'"
)


class Story(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """An editable, evidence-backed professional narrative."""

    __tablename__ = "stories"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'ARCHIVED')",
            name="status_values",
        ),
        Index("idx_stories_user_id", "user_id"),
        Index("idx_stories_user_status", "user_id", "status"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    primary_goal: Mapped[str | None] = mapped_column(Text)
    transformation: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="PROPOSED", server_default="PROPOSED"
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="stories")
    chapters: Mapped[list[StoryChapter]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
        order_by="StoryChapter.position",
    )
    memberships: Mapped[list[StoryMembership]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )
    evidence_links: Mapped[list[StoryEvidence]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )


class StoryChapter(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """An ordered phase within a Career Story."""

    __tablename__ = "story_chapters"
    __table_args__ = (
        CheckConstraint("position >= 0", name="position_nonnegative"),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name="date_range",
        ),
        UniqueConstraint("story_id", "position"),
        Index("idx_story_chapters_user_id", "user_id"),
        Index("idx_story_chapters_story_id", "story_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    story: Mapped[Story] = relationship(back_populates="chapters")
    memberships: Mapped[list[StoryMembership]] = relationship(back_populates="chapter")


class StoryMembership(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Explainable membership of a Career Memory entity in a story."""

    __tablename__ = "story_memberships"
    __table_args__ = (
        CheckConstraint(
            f"entity_type IN ({STORY_ENTITY_TYPES})", name="entity_type_values"
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        UniqueConstraint("story_id", "entity_type", "entity_id"),
        Index("idx_story_memberships_user_id", "user_id"),
        Index("idx_story_memberships_story_id", "story_id"),
        Index(
            "idx_story_memberships_user_entity",
            "user_id",
            "entity_type",
            "entity_id",
        ),
        Index("idx_story_memberships_chapter_id", "chapter_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False
    )
    chapter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("story_chapters.id")
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    role: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)

    story: Mapped[Story] = relationship(back_populates="memberships")
    chapter: Mapped[StoryChapter | None] = relationship(back_populates="memberships")


class StoryEvidence(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Explicit evidence supporting a Career Story."""

    __tablename__ = "story_evidence"
    __table_args__ = (
        UniqueConstraint("story_id", "evidence_item_id"),
        Index("idx_story_evidence_user_id", "user_id"),
        Index("idx_story_evidence_story_id", "story_id"),
        Index("idx_story_evidence_evidence_item_id", "evidence_item_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False
    )
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence_items.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(
        Text, nullable=False, default="SUPPORTS", server_default="SUPPORTS"
    )
    excerpt: Mapped[str | None] = mapped_column(Text)

    story: Mapped[Story] = relationship(back_populates="evidence_links")
    evidence_item: Mapped[EvidenceItem] = relationship()

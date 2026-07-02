"""User-domain persistence models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.career import (
        Achievement,
        Education,
        Experience,
        Program,
        ProgramLink,
        Project,
        Skill,
        SkillLink,
    )
    from app.models.evidence import EvidenceItem, EvidenceLink


class User(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Internal CareerOS user record."""

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_clerk_user_id", "clerk_user_id"),
    )

    clerk_user_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="America/Chicago",
        server_default="America/Chicago",
    )

    preferences: Mapped[UserPreferences | None] = relationship(back_populates="user")
    programs: Mapped[list[Program]] = relationship(back_populates="user")
    program_links: Mapped[list[ProgramLink]] = relationship(back_populates="user")
    education: Mapped[list[Education]] = relationship(back_populates="user")
    experiences: Mapped[list[Experience]] = relationship(back_populates="user")
    projects: Mapped[list[Project]] = relationship(back_populates="user")
    achievements: Mapped[list[Achievement]] = relationship(back_populates="user")
    skills: Mapped[list[Skill]] = relationship(back_populates="user")
    skill_links: Mapped[list[SkillLink]] = relationship(back_populates="user")
    evidence_items: Mapped[list[EvidenceItem]] = relationship(back_populates="user")
    evidence_links: Mapped[list[EvidenceLink]] = relationship(back_populates="user")


class UserPreferences(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Editable preferences used by future recommendation features."""

    __tablename__ = "user_preferences"
    __table_args__ = (
        CheckConstraint(
            "remote_preference IS NULL OR remote_preference IN "
            "('ONSITE', 'HYBRID', 'REMOTE', 'FLEXIBLE')",
            name="remote_preference_values",
        ),
        CheckConstraint(
            "target_salary_min IS NULL OR target_salary_min >= 0",
            name="target_salary_min_nonnegative",
        ),
        CheckConstraint(
            "target_salary_max IS NULL OR target_salary_max >= 0",
            name="target_salary_max_nonnegative",
        ),
        CheckConstraint(
            "target_salary_min IS NULL OR target_salary_max IS NULL "
            "OR target_salary_min <= target_salary_max",
            name="target_salary_range",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )
    preferred_roles: Mapped[list[str] | None] = mapped_column(JSONB)
    preferred_industries: Mapped[list[str] | None] = mapped_column(JSONB)
    preferred_locations: Mapped[list[str] | None] = mapped_column(JSONB)
    remote_preference: Mapped[str | None] = mapped_column(Text)
    work_authorization: Mapped[str | None] = mapped_column(Text)
    sponsorship_required: Mapped[bool | None] = mapped_column(Boolean)
    target_salary_min: Mapped[int | None] = mapped_column(Integer)
    target_salary_max: Mapped[int | None] = mapped_column(Integer)
    resume_style: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="preferences")

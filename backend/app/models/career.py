"""Career Knowledge Engine persistence models."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


DATE_PRECISION_CHECK = (
    "date_precision IS NULL OR date_precision IN ('DAY', 'MONTH', 'YEAR', 'UNKNOWN')"
)


class Program(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A structured program connecting multiple canonical knowledge types."""

    __tablename__ = "programs"
    __table_args__ = (
        CheckConstraint(DATE_PRECISION_CHECK, name="date_precision_values"),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name="date_range",
        ),
        CheckConstraint(
            "NOT is_current OR end_date IS NULL", name="current_has_no_end_date"
        ),
        Index("idx_programs_user_id", "user_id"),
        Index("idx_programs_user_dates", "user_id", "start_date", "end_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    organization_name: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    categories: Mapped[list[str] | None] = mapped_column(JSONB)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    date_precision: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    program_url: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="programs")
    links: Mapped[list[ProgramLink]] = relationship(back_populates="program")


class ProgramLink(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Validated polymorphic link from a Program to canonical knowledge."""

    __tablename__ = "program_links"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('EDUCATION', 'EXPERIENCE', 'PROJECT', 'ACHIEVEMENT')",
            name="entity_type_values",
        ),
        UniqueConstraint("program_id", "entity_type", "entity_id"),
        Index("idx_program_links_program_id", "program_id"),
        Index("idx_program_links_user_entity", "user_id", "entity_type", "entity_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("programs.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relationship_type: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="program_links")
    program: Mapped[Program] = relationship(back_populates="links")


class Education(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A user's formal education record."""

    __tablename__ = "education"
    __table_args__ = (
        CheckConstraint(DATE_PRECISION_CHECK, name="date_precision_values"),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name="date_range",
        ),
        Index("idx_education_user_id", "user_id"),
        Index("idx_education_user_end_date", "user_id", "end_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    institution_name: Mapped[str] = mapped_column(Text, nullable=False)
    degree: Mapped[str | None] = mapped_column(Text)
    field_of_study: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    date_precision: Mapped[str | None] = mapped_column(Text)
    gpa: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    honors: Mapped[list[Any] | None] = mapped_column(JSONB)
    coursework: Mapped[list[Any] | None] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="education")
    projects: Mapped[list[Project]] = relationship(back_populates="education")
    achievements: Mapped[list[Achievement]] = relationship(back_populates="education")


class Experience(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A professional, academic, research, or community experience."""

    __tablename__ = "experiences"
    __table_args__ = (
        CheckConstraint(
            "experience_type IN ('FULL_TIME', 'PART_TIME', 'INTERNSHIP', "
            "'RESEARCH', 'TEACHING', 'VOLUNTEER', 'LEADERSHIP', 'FREELANCE', "
            "'COURSE_PROJECT', 'PERSONAL', 'OTHER')",
            name="experience_type_values",
        ),
        CheckConstraint(DATE_PRECISION_CHECK, name="date_precision_values"),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name="date_range",
        ),
        CheckConstraint(
            "NOT is_current OR end_date IS NULL", name="current_has_no_end_date"
        ),
        Index("idx_experiences_user_id", "user_id"),
        Index("idx_experiences_user_type", "user_id", "experience_type"),
        Index("idx_experiences_user_dates", "user_id", "start_date", "end_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    experience_type: Mapped[str] = mapped_column(Text, nullable=False)
    organization_name: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    date_precision: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    summary: Mapped[str | None] = mapped_column(Text)
    responsibilities: Mapped[list[Any] | None] = mapped_column(JSONB)
    metrics: Mapped[list[Any] | dict[str, Any] | None] = mapped_column(JSONB)

    user: Mapped[User] = relationship(back_populates="experiences")
    projects: Mapped[list[Project]] = relationship(back_populates="experience")
    achievements: Mapped[list[Achievement]] = relationship(back_populates="experience")


class Project(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A technical, academic, research, hackathon, or personal project."""

    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name="date_range",
        ),
        Index("idx_projects_user_id", "user_id"),
        Index("idx_projects_experience_id", "experience_id"),
        Index("idx_projects_education_id", "education_id"),
        Index("idx_projects_user_dates", "user_id", "start_date", "end_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    experience_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiences.id")
    )
    education_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("education.id")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    problem: Mapped[str | None] = mapped_column(Text)
    approach: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    repository_url: Mapped[str | None] = mapped_column(Text)
    demo_url: Mapped[str | None] = mapped_column(Text)
    documentation_url: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    user: Mapped[User] = relationship(back_populates="projects")
    experience: Mapped[Experience | None] = relationship(back_populates="projects")
    education: Mapped[Education | None] = relationship(back_populates="projects")
    achievements: Mapped[list[Achievement]] = relationship(back_populates="project")


class Achievement(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A measurable accomplishment supported by career knowledge."""

    __tablename__ = "achievements"
    __table_args__ = (
        CheckConstraint(
            "category IS NULL OR category IN ('ACADEMIC', 'PROFESSIONAL', "
            "'RESEARCH', 'LEADERSHIP', 'VOLUNTEER', 'COMPETITION', "
            "'SCHOLARSHIP', 'PUBLICATION', 'CERTIFICATION', 'OTHER')",
            name="category_values",
        ),
        Index("idx_achievements_user_id", "user_id"),
        Index("idx_achievements_experience_id", "experience_id"),
        Index("idx_achievements_project_id", "project_id"),
        Index("idx_achievements_education_id", "education_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    metric_value: Mapped[str | None] = mapped_column(Text)
    achieved_on: Mapped[date | None] = mapped_column(Date)
    experience_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiences.id")
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id")
    )
    education_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("education.id")
    )

    user: Mapped[User] = relationship(back_populates="achievements")
    experience: Mapped[Experience | None] = relationship(back_populates="achievements")
    project: Mapped[Project | None] = relationship(back_populates="achievements")
    education: Mapped[Education | None] = relationship(back_populates="achievements")


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """A user-owned skill whose confidence is evidence-backed."""

    __tablename__ = "skills"
    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name"),
        CheckConstraint(
            "proficiency_level IS NULL OR proficiency_level IN "
            "('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT')",
            name="proficiency_level_values",
        ),
        CheckConstraint(
            "confidence_score IS NULL OR "
            "(confidence_score >= 0 AND confidence_score <= 1)",
            name="confidence_score_range",
        ),
        Index("idx_skills_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)
    proficiency_level: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    user: Mapped[User] = relationship(back_populates="skills")
    links: Mapped[list[SkillLink]] = relationship(back_populates="skill")


class SkillLink(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Polymorphic link from a skill to supporting career knowledge."""

    __tablename__ = "skill_links"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('PROGRAM', 'PROJECT', 'EXPERIENCE', 'ACHIEVEMENT', "
            "'EDUCATION')",
            name="entity_type_values",
        ),
        CheckConstraint(
            "relevance_score IS NULL OR "
            "(relevance_score >= 0 AND relevance_score <= 1)",
            name="relevance_score_range",
        ),
        Index("idx_skill_links_user_id", "user_id"),
        Index("idx_skill_links_skill_id", "skill_id"),
        Index("idx_skill_links_user_entity", "user_id", "entity_type", "entity_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="skill_links")
    skill: Mapped[Skill] = relationship(back_populates="links")

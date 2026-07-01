"""Create the Career Knowledge Engine schema.

Revision ID: 20260701_0001
Revises:
Create Date: 2026-07-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260701_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the ten tables in the Sprint 2 persistence scope."""

    op.create_table(
        "users",
        sa.Column("clerk_user_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=True),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column(
            "timezone",
            sa.Text(),
            server_default="America/Chicago",
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("clerk_user_id", name=op.f("uq_users_clerk_user_id")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index("idx_users_clerk_user_id", "users", ["clerk_user_id"])
    op.create_index("idx_users_email", "users", ["email"])

    op.create_table(
        "user_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "preferred_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "preferred_industries",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "preferred_locations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("remote_preference", sa.Text(), nullable=True),
        sa.Column("work_authorization", sa.Text(), nullable=True),
        sa.Column("sponsorship_required", sa.Boolean(), nullable=True),
        sa.Column("target_salary_min", sa.Integer(), nullable=True),
        sa.Column("target_salary_max", sa.Integer(), nullable=True),
        sa.Column("resume_style", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "remote_preference IS NULL OR remote_preference IN "
            "('ONSITE', 'HYBRID', 'REMOTE', 'FLEXIBLE')",
            name=op.f("ck_user_preferences_remote_preference_values"),
        ),
        sa.CheckConstraint(
            "target_salary_min IS NULL OR target_salary_min >= 0",
            name=op.f("ck_user_preferences_target_salary_min_nonnegative"),
        ),
        sa.CheckConstraint(
            "target_salary_max IS NULL OR target_salary_max >= 0",
            name=op.f("ck_user_preferences_target_salary_max_nonnegative"),
        ),
        sa.CheckConstraint(
            "target_salary_min IS NULL OR target_salary_max IS NULL "
            "OR target_salary_min <= target_salary_max",
            name=op.f("ck_user_preferences_target_salary_range"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_preferences_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_preferences")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_preferences_user_id")),
    )

    op.create_table(
        "education",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_name", sa.Text(), nullable=False),
        sa.Column("degree", sa.Text(), nullable=True),
        sa.Column("field_of_study", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("date_precision", sa.Text(), nullable=True),
        sa.Column("gpa", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("honors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("coursework", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "date_precision IS NULL OR date_precision IN "
            "('DAY', 'MONTH', 'YEAR', 'UNKNOWN')",
            name=op.f("ck_education_date_precision_values"),
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name=op.f("ck_education_date_range"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_education_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_education")),
    )
    op.create_index("idx_education_user_end_date", "education", ["user_id", "end_date"])
    op.create_index("idx_education_user_id", "education", ["user_id"])

    op.create_table(
        "experiences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experience_type", sa.Text(), nullable=False),
        sa.Column("organization_name", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("date_precision", sa.Text(), nullable=True),
        sa.Column(
            "is_current", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "responsibilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "experience_type IN ('FULL_TIME', 'PART_TIME', 'INTERNSHIP', "
            "'RESEARCH', 'TEACHING', 'VOLUNTEER', 'LEADERSHIP', 'FREELANCE', "
            "'COURSE_PROJECT', 'PERSONAL', 'OTHER')",
            name=op.f("ck_experiences_experience_type_values"),
        ),
        sa.CheckConstraint(
            "date_precision IS NULL OR date_precision IN "
            "('DAY', 'MONTH', 'YEAR', 'UNKNOWN')",
            name=op.f("ck_experiences_date_precision_values"),
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name=op.f("ck_experiences_date_range"),
        ),
        sa.CheckConstraint(
            "NOT is_current OR end_date IS NULL",
            name=op.f("ck_experiences_current_has_no_end_date"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_experiences_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_experiences")),
    )
    op.create_index(
        "idx_experiences_user_dates",
        "experiences",
        ["user_id", "start_date", "end_date"],
    )
    op.create_index("idx_experiences_user_id", "experiences", ["user_id"])
    op.create_index(
        "idx_experiences_user_type", "experiences", ["user_id", "experience_type"]
    )

    op.create_table(
        "skills",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("normalized_name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("proficiency_level", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "proficiency_level IS NULL OR proficiency_level IN "
            "('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT')",
            name=op.f("ck_skills_proficiency_level_values"),
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR "
            "(confidence_score >= 0 AND confidence_score <= 1)",
            name=op.f("ck_skills_confidence_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_skills_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skills")),
        sa.UniqueConstraint(
            "user_id", "normalized_name", name=op.f("uq_skills_user_id")
        ),
    )
    op.create_index("idx_skills_user_id", "skills", ["user_id"])

    op.create_table(
        "evidence_items",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column(
            "verification_status",
            sa.Text(),
            server_default="UNVERIFIED",
            nullable=False,
        ),
        sa.Column("evidence_date", sa.Date(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "evidence_type IN ('GITHUB_REPOSITORY', 'PUBLICATION', "
            "'RESEARCH_ARTIFACT', 'CERTIFICATE', 'AWARD', 'TRANSCRIPT', "
            "'PRESENTATION', 'SCREENSHOT', 'PORTFOLIO', 'VIDEO', 'LETTER', "
            "'PERFORMANCE_REVIEW', 'USER_NOTE', 'OTHER')",
            name=op.f("ck_evidence_items_evidence_type_values"),
        ),
        sa.CheckConstraint(
            "verification_status IN ('UNVERIFIED', 'SELF_VERIFIED', "
            "'EXTERNALLY_VERIFIED', 'OFFICIAL')",
            name=op.f("ck_evidence_items_verification_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_evidence_items_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_items")),
    )
    op.create_index("idx_evidence_items_user_id", "evidence_items", ["user_id"])

    op.create_table(
        "projects",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experience_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("education_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("project_type", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("problem", sa.Text(), nullable=True),
        sa.Column("approach", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("repository_url", sa.Text(), nullable=True),
        sa.Column("demo_url", sa.Text(), nullable=True),
        sa.Column("documentation_url", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name=op.f("ck_projects_date_range"),
        ),
        sa.ForeignKeyConstraint(
            ["education_id"],
            ["education.id"],
            name=op.f("fk_projects_education_id_education"),
        ),
        sa.ForeignKeyConstraint(
            ["experience_id"],
            ["experiences.id"],
            name=op.f("fk_projects_experience_id_experiences"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_projects_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
    )
    op.create_index("idx_projects_education_id", "projects", ["education_id"])
    op.create_index("idx_projects_experience_id", "projects", ["experience_id"])
    op.create_index(
        "idx_projects_user_dates",
        "projects",
        ["user_id", "start_date", "end_date"],
    )
    op.create_index("idx_projects_user_id", "projects", ["user_id"])

    op.create_table(
        "skill_links",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relevance_score", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "entity_type IN ('PROJECT', 'EXPERIENCE', 'ACHIEVEMENT', 'EDUCATION')",
            name=op.f("ck_skill_links_entity_type_values"),
        ),
        sa.CheckConstraint(
            "relevance_score IS NULL OR "
            "(relevance_score >= 0 AND relevance_score <= 1)",
            name=op.f("ck_skill_links_relevance_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"], ["skills.id"], name=op.f("fk_skill_links_skill_id_skills")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_skill_links_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skill_links")),
    )
    op.create_index("idx_skill_links_skill_id", "skill_links", ["skill_id"])
    op.create_index(
        "idx_skill_links_user_entity",
        "skill_links",
        ["user_id", "entity_type", "entity_id"],
    )
    op.create_index("idx_skill_links_user_id", "skill_links", ["user_id"])

    op.create_table(
        "evidence_links",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["evidence_item_id"],
            ["evidence_items.id"],
            name=op.f("fk_evidence_links_evidence_item_id_evidence_items"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_evidence_links_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_links")),
    )
    op.create_index(
        "idx_evidence_links_evidence_item", "evidence_links", ["evidence_item_id"]
    )
    op.create_index(
        "idx_evidence_links_user_entity",
        "evidence_links",
        ["user_id", "entity_type", "entity_id"],
    )

    op.create_table(
        "achievements",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metric_value", sa.Text(), nullable=True),
        sa.Column("achieved_on", sa.Date(), nullable=True),
        sa.Column("experience_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("education_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "category IS NULL OR category IN ('ACADEMIC', 'PROFESSIONAL', "
            "'RESEARCH', 'LEADERSHIP', 'VOLUNTEER', 'COMPETITION', "
            "'SCHOLARSHIP', 'PUBLICATION', 'CERTIFICATION', 'OTHER')",
            name=op.f("ck_achievements_category_values"),
        ),
        sa.ForeignKeyConstraint(
            ["education_id"],
            ["education.id"],
            name=op.f("fk_achievements_education_id_education"),
        ),
        sa.ForeignKeyConstraint(
            ["experience_id"],
            ["experiences.id"],
            name=op.f("fk_achievements_experience_id_experiences"),
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_achievements_project_id_projects"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_achievements_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_achievements")),
    )
    op.create_index("idx_achievements_education_id", "achievements", ["education_id"])
    op.create_index("idx_achievements_experience_id", "achievements", ["experience_id"])
    op.create_index("idx_achievements_project_id", "achievements", ["project_id"])
    op.create_index("idx_achievements_user_id", "achievements", ["user_id"])


def downgrade() -> None:
    """Remove the Career Knowledge Engine schema."""

    op.drop_index("idx_achievements_user_id", table_name="achievements")
    op.drop_index("idx_achievements_project_id", table_name="achievements")
    op.drop_index("idx_achievements_experience_id", table_name="achievements")
    op.drop_index("idx_achievements_education_id", table_name="achievements")
    op.drop_table("achievements")
    op.drop_index("idx_evidence_links_user_entity", table_name="evidence_links")
    op.drop_index("idx_evidence_links_evidence_item", table_name="evidence_links")
    op.drop_table("evidence_links")
    op.drop_index("idx_skill_links_user_id", table_name="skill_links")
    op.drop_index("idx_skill_links_user_entity", table_name="skill_links")
    op.drop_index("idx_skill_links_skill_id", table_name="skill_links")
    op.drop_table("skill_links")
    op.drop_index("idx_projects_user_id", table_name="projects")
    op.drop_index("idx_projects_user_dates", table_name="projects")
    op.drop_index("idx_projects_experience_id", table_name="projects")
    op.drop_index("idx_projects_education_id", table_name="projects")
    op.drop_table("projects")
    op.drop_index("idx_evidence_items_user_id", table_name="evidence_items")
    op.drop_table("evidence_items")
    op.drop_index("idx_skills_user_id", table_name="skills")
    op.drop_table("skills")
    op.drop_index("idx_experiences_user_type", table_name="experiences")
    op.drop_index("idx_experiences_user_id", table_name="experiences")
    op.drop_index("idx_experiences_user_dates", table_name="experiences")
    op.drop_table("experiences")
    op.drop_index("idx_education_user_id", table_name="education")
    op.drop_index("idx_education_user_end_date", table_name="education")
    op.drop_table("education")
    op.drop_table("user_preferences")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_index("idx_users_clerk_user_id", table_name="users")
    op.drop_table("users")

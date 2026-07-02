"""Add Program persistence to the Career Knowledge Engine.

Revision ID: 20260702_0002
Revises: 20260701_0001
Create Date: 2026-07-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260702_0002"
down_revision: str | None = "20260701_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create Program entities and their validated polymorphic links."""

    op.create_table(
        "programs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("organization_name", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("date_precision", sa.Text(), nullable=True),
        sa.Column(
            "is_current", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("program_url", sa.Text(), nullable=True),
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
            name=op.f("ck_programs_date_precision_values"),
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name=op.f("ck_programs_date_range"),
        ),
        sa.CheckConstraint(
            "NOT is_current OR end_date IS NULL",
            name=op.f("ck_programs_current_has_no_end_date"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_programs_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_programs")),
    )
    op.create_index("idx_programs_user_id", "programs", ["user_id"])
    op.create_index(
        "idx_programs_user_dates", "programs", ["user_id", "start_date", "end_date"]
    )

    op.create_table(
        "program_links",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "entity_type IN ('EDUCATION', 'EXPERIENCE', 'PROJECT', 'ACHIEVEMENT')",
            name=op.f("ck_program_links_entity_type_values"),
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name=op.f("fk_program_links_program_id_programs"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_program_links_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_program_links")),
        sa.UniqueConstraint(
            "program_id",
            "entity_type",
            "entity_id",
            name=op.f("uq_program_links_program_id"),
        ),
    )
    op.create_index("idx_program_links_program_id", "program_links", ["program_id"])
    op.create_index(
        "idx_program_links_user_entity",
        "program_links",
        ["user_id", "entity_type", "entity_id"],
    )

    op.drop_constraint(
        "ck_skill_links_entity_type_values", "skill_links", type_="check"
    )
    op.create_check_constraint(
        "ck_skill_links_entity_type_values",
        "skill_links",
        "entity_type IN ('PROGRAM', 'PROJECT', 'EXPERIENCE', 'ACHIEVEMENT', "
        "'EDUCATION')",
    )


def downgrade() -> None:
    """Remove Program persistence and restore the original skill-link check."""

    op.drop_constraint(
        "ck_skill_links_entity_type_values", "skill_links", type_="check"
    )
    op.create_check_constraint(
        "ck_skill_links_entity_type_values",
        "skill_links",
        "entity_type IN ('PROJECT', 'EXPERIENCE', 'ACHIEVEMENT', 'EDUCATION')",
    )
    op.drop_index("idx_program_links_user_entity", table_name="program_links")
    op.drop_index("idx_program_links_program_id", table_name="program_links")
    op.drop_table("program_links")
    op.drop_index("idx_programs_user_dates", table_name="programs")
    op.drop_index("idx_programs_user_id", table_name="programs")
    op.drop_table("programs")

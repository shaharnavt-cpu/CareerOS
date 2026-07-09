"""Add Application Intelligence persistence.

Revision ID: 20260709_0006
Revises: 20260708_0005
Create Date: 2026-07-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260709_0006"
down_revision: str | None = "20260708_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "application_opportunities",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("organization", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("detected_role_type", sa.Text(), nullable=True),
        sa.Column("detected_skills", postgresql.JSONB(), nullable=False),
        sa.Column("detected_keywords", postgresql.JSONB(), nullable=False),
        sa.Column("detected_responsibilities", postgresql.JSONB(), nullable=False),
        sa.Column("detected_questions", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), server_default="ANALYZED", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_application_opportunities_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_opportunities")),
    )
    op.create_index(
        "idx_application_opportunities_user_id",
        "application_opportunities",
        ["user_id"],
    )
    op.create_index(
        "idx_application_opportunities_user_status",
        "application_opportunities",
        ["user_id", "status"],
    )

    op.create_table(
        "application_questions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.Text(), nullable=False),
        sa.Column("detected_intent", sa.Text(), nullable=False),
        sa.Column("required_themes", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), server_default="OPEN", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["application_opportunities.id"],
            name=op.f(
                "fk_application_questions_opportunity_id_application_opportunities"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_application_questions_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_questions")),
    )
    op.create_index(
        "idx_application_questions_user_id", "application_questions", ["user_id"]
    )
    op.create_index(
        "idx_application_questions_opportunity_id",
        "application_questions",
        ["opportunity_id"],
    )

    op.create_table(
        "application_memory_matches",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("canonical_memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("match_reason", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("themes_matched", postgresql.JSONB(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["canonical_memory_id"],
            ["canonical_memory_records.id"],
            name=op.f(
                "fk_application_memory_matches_canonical_memory_id_canonical_memory_records"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["application_opportunities.id"],
            name=op.f(
                "fk_application_memory_matches_opportunity_id_application_opportunities"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["application_questions.id"],
            name=op.f(
                "fk_application_memory_matches_question_id_application_questions"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_application_memory_matches_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_memory_matches")),
        sa.UniqueConstraint(
            "opportunity_id",
            "question_id",
            "canonical_memory_id",
            name="uq_application_memory_matches_scope_memory",
        ),
    )
    op.create_index(
        "idx_application_matches_user_id",
        "application_memory_matches",
        ["user_id"],
    )
    op.create_index(
        "idx_application_matches_opportunity_id",
        "application_memory_matches",
        ["opportunity_id"],
    )
    op.create_index(
        "idx_application_matches_question_id",
        "application_memory_matches",
        ["question_id"],
    )
    op.create_index(
        "idx_application_matches_canonical_memory_id",
        "application_memory_matches",
        ["canonical_memory_id"],
    )

    op.create_table(
        "application_drafts",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("draft_type", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("draft_text", sa.Text(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.Text(), server_default="DRAFT", nullable=False),
        sa.Column("draft_metadata", postgresql.JSONB(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["application_opportunities.id"],
            name=op.f("fk_application_drafts_opportunity_id_application_opportunities"),
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["application_questions.id"],
            name=op.f("fk_application_drafts_question_id_application_questions"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_application_drafts_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_drafts")),
    )
    op.create_index("idx_application_drafts_user_id", "application_drafts", ["user_id"])
    op.create_index(
        "idx_application_drafts_opportunity_id",
        "application_drafts",
        ["opportunity_id"],
    )
    op.create_index(
        "idx_application_drafts_question_id",
        "application_drafts",
        ["question_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_application_drafts_question_id", table_name="application_drafts")
    op.drop_index(
        "idx_application_drafts_opportunity_id", table_name="application_drafts"
    )
    op.drop_index("idx_application_drafts_user_id", table_name="application_drafts")
    op.drop_table("application_drafts")

    op.drop_index(
        "idx_application_matches_canonical_memory_id",
        table_name="application_memory_matches",
    )
    op.drop_index(
        "idx_application_matches_question_id",
        table_name="application_memory_matches",
    )
    op.drop_index(
        "idx_application_matches_opportunity_id",
        table_name="application_memory_matches",
    )
    op.drop_index(
        "idx_application_matches_user_id", table_name="application_memory_matches"
    )
    op.drop_table("application_memory_matches")

    op.drop_index(
        "idx_application_questions_opportunity_id", table_name="application_questions"
    )
    op.drop_index(
        "idx_application_questions_user_id", table_name="application_questions"
    )
    op.drop_table("application_questions")

    op.drop_index(
        "idx_application_opportunities_user_status",
        table_name="application_opportunities",
    )
    op.drop_index(
        "idx_application_opportunities_user_id",
        table_name="application_opportunities",
    )
    op.drop_table("application_opportunities")

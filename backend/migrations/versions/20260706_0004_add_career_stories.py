"""Add first-class Career Story Intelligence persistence.

Revision ID: 20260706_0004
Revises: 20260703_0003
Create Date: 2026-07-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260706_0004"
down_revision: str | None = "20260703_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ENTITY_TYPES = "'PROGRAM', 'EDUCATION', 'EXPERIENCE', 'PROJECT', 'ACHIEVEMENT', 'SKILL'"


def upgrade() -> None:
    """Create stories, chapters, memberships, and evidence links."""

    op.create_table(
        "stories",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("primary_goal", sa.Text(), nullable=True),
        sa.Column("transformation", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("status", sa.Text(), server_default="PROPOSED", nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
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
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_stories_confidence_range"),
        ),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'ARCHIVED')",
            name=op.f("ck_stories_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_stories_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stories")),
    )
    op.create_index("idx_stories_user_id", "stories", ["user_id"])
    op.create_index("idx_stories_user_status", "stories", ["user_id", "status"])

    op.create_table(
        "story_chapters",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
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
            "position >= 0", name=op.f("ck_story_chapters_position_nonnegative")
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR start_date <= end_date",
            name=op.f("ck_story_chapters_date_range"),
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            name=op.f("fk_story_chapters_story_id_stories"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_story_chapters_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_story_chapters")),
        sa.UniqueConstraint(
            "story_id",
            "position",
            name=op.f("uq_story_chapters_story_id"),
        ),
    )
    op.create_index("idx_story_chapters_user_id", "story_chapters", ["user_id"])
    op.create_index("idx_story_chapters_story_id", "story_chapters", ["story_id"])

    op.create_table(
        "story_memberships",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"entity_type IN ({ENTITY_TYPES})",
            name=op.f("ck_story_memberships_entity_type_values"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_story_memberships_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["chapter_id"],
            ["story_chapters.id"],
            name=op.f("fk_story_memberships_chapter_id_story_chapters"),
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            name=op.f("fk_story_memberships_story_id_stories"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_story_memberships_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_story_memberships")),
        sa.UniqueConstraint(
            "story_id",
            "entity_type",
            "entity_id",
            name=op.f("uq_story_memberships_story_id"),
        ),
    )
    op.create_index("idx_story_memberships_user_id", "story_memberships", ["user_id"])
    op.create_index("idx_story_memberships_story_id", "story_memberships", ["story_id"])
    op.create_index(
        "idx_story_memberships_user_entity",
        "story_memberships",
        ["user_id", "entity_type", "entity_id"],
    )
    op.create_index(
        "idx_story_memberships_chapter_id", "story_memberships", ["chapter_id"]
    )

    op.create_table(
        "story_evidence",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "relationship_type", sa.Text(), server_default="SUPPORTS", nullable=False
        ),
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
            name=op.f("fk_story_evidence_evidence_item_id_evidence_items"),
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            name=op.f("fk_story_evidence_story_id_stories"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_story_evidence_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_story_evidence")),
        sa.UniqueConstraint(
            "story_id",
            "evidence_item_id",
            name=op.f("uq_story_evidence_story_id"),
        ),
    )
    op.create_index("idx_story_evidence_user_id", "story_evidence", ["user_id"])
    op.create_index("idx_story_evidence_story_id", "story_evidence", ["story_id"])
    op.create_index(
        "idx_story_evidence_evidence_item_id",
        "story_evidence",
        ["evidence_item_id"],
    )


def downgrade() -> None:
    """Remove the Career Story tables in reverse dependency order."""

    op.drop_index("idx_story_evidence_evidence_item_id", table_name="story_evidence")
    op.drop_index("idx_story_evidence_story_id", table_name="story_evidence")
    op.drop_index("idx_story_evidence_user_id", table_name="story_evidence")
    op.drop_table("story_evidence")
    op.drop_index("idx_story_memberships_chapter_id", table_name="story_memberships")
    op.drop_index("idx_story_memberships_user_entity", table_name="story_memberships")
    op.drop_index("idx_story_memberships_story_id", table_name="story_memberships")
    op.drop_index("idx_story_memberships_user_id", table_name="story_memberships")
    op.drop_table("story_memberships")
    op.drop_index("idx_story_chapters_story_id", table_name="story_chapters")
    op.drop_index("idx_story_chapters_user_id", table_name="story_chapters")
    op.drop_table("story_chapters")
    op.drop_index("idx_stories_user_status", table_name="stories")
    op.drop_index("idx_stories_user_id", table_name="stories")
    op.drop_table("stories")

"""Add reviewed project evidence enrichment.

Revision ID: 20260713_0010
Revises: 20260713_0009
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260713_0010"
down_revision: str | None = "20260713_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "career_memory_enrichments",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "canonical_memory_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_label", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="PROPOSED", nullable=False),
        sa.Column("enrichment_type", sa.Text(), nullable=False),
        sa.Column("structured_enrichment", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("identity_resolution", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
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
            "status IN ('PROPOSED', 'APPROVED', 'REJECTED', 'ARCHIVED')",
            name=op.f(
                "ck_career_memory_enrichments_"
                "career_memory_enrichment_status_values"
            ),
        ),
        sa.CheckConstraint(
            "enrichment_type IN ('PROJECT_CONTEXT', 'PROJECT_METHOD', "
            "'PROJECT_RESULT', 'PROJECT_LIMITATION', 'PROJECT_OUTPUT', "
            "'PROJECT_ROLE_RELEVANCE', 'PROJECT_FULL_ENRICHMENT', "
            "'MEMORY_MERGE_SUGGESTION')",
            name=op.f(
                "ck_career_memory_enrichments_"
                "career_memory_enrichment_type_values"
            ),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f(
                "ck_career_memory_enrichments_"
                "career_memory_enrichment_confidence_range"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["canonical_memory_id"],
            ["canonical_memory_records.id"],
            name=op.f(
                "fk_career_memory_enrichments_"
                "canonical_memory_id_canonical_memory_records"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["listening_sources.id"],
            name=op.f("fk_career_memory_enrichments_source_id_listening_sources"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_career_memory_enrichments_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_career_memory_enrichments")),
    )
    op.create_index(
        "idx_memory_enrichments_user_status",
        "career_memory_enrichments",
        ["user_id", "status"],
    )
    op.create_index(
        "idx_memory_enrichments_memory_id",
        "career_memory_enrichments",
        ["canonical_memory_id"],
    )
    op.create_index(
        "idx_memory_enrichments_source_id",
        "career_memory_enrichments",
        ["source_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_memory_enrichments_source_id",
        table_name="career_memory_enrichments",
    )
    op.drop_index(
        "idx_memory_enrichments_memory_id",
        table_name="career_memory_enrichments",
    )
    op.drop_index(
        "idx_memory_enrichments_user_status",
        table_name="career_memory_enrichments",
    )
    op.drop_table("career_memory_enrichments")

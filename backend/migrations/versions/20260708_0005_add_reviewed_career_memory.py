"""Add durable proposal review and canonical memory projection.

Revision ID: 20260708_0005
Revises: 20260706_0004
Create Date: 2026-07-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260708_0005"
down_revision: str | None = "20260706_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_proposals",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposal_type", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("identity_key", sa.Text(), nullable=False),
        sa.Column("proposal_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "decision", sa.Text(), server_default="PENDING_REVIEW", nullable=False
        ),
        sa.Column("edited", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("canonical_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["user_id"], ["users.id"], name=op.f("fk_review_proposals_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_proposals")),
    )
    op.create_index(
        "idx_review_proposals_user_status", "review_proposals", ["user_id", "decision"]
    )

    op.create_table(
        "canonical_memory_records",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_key", sa.Text(), nullable=False),
        sa.Column("memory_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("structured_fields", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("source_ids", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("review_proposal_id", sa.Text(), nullable=False),
        sa.Column("typed_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            ["review_proposal_id"],
            ["review_proposals.id"],
            name=op.f(
                "fk_canonical_memory_records_review_proposal_id_review_proposals"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_canonical_memory_records_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canonical_memory_records")),
        sa.UniqueConstraint(
            "user_id", "identity_key", name=op.f("uq_canonical_memory_records_user_id")
        ),
    )
    op.create_index(
        "idx_canonical_memory_user_type",
        "canonical_memory_records",
        ["user_id", "memory_type"],
    )
    op.create_index(
        "idx_canonical_memory_review_proposal_id",
        "canonical_memory_records",
        ["review_proposal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_canonical_memory_review_proposal_id",
        table_name="canonical_memory_records",
    )
    op.drop_index(
        "idx_canonical_memory_user_type", table_name="canonical_memory_records"
    )
    op.drop_table("canonical_memory_records")
    op.drop_index("idx_review_proposals_user_status", table_name="review_proposals")
    op.drop_table("review_proposals")

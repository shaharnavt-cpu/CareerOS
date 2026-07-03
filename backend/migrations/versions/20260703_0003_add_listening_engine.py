"""Add durable staging for the Multi-Source Listening Engine.

Revision ID: 20260703_0003
Revises: 20260702_0002
Create Date: 2026-07-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260703_0003"
down_revision: str | None = "20260702_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE_TYPES = (
    "'RESUME', 'CONVERSATION', 'MANUAL', 'TRANSCRIPT', 'LINKEDIN', "
    "'PORTFOLIO', 'GITHUB', 'CERTIFICATE', 'GENERIC_DOCUMENT'"
)
EVIDENCE_CATEGORIES = (
    "'EDUCATION', 'PROGRAM', 'EXPERIENCE', 'PROJECT', 'SKILL', "
    "'ACHIEVEMENT', 'ORGANIZATION', 'DATE', 'ROLE', 'CONTACT', 'LINK', 'UNKNOWN'"
)


def upgrade() -> None:
    """Create non-canonical source, evidence, fusion, and provenance tables."""

    op.create_table(
        "listening_sources",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("media_type", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("adapter_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="RECEIVED", nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
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
        sa.CheckConstraint(
            f"source_type IN ({SOURCE_TYPES})",
            name=op.f("ck_listening_sources_source_type_values"),
        ),
        sa.CheckConstraint(
            "status IN ('RECEIVED', 'LISTENING', 'READY', 'FAILED')",
            name=op.f("ck_listening_sources_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_listening_sources_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listening_sources")),
        sa.UniqueConstraint(
            "user_id",
            "source_type",
            "content_hash",
            name=op.f("uq_listening_sources_user_id"),
        ),
    )
    op.create_index("idx_listening_sources_user_id", "listening_sources", ["user_id"])
    op.create_index(
        "idx_listening_sources_user_received",
        "listening_sources",
        ["user_id", "received_at"],
    )

    op.create_table(
        "listening_evidence",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("raw_excerpt", sa.Text(), nullable=False),
        sa.Column("normalized_excerpt", sa.Text(), nullable=True),
        sa.Column("excerpt_hash", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("location", postgresql.JSONB(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column(
            "extracted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"source_type IN ({SOURCE_TYPES})",
            name=op.f("ck_listening_evidence_source_type_values"),
        ),
        sa.CheckConstraint(
            f"category IN ({EVIDENCE_CATEGORIES})",
            name=op.f("ck_listening_evidence_category_values"),
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_listening_evidence_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["listening_sources.id"],
            name=op.f("fk_listening_evidence_source_id_listening_sources"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_listening_evidence_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listening_evidence")),
        sa.UniqueConstraint(
            "source_id", "excerpt_hash", name=op.f("uq_listening_evidence_source_id")
        ),
    )
    op.create_index("idx_listening_evidence_user_id", "listening_evidence", ["user_id"])
    op.create_index(
        "idx_listening_evidence_source_id", "listening_evidence", ["source_id"]
    )
    op.create_index(
        "idx_listening_evidence_user_category",
        "listening_evidence",
        ["user_id", "category"],
    )

    op.create_table(
        "listening_evidence_clusters",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("normalized_key", sa.Text(), nullable=False),
        sa.Column(
            "has_conflicts", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("conflicting_claims", postgresql.JSONB(), nullable=False),
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
            f"category IN ({EVIDENCE_CATEGORIES})",
            name=op.f("ck_listening_evidence_clusters_category_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_listening_evidence_clusters_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listening_evidence_clusters")),
        sa.UniqueConstraint(
            "user_id",
            "category",
            "normalized_key",
            name=op.f("uq_listening_evidence_clusters_user_id"),
        ),
    )
    op.create_index(
        "idx_listening_clusters_user_id", "listening_evidence_clusters", ["user_id"]
    )

    op.create_table(
        "listening_cluster_members",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "relationship_type IN ('SUPPORTING', 'DUPLICATE', 'CONFLICTING')",
            name=op.f("ck_listening_cluster_members_relationship_type_values"),
        ),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["listening_evidence_clusters.id"],
            name=op.f(
                "fk_listening_cluster_members_cluster_id_listening_evidence_clusters"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["listening_evidence.id"],
            name=op.f("fk_listening_cluster_members_evidence_id_listening_evidence"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_listening_cluster_members_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listening_cluster_members")),
        sa.UniqueConstraint(
            "cluster_id",
            "evidence_id",
            name=op.f("uq_listening_cluster_members_cluster_id"),
        ),
    )
    op.create_index(
        "idx_listening_members_user_id", "listening_cluster_members", ["user_id"]
    )
    op.create_index(
        "idx_listening_members_cluster_id",
        "listening_cluster_members",
        ["cluster_id"],
    )
    op.create_index(
        "idx_listening_members_evidence_id",
        "listening_cluster_members",
        ["evidence_id"],
    )

    op.create_table(
        "listening_proposal_evidence_links",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proposal_id", sa.Text(), nullable=False),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["listening_evidence_clusters.id"],
            name=op.f(
                "fk_listening_proposal_evidence_links_cluster_id_"
                "listening_evidence_clusters"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["listening_evidence.id"],
            name=op.f(
                "fk_listening_proposal_evidence_links_evidence_id_listening_evidence"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_listening_proposal_evidence_links_user_id_users"),
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_listening_proposal_evidence_links")
        ),
        sa.UniqueConstraint(
            "proposal_id",
            "evidence_id",
            name=op.f("uq_listening_proposal_evidence_links_proposal_id"),
        ),
    )
    op.create_index(
        "idx_listening_proposal_links_user_id",
        "listening_proposal_evidence_links",
        ["user_id"],
    )
    op.create_index(
        "idx_listening_proposal_links_proposal_id",
        "listening_proposal_evidence_links",
        ["proposal_id"],
    )
    op.create_index(
        "idx_listening_proposal_links_cluster_id",
        "listening_proposal_evidence_links",
        ["cluster_id"],
    )
    op.create_index(
        "idx_listening_proposal_links_evidence_id",
        "listening_proposal_evidence_links",
        ["evidence_id"],
    )


def downgrade() -> None:
    """Remove all listening staging tables in reverse dependency order."""

    op.drop_index(
        "idx_listening_proposal_links_evidence_id",
        table_name="listening_proposal_evidence_links",
    )
    op.drop_index(
        "idx_listening_proposal_links_cluster_id",
        table_name="listening_proposal_evidence_links",
    )
    op.drop_index(
        "idx_listening_proposal_links_proposal_id",
        table_name="listening_proposal_evidence_links",
    )
    op.drop_index(
        "idx_listening_proposal_links_user_id",
        table_name="listening_proposal_evidence_links",
    )
    op.drop_table("listening_proposal_evidence_links")
    op.drop_index(
        "idx_listening_members_evidence_id", table_name="listening_cluster_members"
    )
    op.drop_index(
        "idx_listening_members_cluster_id", table_name="listening_cluster_members"
    )
    op.drop_index(
        "idx_listening_members_user_id", table_name="listening_cluster_members"
    )
    op.drop_table("listening_cluster_members")
    op.drop_index(
        "idx_listening_clusters_user_id", table_name="listening_evidence_clusters"
    )
    op.drop_table("listening_evidence_clusters")
    op.drop_index(
        "idx_listening_evidence_user_category", table_name="listening_evidence"
    )
    op.drop_index("idx_listening_evidence_source_id", table_name="listening_evidence")
    op.drop_index("idx_listening_evidence_user_id", table_name="listening_evidence")
    op.drop_table("listening_evidence")
    op.drop_index("idx_listening_sources_user_received", table_name="listening_sources")
    op.drop_index("idx_listening_sources_user_id", table_name="listening_sources")
    op.drop_table("listening_sources")

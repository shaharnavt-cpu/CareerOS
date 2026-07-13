"""Add Proof Artifact Builder persistence.

Revision ID: 20260713_0009
Revises: 20260713_0008
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260713_0009"
down_revision: str | None = "20260713_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "proof_artifacts",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("artifact_type", sa.Text(), nullable=False),
        sa.Column("target_role", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=False),
        sa.Column("source_memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_diagnosis_result_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("status", sa.Text(), server_default="DRAFT", nullable=False),
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
            "artifact_type IN ('CASE_STUDY', 'GITHUB_README', 'PORTFOLIO_PAGE', "
            "'APPLICATION_UPLOAD', 'OUTREACH_SUMMARY', 'INTERVIEW_STORY', "
            "'RESUME_BULLETS')",
            name=op.f("ck_proof_artifacts_proof_artifact_type_values"),
        ),
        sa.CheckConstraint(
            "target_audience IN ('APPLICATION_UPLOAD', 'PORTFOLIO', 'GITHUB', "
            "'OUTREACH', 'INTERVIEW_PREP', 'GENERAL')",
            name=op.f("ck_proof_artifacts_proof_artifact_audience_values"),
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'REVIEWED', 'READY', 'ARCHIVED')",
            name=op.f("ck_proof_artifacts_proof_artifact_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["source_diagnosis_result_id"],
            ["diagnosis_results.id"],
            name=op.f(
                "fk_proof_artifacts_source_diagnosis_result_id_diagnosis_results"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_memory_id"],
            ["canonical_memory_records.id"],
            name=op.f("fk_proof_artifacts_source_memory_id_canonical_memory_records"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_proof_artifacts_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_proof_artifacts")),
    )
    op.create_index("idx_proof_artifacts_user_id", "proof_artifacts", ["user_id"])
    op.create_index(
        "idx_proof_artifacts_user_status",
        "proof_artifacts",
        ["user_id", "status"],
    )
    op.create_index(
        "idx_proof_artifacts_source_memory_id",
        "proof_artifacts",
        ["source_memory_id"],
    )
    op.create_index(
        "idx_proof_artifacts_source_diagnosis_result_id",
        "proof_artifacts",
        ["source_diagnosis_result_id"],
    )

    op.create_table(
        "proof_artifact_versions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_sections", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("outcome_signal_ids", postgresql.JSONB(), nullable=False),
        sa.Column("warnings", postgresql.JSONB(), nullable=False),
        sa.Column("readiness_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("readiness_label", sa.Text(), nullable=False),
        sa.Column("supporting_variants", postgresql.JSONB(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "readiness_label IN ('NEEDS_EVIDENCE', 'DRAFTABLE', "
            "'STRONG_DRAFT', 'READY_TO_SHARE')",
            name=op.f("ck_proof_artifact_versions_proof_artifact_readiness_values"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name=op.f(
                "ck_proof_artifact_versions_proof_artifact_version_number_positive"
            ),
        ),
        sa.CheckConstraint(
            "readiness_score >= 0 AND readiness_score <= 1",
            name=op.f(
                "ck_proof_artifact_versions_proof_artifact_readiness_score_range"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["proof_artifacts.id"],
            name=op.f("fk_proof_artifact_versions_artifact_id_proof_artifacts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_proof_artifact_versions_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_proof_artifact_versions")),
        sa.UniqueConstraint(
            "artifact_id",
            "version_number",
            name="uq_proof_artifact_versions_artifact_version",
        ),
    )
    op.create_index(
        "idx_proof_artifact_versions_user_id",
        "proof_artifact_versions",
        ["user_id"],
    )
    op.create_index(
        "idx_proof_artifact_versions_artifact_id",
        "proof_artifact_versions",
        ["artifact_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_proof_artifact_versions_artifact_id",
        table_name="proof_artifact_versions",
    )
    op.drop_index(
        "idx_proof_artifact_versions_user_id",
        table_name="proof_artifact_versions",
    )
    op.drop_table("proof_artifact_versions")
    op.drop_index(
        "idx_proof_artifacts_source_diagnosis_result_id",
        table_name="proof_artifacts",
    )
    op.drop_index(
        "idx_proof_artifacts_source_memory_id",
        table_name="proof_artifacts",
    )
    op.drop_index("idx_proof_artifacts_user_status", table_name="proof_artifacts")
    op.drop_index("idx_proof_artifacts_user_id", table_name="proof_artifacts")
    op.drop_table("proof_artifacts")

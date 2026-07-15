"""Add versioned application packages.

Revision ID: 20260715_0011
Revises: 20260713_0010
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260715_0011"
down_revision: str | None = "20260713_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "application_packages",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("role_title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("job_type", sa.Text(), nullable=True),
        sa.Column("target_description", sa.Text(), nullable=False),
        sa.Column("required_skills", postgresql.JSONB(), nullable=False),
        sa.Column("preferred_skills", postgresql.JSONB(), nullable=False),
        sa.Column("responsibilities", postgresql.JSONB(), nullable=False),
        sa.Column("selected_memory_ids", postgresql.JSONB(), nullable=False),
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
            "status IN ('DRAFT', 'READY', 'ARCHIVED')",
            name=op.f("ck_application_packages_application_package_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["application_opportunities.id"],
            name=op.f(
                "fk_application_packages_opportunity_id_application_opportunities"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_application_packages_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_packages")),
    )
    op.create_index(
        "idx_application_packages_user_id",
        "application_packages",
        ["user_id"],
    )
    op.create_index(
        "idx_application_packages_user_status",
        "application_packages",
        ["user_id", "status"],
    )
    op.create_index(
        "idx_application_packages_opportunity_id",
        "application_packages",
        ["opportunity_id"],
    )

    op.create_table(
        "application_package_versions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("target_snapshot_json", postgresql.JSONB(), nullable=False),
        sa.Column("selected_memory_ids_json", postgresql.JSONB(), nullable=False),
        sa.Column("input_fingerprint", sa.Text(), nullable=False),
        sa.Column(
            "compiled_profile_snapshots_json", postgresql.JSONB(), nullable=False
        ),
        sa.Column("generated_outputs_json", postgresql.JSONB(), nullable=False),
        sa.Column("evidence_trace_json", postgresql.JSONB(), nullable=False),
        sa.Column("warnings_json", postgresql.JSONB(), nullable=False),
        sa.Column("claim_ledger_json", postgresql.JSONB(), nullable=False),
        sa.Column("memory_ids_used_json", postgresql.JSONB(), nullable=False),
        sa.Column("enrichment_ids_used_json", postgresql.JSONB(), nullable=False),
        sa.Column("outcome_signal_ids_used_json", postgresql.JSONB(), nullable=False),
        sa.Column("user_edits_json", postgresql.JSONB(), nullable=False),
        sa.Column("generator_version", sa.Text(), nullable=False),
        sa.Column("generation_reason", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name=op.f(
                "ck_application_package_versions_"
                "application_package_version_number_positive"
            ),
        ),
        sa.CheckConstraint(
            "generation_reason IN ('GENERATED', 'REGENERATED', 'USER_EDIT')",
            name=op.f(
                "ck_application_package_versions_"
                "application_package_version_reason_values"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["application_packages.id"],
            name=op.f(
                "fk_application_package_versions_package_id_application_packages"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_application_package_versions_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_package_versions")),
        sa.UniqueConstraint(
            "package_id",
            "version_number",
            name="uq_application_package_versions_package_version",
        ),
    )
    op.create_index(
        "idx_application_package_versions_user_id",
        "application_package_versions",
        ["user_id"],
    )
    op.create_index(
        "idx_application_package_versions_package_id",
        "application_package_versions",
        ["package_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_application_package_versions_package_id",
        table_name="application_package_versions",
    )
    op.drop_index(
        "idx_application_package_versions_user_id",
        table_name="application_package_versions",
    )
    op.drop_table("application_package_versions")
    op.drop_index(
        "idx_application_packages_opportunity_id",
        table_name="application_packages",
    )
    op.drop_index(
        "idx_application_packages_user_status",
        table_name="application_packages",
    )
    op.drop_index(
        "idx_application_packages_user_id",
        table_name="application_packages",
    )
    op.drop_table("application_packages")

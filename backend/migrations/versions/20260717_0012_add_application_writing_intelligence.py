"""Add application-writing intelligence and safe provider metadata.

Revision ID: 20260717_0012
Revises: 20260715_0011
Create Date: 2026-07-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260717_0012"
down_revision: str | None = "20260715_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table = "application_package_versions"
    for name in (
        "writing_intelligence_json",
        "quality_review_json",
        "provider_metadata_json",
        "validation_summary_json",
    ):
        op.add_column(
            table,
            sa.Column(
                name,
                postgresql.JSONB(),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
        )
        op.alter_column(table, name, server_default=None)


def downgrade() -> None:
    table = "application_package_versions"
    for name in (
        "validation_summary_json",
        "provider_metadata_json",
        "quality_review_json",
        "writing_intelligence_json",
    ):
        op.drop_column(table, name)

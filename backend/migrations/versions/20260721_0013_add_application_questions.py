"""Add explicit application questions to package workspaces.

Revision ID: 20260721_0013
Revises: 20260717_0012
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260721_0013"
down_revision: str | None = "20260717_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "application_packages",
        sa.Column(
            "application_questions",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column(
        "application_packages",
        "application_questions",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("application_packages", "application_questions")

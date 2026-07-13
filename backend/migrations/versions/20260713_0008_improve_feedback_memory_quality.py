"""Improve feedback memory quality and diagnosis outcome signals.

Revision ID: 20260713_0008
Revises: 20260713_0007
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260713_0008"
down_revision: str | None = "20260713_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "diagnosis_results",
        sa.Column(
            "outcome_signals",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("diagnosis_results", "outcome_signals", server_default=None)

    op.add_column(
        "career_feedback_events",
        sa.Column("artifact_type", sa.Text(), nullable=True),
    )
    op.add_column(
        "career_feedback_events",
        sa.Column("artifact_label", sa.Text(), nullable=True),
    )
    op.add_column(
        "career_feedback_events",
        sa.Column("outcome", sa.Text(), nullable=True),
    )
    op.add_column(
        "career_feedback_events",
        sa.Column(
            "event_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("career_feedback_events", "event_metadata", server_default=None)


def downgrade() -> None:
    op.drop_column("career_feedback_events", "event_metadata")
    op.drop_column("career_feedback_events", "outcome")
    op.drop_column("career_feedback_events", "artifact_label")
    op.drop_column("career_feedback_events", "artifact_type")
    op.drop_column("diagnosis_results", "outcome_signals")

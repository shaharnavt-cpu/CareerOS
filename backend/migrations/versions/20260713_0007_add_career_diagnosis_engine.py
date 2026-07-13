"""Add Career Diagnosis Engine persistence.

Revision ID: 20260713_0007
Revises: 20260709_0006
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260713_0007"
down_revision: str | None = "20260709_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "diagnosis_sessions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_role", sa.Text(), nullable=True),
        sa.Column("target_context", sa.Text(), nullable=True),
        sa.Column("frustration_context", sa.Text(), nullable=True),
        sa.Column("selected_focus", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default="RUNNING", nullable=False),
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
            "status IN ('RUNNING', 'COMPLETE', 'NEEDS_MEMORY', 'FAILED')",
            name=op.f("ck_diagnosis_sessions_diagnosis_session_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_diagnosis_sessions_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnosis_sessions")),
    )
    op.create_index("idx_diagnosis_sessions_user_id", "diagnosis_sessions", ["user_id"])
    op.create_index(
        "idx_diagnosis_sessions_user_status",
        "diagnosis_sessions",
        ["user_id", "status"],
    )

    op.create_table(
        "diagnosis_results",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("career_identity", sa.Text(), nullable=False),
        sa.Column("identity_rationale", sa.Text(), nullable=False),
        sa.Column("evidence_map", postgresql.JSONB(), nullable=False),
        sa.Column("recognition_gap", sa.Text(), nullable=False),
        sa.Column("missing_proof", postgresql.JSONB(), nullable=False),
        sa.Column("proof_sprint", postgresql.JSONB(), nullable=False),
        sa.Column("do_not_waste_time", sa.Text(), nullable=False),
        sa.Column("exact_next_actions", postgresql.JSONB(), nullable=False),
        sa.Column("exact_messages", postgresql.JSONB(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("evidence_ids", postgresql.JSONB(), nullable=False),
        sa.Column("feedback_event_ids", postgresql.JSONB(), nullable=False),
        sa.Column(
            "diagnosis_version",
            sa.Text(),
            server_default="local-deterministic-v0",
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
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["diagnosis_sessions.id"],
            name=op.f("fk_diagnosis_results_session_id_diagnosis_sessions"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_diagnosis_results_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_diagnosis_results")),
        sa.UniqueConstraint("session_id", name=op.f("uq_diagnosis_results_session_id")),
    )
    op.create_index(
        "idx_diagnosis_results_session_id", "diagnosis_results", ["session_id"]
    )
    op.create_index("idx_diagnosis_results_user_id", "diagnosis_results", ["user_id"])

    op.create_table(
        "career_feedback_events",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_note", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("structured_summary", sa.Text(), nullable=False),
        sa.Column("related_memory_ids", postgresql.JSONB(), nullable=False),
        sa.Column(
            "related_opportunity_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("related_draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_future_use", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="PROPOSED", nullable=False),
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
            "event_type IN ('ARTIFACT_SUCCESS', 'APPLICATION_OUTCOME', "
            "'DRAFT_FEEDBACK', 'POSITIONING_RULE', 'MEMORY_USAGE_RULE', "
            "'GENERAL_LEARNING', 'UNKNOWN')",
            name=op.f("ck_career_feedback_events_career_feedback_event_type_values"),
        ),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'APPROVED', 'ARCHIVED')",
            name=op.f("ck_career_feedback_events_career_feedback_status_values"),
        ),
        sa.ForeignKeyConstraint(
            ["related_draft_id"],
            ["application_drafts.id"],
            name=op.f("fk_career_feedback_events_related_draft_id_application_drafts"),
        ),
        sa.ForeignKeyConstraint(
            ["related_opportunity_id"],
            ["application_opportunities.id"],
            name=op.f(
                "fk_career_feedback_events_related_opportunity_id_application_opportunities"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_career_feedback_events_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_career_feedback_events")),
    )
    op.create_index(
        "idx_career_feedback_user_id", "career_feedback_events", ["user_id"]
    )
    op.create_index(
        "idx_career_feedback_user_status",
        "career_feedback_events",
        ["user_id", "status"],
    )
    op.create_index(
        "idx_career_feedback_opportunity_id",
        "career_feedback_events",
        ["related_opportunity_id"],
    )
    op.create_index(
        "idx_career_feedback_draft_id",
        "career_feedback_events",
        ["related_draft_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_career_feedback_draft_id", table_name="career_feedback_events")
    op.drop_index(
        "idx_career_feedback_opportunity_id", table_name="career_feedback_events"
    )
    op.drop_index(
        "idx_career_feedback_user_status", table_name="career_feedback_events"
    )
    op.drop_index("idx_career_feedback_user_id", table_name="career_feedback_events")
    op.drop_table("career_feedback_events")

    op.drop_index(
        "idx_diagnosis_results_user_id",
        table_name="diagnosis_results",
        if_exists=True,
    )
    op.drop_index("idx_diagnosis_results_session_id", table_name="diagnosis_results")
    op.drop_table("diagnosis_results")

    op.drop_index("idx_diagnosis_sessions_user_status", table_name="diagnosis_sessions")
    op.drop_index("idx_diagnosis_sessions_user_id", table_name="diagnosis_sessions")
    op.drop_table("diagnosis_sessions")

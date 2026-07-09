"""PostgreSQL coverage for durable review decisions and dashboard hydration."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal, engine
from app.models import (
    CanonicalMemoryRecord,
    Education,
    EvidenceItem,
    EvidenceLink,
    ReviewProposal,
    Skill,
    User,
)
from app.schemas.knowledge import (
    ApprovalState,
    DurableReviewStatus,
    EntityType,
    EvidenceReference,
    KnowledgeProposal,
    ProposalReviewRequest,
    ReviewDecision,
    ReviewProposalType,
    SourceType,
)
from app.services.review_service import ReviewedCareerMemoryService


def _require_postgres() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")


def _cleanup_user(user_id: uuid.UUID) -> None:
    with SessionLocal.begin() as session:
        for model in (
            CanonicalMemoryRecord,
            ReviewProposal,
            EvidenceLink,
            EvidenceItem,
            Skill,
            Education,
        ):
            session.execute(delete(model).where(model.user_id == user_id))
        session.execute(delete(User).where(User.id == user_id))


def _evidence(source_id: str = "resume-source") -> EvidenceReference:
    return EvidenceReference(
        source_id=source_id,
        source_type=SourceType.RESUME,
        title="Arnav AI Analyst Resume.pdf",
        excerpt="The University of Texas at Dallas May 2027",
        evidence_id=uuid.uuid4(),
        category="EDUCATION",
        confidence=0.93,
    )


def _proposal(
    *,
    proposal_id: str | None = None,
    proposed_value: dict[str, Any] | None = None,
    evidence: list[EvidenceReference] | None = None,
) -> KnowledgeProposal:
    value = proposed_value or {
        "institution_name": "University of Texas at Dallas",
        "degree": "Master of Science",
        "field_of_study": "Business Analytics and AI",
        "track": "Data Science",
        "end_date": "2027-05-01",
    }
    return KnowledgeProposal(
        id=proposal_id or f"proposal-{uuid.uuid4()}",
        entity_type=EntityType.EDUCATION,
        proposal_type=ReviewProposalType.EDUCATION,
        proposed_value=value,
        confidence=0.94,
        evidence=evidence or [_evidence()],
        reasoning_summary=(
            "Resume and transcript evidence identify the same education record."
        ),
    )


def _approve(
    service: ReviewedCareerMemoryService,
    proposal: KnowledgeProposal,
) -> None:
    with SessionLocal() as session:
        service.review(
            session,
            ProposalReviewRequest(
                proposal=proposal,
                decision=ReviewDecision.APPROVE,
            ),
        )


def test_approve_persists_decision_canonical_memory_and_evidence_links() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    service = ReviewedCareerMemoryService(user_id=user_id)
    proposal = _proposal()

    try:
        _approve(service, proposal)

        with SessionLocal() as session:
            review = session.get(ReviewProposal, proposal.id)
            memory = session.scalar(
                select(CanonicalMemoryRecord).where(
                    CanonicalMemoryRecord.user_id == user_id
                )
            )
            dashboard = service.dashboard(session)
            evidence_links = session.scalar(
                select(func.count(EvidenceLink.id)).where(
                    EvidenceLink.user_id == user_id
                )
            )

        assert review is not None
        assert review.decision == DurableReviewStatus.APPROVED.value
        assert review.proposal_data["approval_state"] == ApprovalState.CANONICAL.value
        assert memory is not None
        assert memory.structured_fields["track"] == "Data Science"
        assert memory.evidence_ids == [str(proposal.evidence[0].evidence_id)]
        assert dashboard.counts["EDUCATION"] == 1
        assert dashboard.pending_review_count == 0
        assert dashboard.recent_memories[0].title == "University of Texas at Dallas"
        assert evidence_links == 1
    finally:
        _cleanup_user(user_id)


def test_approving_same_proposal_twice_is_idempotent() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    service = ReviewedCareerMemoryService(user_id=user_id)
    proposal = _proposal()

    try:
        _approve(service, proposal)
        _approve(service, proposal)

        with SessionLocal() as session:
            memory_count = session.scalar(
                select(func.count(CanonicalMemoryRecord.id)).where(
                    CanonicalMemoryRecord.user_id == user_id
                )
            )
            education_count = session.scalar(
                select(func.count(Education.id)).where(Education.user_id == user_id)
            )

        assert memory_count == 1
        assert education_count == 1
    finally:
        _cleanup_user(user_id)


def test_reject_persists_decision_without_creating_canonical_memory() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    service = ReviewedCareerMemoryService(user_id=user_id)
    proposal = _proposal()

    try:
        with SessionLocal() as session:
            response = service.review(
                session,
                ProposalReviewRequest(
                    proposal=proposal,
                    decision=ReviewDecision.REJECT,
                ),
            )
            listed = service.list_proposals(session)
            dashboard = service.dashboard(session)

        assert response.proposal.approval_state is ApprovalState.REJECTED
        assert listed[0].approval_state is ApprovalState.REJECTED
        assert dashboard.canonical_total == 0
        assert dashboard.reviewed_count == 1
        assert dashboard.pending_review_count == 0
    finally:
        _cleanup_user(user_id)


def test_dashboard_summary_empty_state_is_demo_safe() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    service = ReviewedCareerMemoryService(user_id=user_id)

    try:
        with SessionLocal() as session:
            dashboard = service.dashboard(session)

        assert dashboard.canonical_total == 0
        assert dashboard.pending_review_count == 0
        assert dashboard.reviewed_count == 0
        assert dashboard.supporting_evidence_count == 0
        assert dashboard.recent_memories == []
        assert dashboard.counts["EDUCATION"] == 0
    finally:
        _cleanup_user(user_id)


def test_edit_persists_changed_fields_and_promotes_edited_memory() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    service = ReviewedCareerMemoryService(user_id=user_id)
    proposal = _proposal()
    edited = proposal.model_copy(
        update={
            "proposed_value": {
                **proposal.proposed_value,
                "institution_name": "The University of Texas at Dallas",
                "track": "Data Science Track",
            }
        }
    )

    try:
        with SessionLocal() as session:
            saved = service.edit(session, edited)
            assert saved.proposed_value["institution_name"] == (
                "The University of Texas at Dallas"
            )

        _approve(service, saved)

        with SessionLocal() as session:
            review = session.get(ReviewProposal, proposal.id)
            memory = session.scalar(
                select(CanonicalMemoryRecord).where(
                    CanonicalMemoryRecord.user_id == user_id
                )
            )
            listed = service.list_proposals(session)

        assert review is not None
        assert review.decision == DurableReviewStatus.EDITED_APPROVED.value
        assert memory is not None
        assert memory.title == "The University of Texas at Dallas"
        assert memory.structured_fields["track"] == "Data Science Track"
        assert listed[0].approval_state is ApprovalState.CANONICAL
    finally:
        _cleanup_user(user_id)

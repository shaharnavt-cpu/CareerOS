"""Unit tests for explicit proposal approval and canonical persistence."""

import uuid
from contextlib import nullcontext
from typing import Any

import pytest
from fastapi import HTTPException

from app.models import EvidenceItem, EvidenceLink, Skill, User
from app.schemas.knowledge import (
    ApprovalState,
    Clarification,
    ClarificationReason,
    EntityType,
    EvidenceReference,
    KnowledgeProposal,
    ProposalReviewRequest,
    ReviewDecision,
    SourceType,
)
from app.services.memory import CareerMemoryService


class FakeSession:
    """Small unit-test session that records atomic persistence work."""

    def __init__(self) -> None:
        self.added: list[Any] = []

    def begin(self) -> Any:
        return nullcontext()

    def get(self, model: type[Any], entity_id: uuid.UUID) -> None:
        del model, entity_id
        return None

    def scalar(self, statement: Any) -> None:
        del statement
        return None

    def add(self, value: Any) -> None:
        self.added.append(value)

    def flush(self) -> None:
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = uuid.uuid4()


def skill_proposal(*, with_clarification: bool = False) -> KnowledgeProposal:
    clarification = None
    if with_clarification:
        clarification = Clarification(
            question="Which source supports the Python skill?",
            reason=ClarificationReason.MISSING_EVIDENCE,
            detail="No supporting source was found.",
        )
    return KnowledgeProposal(
        id="proposal-python",
        entity_type=EntityType.SKILL,
        proposed_value={"name": "Python", "normalized_name": "python"},
        confidence=0.91,
        evidence=[
            EvidenceReference(
                source_id="resume-123",
                source_type=SourceType.RESUME,
                title="Resume",
                excerpt="Skills: Python",
            )
        ],
        reasoning_summary="Python was explicitly listed in the skills section.",
        clarification=clarification,
    )


def test_approval_atomically_adds_user_entity_evidence_and_link() -> None:
    session = FakeSession()
    request = ProposalReviewRequest(
        proposal=skill_proposal(), decision=ReviewDecision.APPROVE
    )

    response = CareerMemoryService().review(session, request)  # type: ignore[arg-type]

    assert response.proposal.approval_state is ApprovalState.CANONICAL
    assert response.canonical_entity_id is not None
    assert any(isinstance(item, User) for item in session.added)
    assert any(isinstance(item, Skill) for item in session.added)
    assert any(isinstance(item, EvidenceItem) for item in session.added)
    assert any(isinstance(item, EvidenceLink) for item in session.added)


def test_approval_is_blocked_until_specific_clarification_is_resolved() -> None:
    request = ProposalReviewRequest(
        proposal=skill_proposal(with_clarification=True),
        decision=ReviewDecision.APPROVE,
    )

    with pytest.raises(HTTPException, match="Resolve the proposal clarification"):
        CareerMemoryService().review(FakeSession(), request)  # type: ignore[arg-type]

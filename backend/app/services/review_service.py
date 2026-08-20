"""Orchestrate durable review decisions and canonical Career Memory."""

import uuid

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.schemas.knowledge import (
    DEMO_USER_ID,
    DashboardSummaryResponse,
    DurableReviewStatus,
    KnowledgeProposal,
    ProposalReviewRequest,
    ProposalReviewResponse,
    ReviewDecision,
)
from app.services.memory import CareerMemoryService
from app.services.review_repository import ReviewRepository


class ReviewedCareerMemoryService:
    def __init__(
        self,
        memory: CareerMemoryService | None = None,
        reviews: ReviewRepository | None = None,
        user_id: uuid.UUID = DEMO_USER_ID,
    ) -> None:
        self._memory = memory or CareerMemoryService()
        self._reviews = reviews or ReviewRepository()
        self._user_id = user_id

    def list_proposals(self, session: Session) -> list[KnowledgeProposal]:
        return self._reviews.list_proposals(session, self._user_id)

    def edit(self, session: Session, proposal: KnowledgeProposal) -> KnowledgeProposal:
        return self._reviews.save_edit(session, proposal, self._user_id)

    def review(
        self, session: Session, request: ProposalReviewRequest
    ) -> ProposalReviewResponse:
        result = self._memory.review(session, request, self._user_id)
        review_status = (
            DurableReviewStatus.REJECTED
            if request.decision is ReviewDecision.REJECT
            else DurableReviewStatus.APPROVED
        )
        try:
            proposal = self._reviews.persist_decision(
                session,
                result.proposal,
                review_status,
                result.canonical_entity_id,
                self._user_id,
            )
        except OperationalError:
            session.rollback()
            if request.decision is not ReviewDecision.REJECT:
                raise
            # Rejection never changes canonical Career Memory. Keep that safety
            # action available during a database outage; durable review history can
            # be retried later, while approvals continue to fail closed.
            proposal = result.proposal
        return ProposalReviewResponse(
            proposal=proposal,
            canonical_entity_id=result.canonical_entity_id,
        )

    def dashboard(self, session: Session) -> DashboardSummaryResponse:
        return self._reviews.dashboard(session, self._user_id)

"""Persistence and read models for reviewed Career Memory proposals."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CanonicalMemoryRecord, ListeningEvidence, ReviewProposal, User
from app.schemas.knowledge import (
    DEMO_USER_ID,
    ApprovalState,
    CanonicalReviewMemory,
    DashboardSummaryResponse,
    DurableReviewStatus,
    KnowledgeProposal,
    ReviewProposalType,
)


class ReviewRepository:
    def upsert_proposals(
        self,
        session: Session,
        proposals: list[KnowledgeProposal],
        user_id: uuid.UUID = DEMO_USER_ID,
    ) -> None:
        self._ensure_user(session, user_id)
        for proposal in proposals:
            record = session.get(ReviewProposal, proposal.id)
            if record is None:
                session.add(self._record(proposal, user_id))
            elif record.decision in {
                DurableReviewStatus.PENDING_REVIEW.value,
                DurableReviewStatus.NEEDS_CLARIFICATION.value,
            }:
                self._apply_proposal(record, proposal)

    def list_proposals(
        self, session: Session, user_id: uuid.UUID = DEMO_USER_ID
    ) -> list[KnowledgeProposal]:
        records = session.scalars(
            select(ReviewProposal)
            .where(ReviewProposal.user_id == user_id)
            .order_by(ReviewProposal.created_at)
        ).all()
        return [self._proposal(record) for record in records]

    def save_edit(
        self,
        session: Session,
        proposal: KnowledgeProposal,
        user_id: uuid.UUID = DEMO_USER_ID,
    ) -> KnowledgeProposal:
        with session.begin():
            self._ensure_user(session, user_id)
            record = session.get(ReviewProposal, proposal.id)
            if record is None:
                record = self._record(proposal, user_id)
                session.add(record)
            self._apply_proposal(record, proposal)
            record.edited = True
            record.decision = (
                DurableReviewStatus.NEEDS_CLARIFICATION.value
                if proposal.clarification
                else DurableReviewStatus.PENDING_REVIEW.value
            )
            record.reviewed_at = None
        return self._proposal(record)

    def persist_decision(
        self,
        session: Session,
        proposal: KnowledgeProposal,
        decision: DurableReviewStatus,
        canonical_entity_id: uuid.UUID | None,
        user_id: uuid.UUID = DEMO_USER_ID,
    ) -> KnowledgeProposal:
        with session.begin():
            self._ensure_user(session, user_id)
            record = session.get(ReviewProposal, proposal.id)
            if record is None:
                record = self._record(proposal, user_id)
                session.add(record)
            if decision is DurableReviewStatus.APPROVED and record.edited:
                decision = DurableReviewStatus.EDITED_APPROVED
            final_state = (
                ApprovalState.REJECTED
                if decision is DurableReviewStatus.REJECTED
                else ApprovalState.CANONICAL
            )
            final = proposal.model_copy(update={"approval_state": final_state})
            self._apply_proposal(record, final)
            record.decision = decision.value
            record.canonical_entity_id = canonical_entity_id
            record.reviewed_at = datetime.now(UTC)
            session.flush()
            if canonical_entity_id is not None:
                self._upsert_canonical(
                    session,
                    record,
                    final,
                    canonical_entity_id,
                    user_id,
                )
        return final

    def dashboard(
        self, session: Session, user_id: uuid.UUID = DEMO_USER_ID
    ) -> DashboardSummaryResponse:
        memories = session.scalars(
            select(CanonicalMemoryRecord)
            .where(CanonicalMemoryRecord.user_id == user_id)
            .order_by(CanonicalMemoryRecord.updated_at.desc())
        ).all()
        proposals = session.scalars(
            select(ReviewProposal).where(ReviewProposal.user_id == user_id)
        ).all()
        counts = {kind.value: 0 for kind in ReviewProposalType}
        for memory in memories:
            counts[memory.memory_type] = counts.get(memory.memory_type, 0) + 1
        pending = sum(
            item.decision
            in {
                DurableReviewStatus.PENDING_REVIEW.value,
                DurableReviewStatus.NEEDS_CLARIFICATION.value,
            }
            for item in proposals
        )
        evidence_count = int(
            session.scalar(
                select(func.count(ListeningEvidence.id)).where(
                    ListeningEvidence.user_id == user_id
                )
            )
            or 0
        )
        core = (
            "EDUCATION",
            "PROGRAM",
            "EXPERIENCE",
            "PROJECT",
            "SKILL_SET",
            "ACHIEVEMENT",
        )
        populated = sum(counts.get(kind, 0) > 0 for kind in core)
        completeness = min(
            100, round((populated / len(core)) * 85 + (15 if memories else 0))
        )
        return DashboardSummaryResponse(
            counts=counts,
            canonical_total=len(memories),
            pending_review_count=pending,
            reviewed_count=len(proposals) - pending,
            proposal_total=len(proposals),
            supporting_evidence_count=evidence_count,
            profile_completeness=completeness,
            recent_memories=[self._memory(item) for item in memories[:6]],
        )

    @classmethod
    def identity_key(cls, proposal: KnowledgeProposal) -> str:
        value = proposal.proposed_value
        keys = {
            ReviewProposalType.EDUCATION: (
                "institution_name",
                "degree",
                "field_of_study",
                "track",
            ),
            ReviewProposalType.EXPERIENCE: (
                "organization_name",
                "title",
                "start_date",
                "end_date",
            ),
            ReviewProposalType.PROJECT: (
                "title",
                "organization",
                "start_date",
                "end_date",
            ),
            ReviewProposalType.SKILL_SET: ("category", "name"),
            ReviewProposalType.PROGRAM: ("name", "organization_name"),
            ReviewProposalType.ACHIEVEMENT: ("title", "context"),
        }.get(proposal.proposal_type, ("name", "title"))
        parts = [str(value.get(key, "")) for key in keys]
        normalized = "|".join(
            re.sub(r"\W+", " ", part.casefold()).strip() for part in parts
        )
        return hashlib.sha256(
            f"{proposal.proposal_type.value}:{normalized}".encode()
        ).hexdigest()

    def _record(
        self, proposal: KnowledgeProposal, user_id: uuid.UUID
    ) -> ReviewProposal:
        return ReviewProposal(
            id=proposal.id,
            user_id=user_id,
            proposal_type=proposal.proposal_type.value,
            entity_type=proposal.entity_type.value,
            title=self._title(proposal),
            identity_key=self.identity_key(proposal),
            proposal_data=proposal.model_dump(mode="json"),
            decision=(
                DurableReviewStatus.NEEDS_CLARIFICATION.value
                if proposal.clarification
                else DurableReviewStatus.PENDING_REVIEW.value
            ),
        )

    def _apply_proposal(
        self, record: ReviewProposal, proposal: KnowledgeProposal
    ) -> None:
        record.proposal_type = proposal.proposal_type.value
        record.entity_type = proposal.entity_type.value
        record.title = self._title(proposal)
        record.identity_key = self.identity_key(proposal)
        record.proposal_data = proposal.model_dump(mode="json")

    def _upsert_canonical(
        self,
        session: Session,
        review: ReviewProposal,
        proposal: KnowledgeProposal,
        typed_entity_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        memory = session.scalar(
            select(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.user_id == user_id,
                CanonicalMemoryRecord.identity_key == review.identity_key,
            )
        )
        if memory is None:
            memory = session.scalar(
                select(CanonicalMemoryRecord).where(
                    CanonicalMemoryRecord.user_id == user_id,
                    CanonicalMemoryRecord.review_proposal_id == proposal.id,
                )
            )
        if memory is None:
            memory = CanonicalMemoryRecord(
                user_id=user_id,
                identity_key=review.identity_key,
                memory_type=proposal.proposal_type.value,
                title=self._title(proposal),
                structured_fields=proposal.proposed_value,
                evidence_ids=[],
                source_ids=[],
                confidence=Decimal(str(proposal.confidence)),
                review_proposal_id=proposal.id,
                typed_entity_id=typed_entity_id,
            )
            session.add(memory)
        memory.identity_key = review.identity_key
        memory.title = self._title(proposal)
        memory.structured_fields = proposal.proposed_value
        memory.evidence_ids = list(
            dict.fromkeys(
                str(item.evidence_id)
                for item in proposal.evidence
                if item.evidence_id is not None
            )
        )
        memory.source_ids = list(
            dict.fromkeys(item.source_id for item in proposal.evidence)
        )
        memory.confidence = Decimal(str(proposal.confidence))
        memory.review_proposal_id = proposal.id
        memory.typed_entity_id = typed_entity_id

    @staticmethod
    def _proposal(record: ReviewProposal) -> KnowledgeProposal:
        return KnowledgeProposal.model_validate(record.proposal_data)

    @staticmethod
    def _title(proposal: KnowledgeProposal) -> str:
        for key in (
            "name",
            "title",
            "project_name",
            "institution_name",
            "organization_name",
        ):
            value = proposal.proposed_value.get(key)
            if value:
                return str(value)
        return proposal.proposal_type.value.replace("_", " ").title()

    @staticmethod
    def _memory(record: CanonicalMemoryRecord) -> CanonicalReviewMemory:
        return CanonicalReviewMemory(
            id=record.id,
            memory_type=ReviewProposalType(record.memory_type),
            title=record.title,
            structured_fields=record.structured_fields,
            evidence_ids=record.evidence_ids,
            source_ids=record.source_ids,
            confidence=float(record.confidence),
            review_proposal_id=record.review_proposal_id,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _ensure_user(session: Session, user_id: uuid.UUID) -> None:
        if session.get(User, user_id) is None:
            session.add(
                User(
                    id=user_id,
                    clerk_user_id=f"review-demo-{user_id}",
                    email=f"review-demo-{user_id}@example.invalid",
                    display_name="Review Demo User",
                )
            )
            session.flush()

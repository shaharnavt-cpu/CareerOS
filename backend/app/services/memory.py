"""Explicit approval boundary between proposals and Career Memory."""

from __future__ import annotations

import hashlib
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Achievement,
    Education,
    EvidenceItem,
    EvidenceLink,
    Experience,
    Program,
    Project,
    Skill,
    User,
)
from app.schemas.knowledge import (
    DEMO_USER_ID,
    ApprovalState,
    CanonicalMemoryItem,
    CareerMemoryResponse,
    EntityType,
    KnowledgeProposal,
    ProposalOperation,
    ProposalReviewRequest,
    ProposalReviewResponse,
    ReviewDecision,
    SourceType,
)


class CareerMemoryService:
    """Apply reviewed proposals atomically to existing canonical tables."""

    _model_by_type = {
        EntityType.EDUCATION: Education,
        EntityType.PROGRAM: Program,
        EntityType.EXPERIENCE: Experience,
        EntityType.PROJECT: Project,
        EntityType.ACHIEVEMENT: Achievement,
        EntityType.SKILL: Skill,
    }
    _allowed_fields = {
        EntityType.EDUCATION: {
            "institution_name",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "date_precision",
            "gpa",
            "honors",
            "coursework",
            "description",
        },
        EntityType.PROGRAM: {
            "name",
            "organization_name",
            "summary",
            "categories",
            "start_date",
            "end_date",
            "date_precision",
            "is_current",
            "program_url",
        },
        EntityType.EXPERIENCE: {
            "experience_type",
            "organization_name",
            "title",
            "location",
            "start_date",
            "end_date",
            "date_precision",
            "is_current",
            "summary",
            "responsibilities",
            "metrics",
        },
        EntityType.PROJECT: {
            "title",
            "project_type",
            "summary",
            "problem",
            "approach",
            "outcome",
            "repository_url",
            "demo_url",
            "documentation_url",
            "start_date",
            "end_date",
        },
        EntityType.ACHIEVEMENT: {
            "title",
            "category",
            "description",
            "metric_value",
            "achieved_on",
        },
        EntityType.SKILL: {
            "name",
            "normalized_name",
            "category",
            "proficiency_level",
        },
    }
    _required_fields = {
        EntityType.EDUCATION: {"institution_name"},
        EntityType.PROGRAM: {"name"},
        EntityType.EXPERIENCE: {"experience_type", "organization_name", "title"},
        EntityType.PROJECT: {"title"},
        EntityType.ACHIEVEMENT: {"title"},
        EntityType.SKILL: {"name", "normalized_name"},
    }
    _date_fields = {"start_date", "end_date", "achieved_on"}

    def review(
        self,
        session: Session,
        request: ProposalReviewRequest,
        user_id: uuid.UUID = DEMO_USER_ID,
    ) -> ProposalReviewResponse:
        if request.decision is ReviewDecision.REJECT:
            rejected = request.proposal.model_copy(
                update={"approval_state": ApprovalState.REJECTED}
            )
            return ProposalReviewResponse(proposal=rejected)

        if request.proposal.clarification is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Resolve the proposal clarification before approval.",
            )
        if request.proposal.entity_type not in self._model_by_type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"{request.proposal.entity_type.value} persistence is not part of "
                    "the current Career Knowledge Engine schema."
                ),
            )

        with session.begin():
            self._ensure_demo_user(session, user_id)
            entity = self._upsert_entity(session, user_id, request.proposal)
            session.flush()
            self._attach_evidence(
                session,
                user_id,
                request.proposal,
                entity.id,
            )

        canonical = request.proposal.model_copy(
            update={"approval_state": ApprovalState.CANONICAL}
        )
        return ProposalReviewResponse(
            proposal=canonical,
            canonical_entity_id=entity.id,
        )

    def get_memory(self, session: Session, user_id: uuid.UUID) -> CareerMemoryResponse:
        items: list[CanonicalMemoryItem] = []
        for entity_type, model in self._model_by_type.items():
            records = session.scalars(
                select(model).where(
                    model.user_id == user_id, model.deleted_at.is_(None)
                )
            )
            items.extend(
                CanonicalMemoryItem(
                    id=record.id,
                    entity_type=entity_type,
                    value=self._serialize_record(entity_type, record),
                )
                for record in records
            )
        return CareerMemoryResponse(user_id=user_id, items=items)

    def _upsert_entity(
        self,
        session: Session,
        user_id: uuid.UUID,
        proposal: KnowledgeProposal,
    ) -> Education | Program | Experience | Project | Achievement | Skill:
        model = self._model_by_type[proposal.entity_type]
        values = self._validated_values(proposal)
        entity = None

        if proposal.operation is ProposalOperation.UPDATE and proposal.duplicate_of:
            entity = session.scalar(
                select(model).where(
                    model.id == proposal.duplicate_of,
                    model.user_id == user_id,
                    model.deleted_at.is_(None),
                )
            )
            if entity is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=(
                        "The canonical duplicate is unavailable or belongs to "
                        "another user."
                    ),
                )

        if entity is None and proposal.entity_type is EntityType.SKILL:
            entity = session.scalar(
                select(Skill).where(
                    Skill.user_id == user_id,
                    Skill.normalized_name == values["normalized_name"],
                    Skill.deleted_at.is_(None),
                )
            )

        if entity is None:
            entity = self._find_matching_entity(
                session, user_id, proposal.entity_type, values
            )

        if entity is None:
            if proposal.entity_type is EntityType.SKILL:
                values["confidence_score"] = Decimal(str(proposal.confidence))
            entity = model(user_id=user_id, **values)
            session.add(entity)
        else:
            for field, value in values.items():
                setattr(entity, field, value)
            if isinstance(entity, Skill):
                entity.confidence_score = Decimal(str(proposal.confidence))

        return entity

    def _find_matching_entity(
        self,
        session: Session,
        user_id: uuid.UUID,
        entity_type: EntityType,
        values: dict[str, Any],
    ) -> Education | Program | Experience | Project | Achievement | Skill | None:
        model = self._model_by_type[entity_type]
        identity_fields = {
            EntityType.EDUCATION: ("institution_name", "degree", "field_of_study"),
            EntityType.PROGRAM: ("name", "organization_name"),
            EntityType.EXPERIENCE: (
                "organization_name",
                "title",
                "start_date",
                "end_date",
            ),
            EntityType.PROJECT: ("title", "start_date", "end_date"),
            EntityType.ACHIEVEMENT: ("title",),
            EntityType.SKILL: ("normalized_name",),
        }[entity_type]
        conditions = [model.user_id == user_id, model.deleted_at.is_(None)]
        for field in identity_fields:
            value = values.get(field)
            column = getattr(model, field)
            conditions.append(
                column == value if value is not None else column.is_(None)
            )
        return session.scalar(select(model).where(*conditions))

    def _validated_values(self, proposal: KnowledgeProposal) -> dict[str, Any]:
        allowed = self._allowed_fields[proposal.entity_type]
        values = {
            key: value
            for key, value in proposal.proposed_value.items()
            if key in allowed
        }
        missing = [
            field
            for field in self._required_fields[proposal.entity_type]
            if not values.get(field)
        ]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Approved value is missing: " + ", ".join(sorted(missing)),
            )
        for field in self._date_fields.intersection(values):
            value = values[field]
            if isinstance(value, str):
                try:
                    values[field] = date.fromisoformat(value)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"{field} must use ISO date format.",
                    ) from exc
        if proposal.entity_type is EntityType.SKILL:
            values["normalized_name"] = str(values["name"]).casefold().strip()
        return values

    def _attach_evidence(
        self,
        session: Session,
        user_id: uuid.UUID,
        proposal: KnowledgeProposal,
        entity_id: uuid.UUID,
    ) -> None:
        for reference in proposal.evidence:
            content_hash = hashlib.sha256(
                f"{reference.source_id}:{reference.excerpt}".encode()
            ).hexdigest()
            evidence = session.scalar(
                select(EvidenceItem).where(
                    EvidenceItem.user_id == user_id,
                    EvidenceItem.content_hash == content_hash,
                    EvidenceItem.deleted_at.is_(None),
                )
            )
            if evidence is None:
                evidence = EvidenceItem(
                    user_id=user_id,
                    evidence_type=self._evidence_type(reference.source_type),
                    title=reference.title,
                    description=reference.excerpt,
                    content_hash=content_hash,
                    verification_status=reference.verification_status,
                )
                session.add(evidence)
                session.flush()
            existing_link = session.scalar(
                select(EvidenceLink).where(
                    EvidenceLink.user_id == user_id,
                    EvidenceLink.evidence_item_id == evidence.id,
                    EvidenceLink.entity_type == proposal.entity_type.value,
                    EvidenceLink.entity_id == entity_id,
                )
            )
            if existing_link is None:
                session.add(
                    EvidenceLink(
                        user_id=user_id,
                        evidence_item_id=evidence.id,
                        entity_type=proposal.entity_type.value,
                        entity_id=entity_id,
                        relationship_type="SUPPORTS",
                        excerpt=reference.excerpt,
                    )
                )

    @staticmethod
    def _ensure_demo_user(session: Session, user_id: uuid.UUID) -> None:
        if session.get(User, user_id) is None:
            session.add(
                User(
                    id=user_id,
                    clerk_user_id=f"sprint4-demo-{user_id}",
                    email=f"sprint4-demo-{user_id}@example.invalid",
                    display_name="Sprint 4 Demo User",
                )
            )
            session.flush()

    @staticmethod
    def _evidence_type(source_type: SourceType) -> str:
        return {
            SourceType.TRANSCRIPT: "TRANSCRIPT",
            SourceType.GITHUB: "GITHUB_REPOSITORY",
            SourceType.PORTFOLIO: "PORTFOLIO",
            SourceType.CERTIFICATE: "CERTIFICATE",
            SourceType.CONVERSATION: "USER_NOTE",
            SourceType.MANUAL: "USER_NOTE",
        }.get(source_type, "OTHER")

    def _serialize_record(
        self,
        entity_type: EntityType,
        record: Education | Program | Experience | Project | Achievement | Skill,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field in self._allowed_fields[entity_type]:
            value = getattr(record, field, None)
            if value is not None:
                values[field] = value
        return values

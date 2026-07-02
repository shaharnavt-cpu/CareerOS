"""Knowledge reasoning and review API contracts."""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class SourceType(StrEnum):
    """Source adapters supported by the first reasoning pipeline."""

    RESUME = "RESUME"
    CONVERSATION = "CONVERSATION"
    MANUAL = "MANUAL"
    TRANSCRIPT = "TRANSCRIPT"
    LINKEDIN = "LINKEDIN"
    PORTFOLIO = "PORTFOLIO"
    GITHUB = "GITHUB"
    CERTIFICATE = "CERTIFICATE"


class EntityType(StrEnum):
    """Canonical targets accepted by proposal validation."""

    EDUCATION = "EDUCATION"
    PROGRAM = "PROGRAM"
    EXPERIENCE = "EXPERIENCE"
    PROJECT = "PROJECT"
    ACHIEVEMENT = "ACHIEVEMENT"
    SKILL = "SKILL"


class ProposalOperation(StrEnum):
    """Change a proposal would make after approval."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    LINK = "LINK"


class ApprovalState(StrEnum):
    """Conceptual lifecycle shared with the onboarding flow."""

    DISCOVERED = "DISCOVERED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANONICAL = "CANONICAL"


class ReviewDecision(StrEnum):
    """Explicit decisions a user may submit."""

    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ClarificationReason(StrEnum):
    """The only reasons that may justify a clarification question."""

    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class EvidenceReference(BaseModel):
    """Addressable evidence retained with a proposal."""

    source_id: str = Field(min_length=1, max_length=128)
    source_type: SourceType
    title: str = Field(min_length=1, max_length=256)
    excerpt: str = Field(min_length=1, max_length=4000)
    location: str | None = Field(default=None, max_length=256)
    verification_status: str = "UNVERIFIED"


class Clarification(BaseModel):
    """A specific question and its deterministic justification."""

    question: str = Field(min_length=10, max_length=1000)
    reason: ClarificationReason
    detail: str = Field(min_length=3, max_length=1000)


class ProposalRelationship(BaseModel):
    """A validated relationship inferred between two proposals."""

    target_proposal_id: str = Field(min_length=1, max_length=128)
    relationship_type: str = Field(min_length=1, max_length=64)


class KnowledgeProposal(BaseModel):
    """Explainable, reviewable candidate change to Career Memory."""

    id: str = Field(min_length=1, max_length=128)
    entity_type: EntityType
    proposed_value: dict[str, Any]
    operation: ProposalOperation = ProposalOperation.CREATE
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceReference] = Field(min_length=1)
    reasoning_summary: str = Field(min_length=3, max_length=2000)
    clarification: Clarification | None = None
    approval_state: ApprovalState = ApprovalState.NEEDS_REVIEW
    duplicate_of: uuid.UUID | None = None
    relationships: list[ProposalRelationship] = Field(default_factory=list)

    @model_validator(mode="after")
    def clarification_matches_confidence(self) -> KnowledgeProposal:
        if (
            self.clarification
            and self.clarification.reason is ClarificationReason.LOW_CONFIDENCE
            and self.confidence >= 0.7
        ):
            raise ValueError("low-confidence clarification requires confidence < 0.7")
        return self


class ExistingMemoryItem(BaseModel):
    """Minimal canonical record used for deterministic duplicate detection."""

    id: uuid.UUID
    entity_type: EntityType
    value: dict[str, Any]


class ReasoningRequest(BaseModel):
    """Raw single-source input to the reasoning pipeline."""

    raw_source: str = Field(min_length=1, max_length=100_000)
    source_type: SourceType = SourceType.RESUME
    source_name: str = Field(default="Career source", min_length=1, max_length=256)
    existing_memory: list[ExistingMemoryItem] = Field(default_factory=list)


class ProcessingSummary(BaseModel):
    """Safe, user-facing execution metadata."""

    normalized_lines: int
    extracted_candidates: int
    proposals: int
    provider: str


class ReasoningResponse(BaseModel):
    """Result of a complete reasoning pass."""

    source_id: str
    proposals: list[KnowledgeProposal]
    summary: ProcessingSummary


class ProposalReviewRequest(BaseModel):
    """User decision over the exact proposal being reviewed."""

    proposal: KnowledgeProposal
    decision: ReviewDecision


class ProposalReviewResponse(BaseModel):
    """Decision result, including the canonical record when created."""

    proposal: KnowledgeProposal
    canonical_entity_id: uuid.UUID | None = None


class CanonicalMemoryItem(BaseModel):
    """A canonical entity returned for review or dashboard consumption."""

    id: uuid.UUID
    entity_type: EntityType
    value: dict[str, Any]


class CareerMemoryResponse(BaseModel):
    """Current canonical knowledge for one user."""

    user_id: uuid.UUID
    items: list[CanonicalMemoryItem]


class NormalizedLine(BaseModel):
    """A normalized source line with stable provenance."""

    number: int
    text: str


class NormalizedSource(BaseModel):
    """Common representation emitted by every source adapter."""

    id: str
    source_type: SourceType
    name: str
    content_hash: str
    lines: list[NormalizedLine]


class ExtractedCandidate(BaseModel):
    """Deterministically identified entity before semantic reasoning."""

    id: str
    hinted_type: EntityType | None
    raw_value: str
    location: str
    evidence_excerpt: str
    extraction_confidence: float = Field(ge=0, le=1)


class SemanticAssessment(BaseModel):
    """Provider output consumed only after deterministic validation."""

    candidate_id: str
    entity_type: EntityType
    proposed_value: dict[str, Any]
    semantic_confidence: float = Field(ge=0, le=1)
    reasoning_summary: str = Field(min_length=3, max_length=2000)
    missing_fields: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)
    clarification_question: str | None = Field(default=None, max_length=1000)
    relationships: list[ProposalRelationship] = Field(default_factory=list)

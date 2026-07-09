"""API contracts for Application Intelligence."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.knowledge import CanonicalReviewMemory, ReviewProposalType


class ApplicationOpportunityStatus(StrEnum):
    ANALYZED = "ANALYZED"
    NEEDS_MEMORY = "NEEDS_MEMORY"
    SAVED = "SAVED"
    ARCHIVED = "ARCHIVED"


class ApplicationQuestionStatus(StrEnum):
    OPEN = "OPEN"
    DRAFTED = "DRAFTED"
    ANSWERED = "ANSWERED"
    ARCHIVED = "ARCHIVED"


class ApplicationDraftStatus(StrEnum):
    DRAFT = "DRAFT"
    EDITED = "EDITED"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class ApplicationQuestionType(StrEnum):
    WHY_THIS_ROLE = "WHY_THIS_ROLE"
    WHY_THIS_COMPANY = "WHY_THIS_COMPANY"
    TELL_ME_ABOUT_YOURSELF = "TELL_ME_ABOUT_YOURSELF"
    EXPERIENCE_EXAMPLE = "EXPERIENCE_EXAMPLE"
    LEADERSHIP = "LEADERSHIP"
    TECHNICAL_SKILLS = "TECHNICAL_SKILLS"
    PROJECT_EXPLANATION = "PROJECT_EXPLANATION"
    STRENGTHS = "STRENGTHS"
    GENERAL_COVER_LETTER = "GENERAL_COVER_LETTER"
    UNKNOWN = "UNKNOWN"


class ApplicationDraftType(StrEnum):
    GENERAL_RESPONSE = "GENERAL_RESPONSE"
    COVER_LETTER_SNIPPET = "COVER_LETTER_SNIPPET"
    QUESTION_ANSWER = "QUESTION_ANSWER"


class ApplicationDraftLength(StrEnum):
    SHORT = "SHORT"
    MEDIUM = "MEDIUM"
    DETAILED = "DETAILED"
    # Backward-compatible alias for Sprint 9 clients.
    LONG = "LONG"


class ApplicationOpportunityCreateRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=100_000)
    title: str | None = Field(default=None, max_length=256)
    organization: str | None = Field(default=None, max_length=256)

    @field_validator("raw_text")
    @classmethod
    def raw_text_has_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "Paste a job description, internship posting, or application question."
            )
        return value


class ApplicationQuestionCreateRequest(BaseModel):
    opportunity_id: uuid.UUID
    question_text: str = Field(min_length=1, max_length=5000)


class ApplicationDraftRequest(BaseModel):
    question_id: uuid.UUID | None = None
    draft_type: ApplicationDraftType = ApplicationDraftType.GENERAL_RESPONSE
    length: ApplicationDraftLength = ApplicationDraftLength.MEDIUM


class ApplicationDraftUpdateRequest(BaseModel):
    draft_text: str | None = Field(default=None, min_length=1, max_length=20_000)
    status: ApplicationDraftStatus | None = None


class ApplicationQuestionView(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    question_text: str
    question_type: ApplicationQuestionType
    detected_intent: str
    required_themes: list[str]
    status: ApplicationQuestionStatus
    created_at: datetime
    updated_at: datetime


class ApplicationMemoryMatchView(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    question_id: uuid.UUID | None
    canonical_memory_id: uuid.UUID
    match_score: float
    match_reason: str
    evidence_ids: list[str]
    themes_matched: list[str]
    memory: CanonicalReviewMemory


class ApplicationDraftView(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    question_id: uuid.UUID | None
    draft_type: ApplicationDraftType
    prompt: str
    draft_text: str
    evidence_ids: list[str]
    status: ApplicationDraftStatus
    draft_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ApplicationStoryContext(BaseModel):
    id: uuid.UUID
    title: str
    summary: str
    evidence_ids: list[str]
    confidence: float


class ApplicationOpportunityView(BaseModel):
    id: uuid.UUID
    title: str
    organization: str | None
    raw_text: str
    detected_role_type: str | None
    detected_skills: list[str]
    detected_keywords: list[str]
    detected_responsibilities: list[str]
    detected_questions: list[str]
    status: ApplicationOpportunityStatus
    gaps: list[str]
    questions: list[ApplicationQuestionView]
    matches: list[ApplicationMemoryMatchView]
    drafts: list[ApplicationDraftView]
    approved_stories: list[ApplicationStoryContext] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ApplicationOpportunityListItem(BaseModel):
    id: uuid.UUID
    title: str
    organization: str | None
    detected_role_type: str | None
    detected_skills: list[str]
    status: ApplicationOpportunityStatus
    match_count: int
    draft_count: int
    created_at: datetime
    updated_at: datetime


class ApplicationMatchResponse(BaseModel):
    opportunity: ApplicationOpportunityView
    matches: list[ApplicationMemoryMatchView]
    gaps: list[str]


class ApplicationDraftResponse(BaseModel):
    draft: ApplicationDraftView
    matches_used: list[ApplicationMemoryMatchView]
    evidence_used: list[str]


MEMORY_TYPE_WEIGHT: dict[ReviewProposalType, float] = {
    ReviewProposalType.PROJECT: 0.24,
    ReviewProposalType.EXPERIENCE: 0.22,
    ReviewProposalType.SKILL_SET: 0.22,
    ReviewProposalType.EDUCATION: 0.14,
    ReviewProposalType.PROGRAM: 0.12,
    ReviewProposalType.ACHIEVEMENT: 0.1,
    ReviewProposalType.ORGANIZATION: 0.04,
    ReviewProposalType.CONTACT: 0.01,
    ReviewProposalType.NEEDS_CLASSIFICATION: 0.02,
}

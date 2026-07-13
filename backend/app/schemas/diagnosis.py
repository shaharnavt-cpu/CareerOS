"""API contracts for Career Diagnosis Engine v0."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.schemas.knowledge import ReviewProposalType


class DiagnosisFocus(StrEnum):
    ANALYTICS = "ANALYTICS"
    AI_AUTOMATION = "AI_AUTOMATION"
    RESEARCH = "RESEARCH"
    QUANT_FINANCE = "QUANT_FINANCE"
    CAMPUS_JOB = "CAMPUS_JOB"
    SCHOLARSHIP_LEADERSHIP = "SCHOLARSHIP_LEADERSHIP"
    GENERAL = "GENERAL"


class DiagnosisSessionStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    NEEDS_MEMORY = "NEEDS_MEMORY"
    FAILED = "FAILED"


class FeedbackEventType(StrEnum):
    ARTIFACT_SUCCESS = "ARTIFACT_SUCCESS"
    APPLICATION_OUTCOME = "APPLICATION_OUTCOME"
    DRAFT_FEEDBACK = "DRAFT_FEEDBACK"
    POSITIONING_RULE = "POSITIONING_RULE"
    MEMORY_USAGE_RULE = "MEMORY_USAGE_RULE"
    GENERAL_LEARNING = "GENERAL_LEARNING"
    UNKNOWN = "UNKNOWN"


class FeedbackEventStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    ARCHIVED = "ARCHIVED"


class DiagnosisSessionCreateRequest(BaseModel):
    target_role: str | None = Field(default=None, max_length=500)
    target_context: str | None = Field(default=None, max_length=5000)
    frustration_context: str | None = Field(default=None, max_length=5000)
    selected_focus: DiagnosisFocus | None = None

    @field_validator("target_role", "target_context", "frustration_context")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class EvidenceMapItem(BaseModel):
    memory_id: uuid.UUID
    memory_title: str
    memory_type: ReviewProposalType
    relevant_themes: list[str]
    claim_supported: str
    evidence_ids: list[str]
    strength: str
    confidence: float = Field(ge=0, le=1)
    reason_code: str


class ProofSprint(BaseModel):
    objective: str
    actions: list[str]
    expected_artifact: str
    why_it_matters: str
    evidence_to_strengthen: list[str]
    application_use: str


class DiagnosisResultView(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    career_identity: str
    identity_rationale: str
    evidence_map: list[EvidenceMapItem]
    recognition_gap: str
    missing_proof: list[str]
    proof_sprint: ProofSprint
    do_not_waste_time: str
    exact_next_actions: list[str]
    exact_messages: dict[str, str]
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str]
    feedback_event_ids: list[str]
    diagnosis_version: str
    created_at: datetime
    updated_at: datetime


class DiagnosisSessionView(BaseModel):
    id: uuid.UUID
    target_role: str | None
    target_context: str | None
    frustration_context: str | None
    selected_focus: DiagnosisFocus | None
    status: DiagnosisSessionStatus
    approved_memory_only: bool = True
    result: DiagnosisResultView
    created_at: datetime
    updated_at: datetime


class FeedbackEventCreateRequest(BaseModel):
    raw_note: str = Field(min_length=1, max_length=10_000)
    related_memory_ids: list[uuid.UUID] = Field(default_factory=list)
    related_opportunity_id: uuid.UUID | None = None
    related_draft_id: uuid.UUID | None = None
    status: FeedbackEventStatus = FeedbackEventStatus.PROPOSED

    @field_validator("raw_note")
    @classmethod
    def note_has_content(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Tell CareerOS what happened or how to use your proof.")
        return stripped


class FeedbackEventUpdateRequest(BaseModel):
    raw_note: str | None = Field(default=None, min_length=1, max_length=10_000)
    event_type: FeedbackEventType | None = None
    structured_summary: str | None = Field(default=None, max_length=10_000)
    related_memory_ids: list[uuid.UUID] | None = None
    related_opportunity_id: uuid.UUID | None = None
    related_draft_id: uuid.UUID | None = None
    suggested_future_use: str | None = Field(default=None, max_length=10_000)
    status: FeedbackEventStatus | None = None

    @field_validator("raw_note", "structured_summary", "suggested_future_use")
    @classmethod
    def changed_text_has_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("Updated feedback text cannot be blank.")
        return stripped


class FeedbackEventView(BaseModel):
    id: uuid.UUID
    raw_note: str
    event_type: FeedbackEventType
    structured_summary: str
    related_memory_ids: list[str]
    related_opportunity_id: uuid.UUID | None
    related_draft_id: uuid.UUID | None
    suggested_future_use: str
    status: FeedbackEventStatus
    created_at: datetime
    updated_at: datetime

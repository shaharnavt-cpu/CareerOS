"""Proof Artifact Builder API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ProofArtifactType(StrEnum):
    CASE_STUDY = "CASE_STUDY"
    GITHUB_README = "GITHUB_README"
    PORTFOLIO_PAGE = "PORTFOLIO_PAGE"
    APPLICATION_UPLOAD = "APPLICATION_UPLOAD"
    OUTREACH_SUMMARY = "OUTREACH_SUMMARY"
    INTERVIEW_STORY = "INTERVIEW_STORY"
    RESUME_BULLETS = "RESUME_BULLETS"


class ProofArtifactStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEWED = "REVIEWED"
    READY = "READY"
    ARCHIVED = "ARCHIVED"


class ProofTargetAudience(StrEnum):
    APPLICATION_UPLOAD = "APPLICATION_UPLOAD"
    PORTFOLIO = "PORTFOLIO"
    GITHUB = "GITHUB"
    OUTREACH = "OUTREACH"
    INTERVIEW_PREP = "INTERVIEW_PREP"
    GENERAL = "GENERAL"


class ProofReadinessLabel(StrEnum):
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    DRAFTABLE = "DRAFTABLE"
    STRONG_DRAFT = "STRONG_DRAFT"
    READY_TO_SHARE = "READY_TO_SHARE"


class ProofArtifactCreateRequest(BaseModel):
    source_memory_id: uuid.UUID
    target_role: str = Field(min_length=1, max_length=500)
    target_audience: ProofTargetAudience = ProofTargetAudience.GENERAL
    artifact_type: ProofArtifactType = ProofArtifactType.CASE_STUDY
    source_diagnosis_result_id: uuid.UUID | None = None

    @field_validator("target_role")
    @classmethod
    def target_role_has_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Target role or program cannot be blank.")
        return value


class ProofArtifactRegenerateRequest(BaseModel):
    target_role: str | None = Field(default=None, max_length=500)
    target_audience: ProofTargetAudience | None = None
    artifact_type: ProofArtifactType | None = None

    @field_validator("target_role")
    @classmethod
    def changed_target_has_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Target role or program cannot be blank.")
        return value


class ProofArtifactUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=1000)
    target_role: str | None = Field(default=None, max_length=500)
    target_audience: ProofTargetAudience | None = None
    status: ProofArtifactStatus | None = None

    @field_validator("title", "target_role")
    @classmethod
    def changed_metadata_has_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Updated proof artifact text cannot be blank.")
        return value


class ProofArtifactVersionUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=1000)
    claim: str | None = Field(default=None, max_length=5000)
    content: str | None = Field(default=None, max_length=50_000)
    structured_sections: dict[str, Any] | None = None
    supporting_variants: dict[str, Any] | None = None

    @field_validator("title", "claim", "content")
    @classmethod
    def edited_text_has_content(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Edited proof artifact text cannot be blank.")
        return value

    @model_validator(mode="after")
    def includes_a_change(self) -> ProofArtifactVersionUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one proof artifact version change.")
        return self


class ProofEvidenceReference(BaseModel):
    evidence_id: str
    source_label: str
    excerpt: str | None = None


class ProofOutcomeSignal(BaseModel):
    feedback_event_id: uuid.UUID
    summary: str
    guidance: str
    caveat: str


class ProofArtifactVersionView(BaseModel):
    id: uuid.UUID
    artifact_id: uuid.UUID
    version_number: int
    title: str
    claim: str
    content: str
    structured_sections: dict[str, Any]
    evidence_ids: list[str]
    evidence_references: list[ProofEvidenceReference]
    outcome_signal_ids: list[str]
    outcome_signals: list[ProofOutcomeSignal]
    warnings: list[str]
    readiness_score: float = Field(ge=0, le=1)
    readiness_label: ProofReadinessLabel
    supporting_variants: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ProofArtifactView(BaseModel):
    id: uuid.UUID
    title: str
    artifact_type: ProofArtifactType
    target_role: str
    target_audience: ProofTargetAudience
    source_memory_id: uuid.UUID
    source_memory_title: str
    source_diagnosis_result_id: uuid.UUID | None
    status: ProofArtifactStatus
    latest_version: ProofArtifactVersionView
    version_count: int
    created_at: datetime
    updated_at: datetime


class ProofMemoryOption(BaseModel):
    id: uuid.UUID
    title: str
    memory_type: str
    evidence_count: int
    evidence_ids: list[str]
    source_labels: list[str]
    confidence: float = Field(ge=0, le=1)

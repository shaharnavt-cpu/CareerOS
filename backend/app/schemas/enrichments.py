"""Project evidence enrichment and memory identity API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class MemoryResolutionKind(StrEnum):
    CREATE_NEW = "CREATE_NEW"
    ENRICH_EXISTING = "ENRICH_EXISTING"
    DUPLICATE_PROPOSAL = "DUPLICATE_PROPOSAL"
    POSSIBLE_MERGE = "POSSIBLE_MERGE"
    QUIET_SUPPORTING_EVIDENCE = "QUIET_SUPPORTING_EVIDENCE"
    NEEDS_USER_CONFIRMATION = "NEEDS_USER_CONFIRMATION"


class RecommendedReviewAction(StrEnum):
    CREATE_MEMORY = "CREATE_MEMORY"
    CREATE_ENRICHMENT = "CREATE_ENRICHMENT"
    USE_EXISTING_PROPOSAL = "USE_EXISTING_PROPOSAL"
    REVIEW_POSSIBLE_MERGE = "REVIEW_POSSIBLE_MERGE"
    KEEP_AS_SUPPORTING_EVIDENCE = "KEEP_AS_SUPPORTING_EVIDENCE"
    ASK_USER = "ASK_USER"


class MemoryIdentityResolution(BaseModel):
    resolution: MemoryResolutionKind
    confidence: float = Field(ge=0, le=1)
    matched_memory_id: uuid.UUID | None = None
    matched_memory_title: str | None = None
    matched_proposal_id: str | None = None
    reasons: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    recommended_review_action: RecommendedReviewAction


class MemoryIdentityCandidatesResponse(BaseModel):
    query_title: str
    candidates: list[MemoryIdentityResolution]


class EnrichmentStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class EnrichmentType(StrEnum):
    PROJECT_CONTEXT = "PROJECT_CONTEXT"
    PROJECT_METHOD = "PROJECT_METHOD"
    PROJECT_RESULT = "PROJECT_RESULT"
    PROJECT_LIMITATION = "PROJECT_LIMITATION"
    PROJECT_OUTPUT = "PROJECT_OUTPUT"
    PROJECT_ROLE_RELEVANCE = "PROJECT_ROLE_RELEVANCE"
    PROJECT_FULL_ENRICHMENT = "PROJECT_FULL_ENRICHMENT"
    MEMORY_MERGE_SUGGESTION = "MEMORY_MERGE_SUGGESTION"


class CareerMemoryTarget(BaseModel):
    id: uuid.UUID
    title: str
    memory_type: str


class EnrichmentCreateRequest(BaseModel):
    enrichment_text: str | None = Field(default=None, max_length=100_000)
    source_id: uuid.UUID | None = None
    source_label: str | None = Field(default=None, max_length=500)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    enrichment_type: EnrichmentType = EnrichmentType.PROJECT_FULL_ENRICHMENT

    @field_validator("enrichment_text")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def has_input(self) -> EnrichmentCreateRequest:
        if (
            not self.enrichment_text
            and self.source_id is None
            and not self.evidence_ids
        ):
            raise ValueError("Paste project detail or select saved source evidence.")
        return self


class EnrichmentUpdateRequest(BaseModel):
    status: EnrichmentStatus | None = None
    structured_enrichment: dict[str, Any] | None = None
    reasoning: str | None = Field(default=None, max_length=5000)

    @field_validator("reasoning")
    @classmethod
    def normalize_reasoning(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Reasoning cannot be blank.")
        return value

    @model_validator(mode="after")
    def has_change(self) -> EnrichmentUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one enrichment change.")
        return self


class EnrichmentView(BaseModel):
    id: uuid.UUID
    target_memory: CareerMemoryTarget
    status: EnrichmentStatus
    enrichment_type: EnrichmentType
    structured_enrichment: dict[str, Any]
    evidence_ids: list[str]
    source_id: uuid.UUID | None
    source_label: str | None
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    identity_resolution: MemoryIdentityResolution
    warnings: list[str]
    proof_artifact_readiness_impact: str
    memory_quality_impact: list[str]
    missing_or_weak_sections: list[str]
    project_boundary: str
    created_at: datetime
    updated_at: datetime

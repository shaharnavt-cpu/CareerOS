"""Contracts for source ingestion, listening, fusion, and proposal handoff."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.knowledge import ExistingMemoryItem, KnowledgeProposal, SourceType


class EvidenceCategory(StrEnum):
    """Source-level observations a listener may identify without reasoning."""

    EDUCATION = "EDUCATION"
    PROGRAM = "PROGRAM"
    EXPERIENCE = "EXPERIENCE"
    PROJECT = "PROJECT"
    SKILL = "SKILL"
    ACHIEVEMENT = "ACHIEVEMENT"
    ORGANIZATION = "ORGANIZATION"
    DATE = "DATE"
    ROLE = "ROLE"
    CONTACT = "CONTACT"
    LINK = "LINK"
    UNKNOWN = "UNKNOWN"


class ListeningStatus(StrEnum):
    """Resumable processing state for an ingested source."""

    RECEIVED = "RECEIVED"
    LISTENING = "LISTENING"
    READY = "READY"
    FAILED = "FAILED"


class SourceSubmission(BaseModel):
    """User-provided text source accepted by the listening API."""

    source_type: SourceType
    label: str = Field(min_length=1, max_length=256)
    raw_text: str = Field(min_length=1, max_length=100_000)
    original_filename: str | None = Field(default=None, max_length=512)
    media_type: str | None = Field(default="text/plain", max_length=128)
    source_url: str | None = Field(default=None, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NormalizedListeningSource(BaseModel):
    """Source-agnostic representation produced by every source adapter."""

    id: uuid.UUID
    user_id: uuid.UUID
    source_type: SourceType
    label: str
    raw_text: str
    content_hash: str
    metadata: dict[str, Any]
    provenance: dict[str, Any]
    received_at: datetime
    adapter_version: str


class EvidenceObject(BaseModel):
    """A standardized, provenance-preserving observation from one source."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_id: uuid.UUID
    source_type: SourceType
    raw_excerpt: str = Field(min_length=1, max_length=4000)
    normalized_excerpt: str | None = Field(default=None, max_length=4000)
    category: EvidenceCategory
    confidence: float = Field(ge=0, le=1)
    location: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ConflictingClaim(BaseModel):
    """Two or more retained observations that disagree on a comparable claim."""

    evidence_ids: list[uuid.UUID] = Field(min_length=2)
    excerpts: list[str] = Field(min_length=2)
    reason: str


class EvidenceCluster(BaseModel):
    """Related evidence with support and disagreement kept side by side."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    category: EvidenceCategory
    label: str
    normalized_key: str
    evidence: list[EvidenceObject] = Field(min_length=1)
    contributing_source_ids: list[uuid.UUID] = Field(default_factory=list)
    conflicting_claims: list[ConflictingClaim] = Field(default_factory=list)
    corroborated: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicting_claims)


class ListeningSourceSummary(BaseModel):
    """Safe source metadata returned without raw source content."""

    id: uuid.UUID
    source_type: SourceType
    label: str
    original_filename: str | None = None
    media_type: str | None = None
    content_hash: str
    status: ListeningStatus
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime
    created_at: datetime
    evidence_count: int = 0


class SourceIngestionResponse(BaseModel):
    """Result of normalization and deterministic listening."""

    source: ListeningSourceSummary
    evidence: list[EvidenceObject]
    clusters: list[EvidenceCluster]


class ListeningProposalRequest(BaseModel):
    """Select staged sources whose fused evidence should reach Sprint 4."""

    source_ids: list[uuid.UUID] = Field(default_factory=list)
    existing_memory: list[ExistingMemoryItem] = Field(default_factory=list)


class ListeningProposalResponse(BaseModel):
    """Knowledge proposals returned by Sprint 4 with listening provenance."""

    proposals: list[KnowledgeProposal]
    clusters_considered: int
    evidence_considered: int
    provider: str


class ListeningJobStage(StrEnum):
    """Public progress states for a background listening job."""

    QUEUED = "QUEUED"
    READING = "READING"
    EXTRACTING_EVIDENCE = "EXTRACTING_EVIDENCE"
    COMPARING_SOURCES = "COMPARING_SOURCES"
    PREPARING_PROPOSALS = "PREPARING_PROPOSALS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ListeningJobResponse(BaseModel):
    """Safe, pollable state for one uploaded source."""

    id: uuid.UUID
    filename: str
    media_type: str | None = None
    stage: ListeningJobStage
    progress: int = Field(ge=0, le=100)
    message: str
    attempt: int = Field(ge=1)
    source_id: uuid.UUID | None = None
    source_type: SourceType | None = None
    document_type: str | None = None
    detection_confidence: float | None = Field(default=None, ge=0, le=1)
    evidence_count: int = Field(default=0, ge=0)
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class ListeningUploadResponse(BaseModel):
    """Jobs created by one multi-file attachment request."""

    jobs: list[ListeningJobResponse]

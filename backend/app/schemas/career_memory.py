"""Structured output from the deterministic Career Memory compiler."""

from __future__ import annotations

import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class CompiledEvidenceKind(StrEnum):
    """Trust tier for one compiler input."""

    CANONICAL_MEMORY = "CANONICAL_MEMORY"
    CANONICAL_EVIDENCE = "CANONICAL_EVIDENCE"
    APPROVED_ENRICHMENT = "APPROVED_ENRICHMENT"


class CompiledEvidence(BaseModel):
    """User-owned source material used to support the compiled profile."""

    evidence_id: str
    kind: CompiledEvidenceKind
    source_label: str
    excerpt: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class CompiledOutcomeSignal(BaseModel):
    """Approved strategy feedback kept explicitly separate from factual proof."""

    feedback_event_id: uuid.UUID
    summary: str
    guidance: str
    caveat: str


class CompiledCareerMemoryProfile(BaseModel):
    """Evidence-backed interpretation of one approved canonical memory."""

    memory_id: uuid.UUID
    canonical_title: str
    memory_type: str
    project_kind: str
    project_boundary: str
    aliases: list[str] = Field(default_factory=list)
    source_confidence: float = Field(ge=0, le=1)
    research_question_or_problem: str | None = None
    data_or_inputs: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    findings_or_results: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    collaborators_or_context: list[str] = Field(default_factory=list)
    role_relevance: str
    role_relevance_by_target: dict[str, str] = Field(default_factory=dict)
    skills_demonstrated: list[str] = Field(default_factory=list)
    proof_claims: list[str] = Field(default_factory=list)
    resume_bullet_claims: list[str] = Field(default_factory=list)
    cover_letter_angles: list[str] = Field(default_factory=list)
    proof_artifact_angles: list[str] = Field(default_factory=list)
    warnings_not_to_claim: list[str] = Field(default_factory=list)
    evidence_used: list[CompiledEvidence] = Field(default_factory=list)
    evidence_ids_used: list[str] = Field(default_factory=list)
    enrichment_ids_used: list[uuid.UUID] = Field(default_factory=list)
    outcome_signal_ids_used: list[uuid.UUID] = Field(default_factory=list)
    outcome_signals: list[CompiledOutcomeSignal] = Field(default_factory=list)
    missing_or_weak_sections: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    target_role_interpretation: str | None = None
    compiler_version: str = "career-memory-compiler-v1"

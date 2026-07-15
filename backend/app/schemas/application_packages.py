"""Validated contracts for evidence-backed application packages."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class ApplicationPackageStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    ARCHIVED = "ARCHIVED"


class ApplicationPackageGenerationReason(StrEnum):
    GENERATED = "GENERATED"
    REGENERATED = "REGENERATED"
    USER_EDIT = "USER_EDIT"


class EvidenceSourceType(StrEnum):
    APPROVED_MEMORY = "APPROVED_MEMORY"
    APPROVED_ENRICHMENT = "APPROVED_ENRICHMENT"
    STRATEGY_SIGNAL = "STRATEGY_SIGNAL"
    TARGET_CONTEXT = "TARGET_CONTEXT"


class EvidenceSupportType(StrEnum):
    DIRECT = "DIRECT"
    INFERRED_FRAMING = "INFERRED_FRAMING"
    STRATEGY_ONLY = "STRATEGY_ONLY"
    RELEVANCE_ONLY = "RELEVANCE_ONLY"


class ApplicationWarningSeverity(StrEnum):
    INFO = "INFO"
    CAUTION = "CAUTION"
    BLOCKING = "BLOCKING"


class ApplicationPackageCreateRequest(BaseModel):
    opportunity_id: uuid.UUID | None = None
    display_name: str | None = Field(default=None, max_length=500)
    role_title: str = Field(min_length=1, max_length=500)
    company: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=500)
    job_type: str | None = Field(default=None, max_length=200)
    target_description: str = Field(default="", max_length=100_000)
    required_skills: list[str] = Field(default_factory=list, max_length=100)
    preferred_skills: list[str] = Field(default_factory=list, max_length=100)
    responsibilities: list[str] = Field(default_factory=list, max_length=100)
    selected_memory_ids: list[uuid.UUID] = Field(default_factory=list, max_length=50)

    @field_validator(
        "display_name",
        "role_title",
        "company",
        "location",
        "job_type",
        mode="before",
    )
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator(
        "required_skills", "preferred_skills", "responsibilities", mode="after"
    )
    @classmethod
    def clean_list(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            rendered = " ".join(value.split()).strip()
            if not rendered or rendered.casefold() in seen:
                continue
            seen.add(rendered.casefold())
            cleaned.append(rendered)
        return cleaned

    @field_validator("selected_memory_ids", mode="after")
    @classmethod
    def memory_ids_are_unique(cls, values: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(values)) != len(values):
            raise ValueError("Selected Career Memory IDs must be unique.")
        return values


class ApplicationPackageUpdateRequest(BaseModel):
    opportunity_id: uuid.UUID | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=500)
    role_title: str | None = Field(default=None, min_length=1, max_length=500)
    company: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=500)
    job_type: str | None = Field(default=None, max_length=200)
    target_description: str | None = Field(default=None, max_length=100_000)
    required_skills: list[str] | None = Field(default=None, max_length=100)
    preferred_skills: list[str] | None = Field(default=None, max_length=100)
    responsibilities: list[str] | None = Field(default=None, max_length=100)
    selected_memory_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)
    status: ApplicationPackageStatus | None = None

    @field_validator(
        "display_name", "role_title", "company", "location", "job_type", mode="before"
    )
    @classmethod
    def trim_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("selected_memory_ids", mode="after")
    @classmethod
    def memory_ids_are_unique(
        cls, values: list[uuid.UUID] | None
    ) -> list[uuid.UUID] | None:
        if values is not None and len(set(values)) != len(values):
            raise ValueError("Selected Career Memory IDs must be unique.")
        return values

    @model_validator(mode="after")
    def includes_a_change(self) -> ApplicationPackageUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one application package change.")
        non_nullable_fields = {
            "display_name",
            "role_title",
            "target_description",
            "required_skills",
            "preferred_skills",
            "responsibilities",
            "selected_memory_ids",
            "status",
        }
        null_fields = sorted(
            field
            for field in self.model_fields_set & non_nullable_fields
            if getattr(self, field) is None
        )
        if null_fields:
            raise ValueError(
                "These application package fields cannot be null: "
                + ", ".join(null_fields)
                + "."
            )
        return self


class ApplicationPackageGenerateRequest(BaseModel):
    selected_memory_ids: list[uuid.UUID] | None = Field(default=None, max_length=50)

    @field_validator("selected_memory_ids", mode="after")
    @classmethod
    def memory_ids_are_unique(
        cls, values: list[uuid.UUID] | None
    ) -> list[uuid.UUID] | None:
        if values is not None and len(set(values)) != len(values):
            raise ValueError("Selected Career Memory IDs must be unique.")
        return values


class ApplicationEvidenceTrace(BaseModel):
    trace_id: str
    source_type: EvidenceSourceType
    support_type: EvidenceSupportType
    source_label: str
    detail: str
    memory_id: uuid.UUID | None = None
    memory_title: str | None = None
    evidence_id: str | None = None
    enrichment_id: uuid.UUID | None = None
    outcome_signal_id: uuid.UUID | None = None
    caveat: str | None = None


class ApplicationPackageWarning(BaseModel):
    code: str
    message: str
    severity: ApplicationWarningSeverity = ApplicationWarningSeverity.CAUTION
    requirement: str | None = None
    memory_ids: list[uuid.UUID] = Field(default_factory=list)


class ResumeBullet(BaseModel):
    bullet_text: str
    evidence_trace: list[ApplicationEvidenceTrace]
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    why_this_bullet: str


class ResumeBulletGroup(BaseModel):
    section_suggestion: str
    memory_id: uuid.UUID
    memory_title: str
    target_reason: str
    bullets: list[ResumeBullet]


class CoverLetterParagraphTrace(BaseModel):
    paragraph_label: str
    paragraph_text: str
    evidence_trace: list[ApplicationEvidenceTrace]


class CoverLetterDraft(BaseModel):
    subject_or_heading: str
    greeting: str
    opening_paragraph: str
    body_paragraphs: list[str]
    closing_paragraph: str
    full_text: str
    evidence_trace_by_paragraph: list[CoverLetterParagraphTrace]
    warnings: list[str] = Field(default_factory=list)
    strategy_notes: list[str] = Field(default_factory=list)


class PositioningSummary(BaseModel):
    primary_positioning: str
    strongest_evidence: str
    secondary_evidence: list[str] = Field(default_factory=list)
    risks_and_gaps: list[str] = Field(default_factory=list)
    recommended_emphasis: list[str] = Field(default_factory=list)
    do_not_claim: list[str] = Field(default_factory=list)


class ApplicationSnippet(BaseModel):
    question: str
    text: str
    evidence_trace: list[ApplicationEvidenceTrace]
    warnings: list[str] = Field(default_factory=list)


class SuggestedProofArtifact(BaseModel):
    memory_id: uuid.UUID
    memory_title: str
    artifact_id: uuid.UUID | None = None
    artifact_title: str
    action: str
    reason: str


class ApplicationPackageOutputs(BaseModel):
    positioning_summary: PositioningSummary
    resume_bullets: list[ResumeBulletGroup]
    cover_letter: CoverLetterDraft
    application_snippets: list[ApplicationSnippet]
    suggested_proof_artifacts: list[SuggestedProofArtifact]
    reviewer_questions: list[str]
    unsupported_claims: list[str]


class ApplicationPackageOutputsUpdateRequest(BaseModel):
    positioning_summary: PositioningSummary | None = None
    resume_bullets: list[ResumeBulletGroup] | None = None
    cover_letter: CoverLetterDraft | None = None
    application_snippets: list[ApplicationSnippet] | None = None
    suggested_proof_artifacts: list[SuggestedProofArtifact] | None = None
    reviewer_questions: list[str] | None = None
    edit_summary: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def includes_output_change(self) -> ApplicationPackageOutputsUpdateRequest:
        output_fields = {
            "positioning_summary",
            "resume_bullets",
            "cover_letter",
            "application_snippets",
            "suggested_proof_artifacts",
            "reviewer_questions",
        }
        if not (self.model_fields_set & output_fields):
            raise ValueError("Provide at least one generated output change.")
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in output_fields
        ):
            raise ValueError("Edited output sections cannot be null.")
        return self


class ApplicationClaimLedgerEntry(BaseModel):
    claim_id: str
    surface: str
    text: str
    memory_ids: list[uuid.UUID] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    enrichment_ids: list[uuid.UUID] = Field(default_factory=list)
    proof_artifact_ids: list[uuid.UUID] = Field(default_factory=list)
    support_level: str
    warnings: list[str] = Field(default_factory=list)
    user_edited: bool = False
    strategy_signal_ids: list[uuid.UUID] = Field(default_factory=list)
    strategy_signal_caveat: str | None = None


class ApplicationPackageMemoryOption(BaseModel):
    id: uuid.UUID
    title: str
    memory_type: str
    evidence_count: int
    source_labels: list[str]
    confidence: float = Field(ge=0, le=1)
    target_reason: str | None = None


class ApplicationPackageVersionView(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    version_number: int
    target_snapshot: dict[str, object]
    selected_memory_ids: list[uuid.UUID]
    input_fingerprint: str
    outputs: ApplicationPackageOutputs
    evidence_trace: list[ApplicationEvidenceTrace]
    warnings: list[ApplicationPackageWarning]
    claim_ledger: list[ApplicationClaimLedgerEntry]
    memory_ids_used: list[uuid.UUID]
    enrichment_ids_used: list[uuid.UUID]
    outcome_signal_ids_used: list[uuid.UUID]
    user_edits: dict[str, object]
    generator_version: str
    generation_reason: ApplicationPackageGenerationReason
    created_at: datetime


class ApplicationPackageView(BaseModel):
    package_id: uuid.UUID
    opportunity_id: uuid.UUID | None
    display_name: str
    role_title: str
    company: str | None
    location: str | None
    job_type: str | None
    target_description: str
    required_skills: list[str]
    preferred_skills: list[str]
    responsibilities: list[str]
    selected_memory_ids: list[uuid.UUID]
    status: ApplicationPackageStatus
    latest_version: ApplicationPackageVersionView | None
    versions: list[ApplicationPackageVersionView]
    version_count: int
    is_stale: bool
    positioning_summary: PositioningSummary | None = None
    resume_bullets: list[ResumeBulletGroup] = Field(default_factory=list)
    cover_letter: CoverLetterDraft | None = None
    application_snippets: list[ApplicationSnippet] = Field(default_factory=list)
    suggested_proof_artifacts: list[SuggestedProofArtifact] = Field(
        default_factory=list
    )
    evidence_trace: list[ApplicationEvidenceTrace] = Field(default_factory=list)
    warnings: list[ApplicationPackageWarning] = Field(default_factory=list)
    reviewer_questions: list[str] = Field(default_factory=list)
    memory_ids_used: list[uuid.UUID] = Field(default_factory=list)
    enrichment_ids_used: list[uuid.UUID] = Field(default_factory=list)
    outcome_signal_ids_used: list[uuid.UUID] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ApplicationPackageListItem(BaseModel):
    package_id: uuid.UUID
    display_name: str
    role_title: str
    company: str | None
    status: ApplicationPackageStatus
    selected_memory_ids: list[uuid.UUID]
    version_count: int
    latest_version_number: int | None
    is_stale: bool
    created_at: datetime
    updated_at: datetime

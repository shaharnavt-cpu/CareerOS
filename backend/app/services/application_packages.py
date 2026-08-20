"""Deterministic, evidence-backed application package generation."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.models import (
    ApplicationOpportunity,
    ApplicationPackage,
    ApplicationPackageVersion,
    CanonicalMemoryRecord,
    ProofArtifact,
    ReviewProposal,
    User,
)
from app.schemas.application_packages import (
    ApplicationClaimLedgerEntry,
    ApplicationClaimPlan,
    ApplicationEvidenceGroup,
    ApplicationEvidenceTrace,
    ApplicationJobUnderstanding,
    ApplicationPackageCreateRequest,
    ApplicationPackageGenerateRequest,
    ApplicationPackageGenerationReason,
    ApplicationPackageListItem,
    ApplicationPackageMemoryOption,
    ApplicationPackageOutputs,
    ApplicationPackageOutputsUpdateRequest,
    ApplicationPackageStatus,
    ApplicationPackageUpdateRequest,
    ApplicationPackageVersionView,
    ApplicationPackageView,
    ApplicationPackageWarning,
    ApplicationProviderMetadata,
    ApplicationQuestion,
    ApplicationSnippet,
    ApplicationValidationRepair,
    ApplicationValidationSummary,
    ApplicationWarningGroups,
    ApplicationWarningSeverity,
    ApplicationWritingIntelligence,
    ApplicationWritingQualityReview,
    CoverLetterDraft,
    CoverLetterParagraphTrace,
    EvidenceSourceType,
    EvidenceSupportType,
    PositioningSummary,
    RequirementCoverage,
    RequirementCoverageItem,
    ResumeBullet,
    ResumeBulletGroup,
    SuggestedProofArtifact,
)
from app.schemas.career_memory import CompiledCareerMemoryProfile, CompiledEvidenceKind
from app.schemas.knowledge import DEMO_USER_ID, DurableReviewStatus
from app.services.application_writing_provider import (
    ApplicationQuestionInput,
    ApplicationSnippetOutput,
    ApplicationWritingDataClassification,
    ApplicationWritingDataSource,
    ApplicationWritingErrorCode,
    ApplicationWritingInput,
    ApplicationWritingMalformedOutputError,
    ApplicationWritingOutput,
    ApplicationWritingProvider,
    ApplicationWritingProviderError,
    ApplicationWritingRequirements,
    ApprovedEnrichmentInput,
    ApprovedEvidenceAtom,
    CandidateClaimType,
    CandidateFacingClaim,
    ClaimCertainty,
    ClaimPlanOutput,
    CoverLetterSectionsOutput,
    EvidenceAtomSupportType,
    EvidenceReferenceUsed,
    JobUnderstandingOutput,
    MissingProofWarningInput,
    ProofArtifactInput,
    RequirementCoverageLevel,
    ResumeBulletGroupOutput,
    ResumeBulletOutput,
    SelectedCompiledMemory,
    StrategyOutcomeSignal,
    StructuredOutcome,
    UnsupportedRequirementOutput,
    _direct_proof_patterns,
    _mask_target_role_framing,
    build_application_writing_provider,
    sanitize_application_writing_output,
    validate_application_writing_output_contract,
)
from app.services.application_writing_provider import (
    RequirementCoverageItem as ProviderRequirementCoverageItem,
)
from app.services.career_memory_compiler import (
    CareerMemoryCompilationError,
    CareerMemoryCompiler,
)


class ApplicationPackageNotFoundError(LookupError):
    """Raised when a package resource is outside the current-user boundary."""


class ApplicationPackageValidationError(ValueError):
    """Raised when generation would violate package trust or freshness rules."""


@dataclass(frozen=True)
class _RankedProfile:
    profile: CompiledCareerMemoryProfile
    score: float
    target_reason: str


@dataclass(frozen=True)
class _EditedClaim:
    claim_id: str
    surface: str
    text: str
    memory_ids: tuple[uuid.UUID, ...]


class ApplicationPackageService:
    """Create versioned application materials from exact compiled memories."""

    generator_version = "application-writing-intelligence-v3"

    _requirement_rules: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
        ("Python", (r"\bpython\b",), (r"\bpython\b",)),
        ("SQL", (r"\bsql\b",), (r"\bsql\b",)),
        ("R", (r"(?<![a-z])r(?![a-z])",), (r"(?<![a-z])r(?![a-z])",)),
        ("Excel", (r"\bexcel\b",), (r"\bexcel\b",)),
        ("Tableau", (r"\btableau\b",), (r"\btableau\b",)),
        ("Power BI", (r"\bpower\s*bi\b",), (r"\bpower\s*bi\b",)),
        (
            "data analysis",
            (
                r"\banalytics?\b",
                r"\bdata analysis\b",
                r"\banalytical workflows?\b",
                r"\bresearch analysis\b",
                r"\bstatistical analysis\b",
                r"\banaly[sz](?:e|ed|ing|is)\b",
            ),
            (
                r"\banalytics?\b",
                r"\bdata analysis\b",
                r"\banalytical workflows?\b",
                r"\bresearch analysis\b",
                r"\bstatistical analysis\b",
                r"\banaly[sz](?:e|ed|ing|is)\b",
            ),
        ),
        (
            "modeling",
            (r"\bmodel(?:s|ed|ing|ling)?\b",),
            (r"\bmodel(?:s|ed|ing|ling)?\b", r"gaussian fit"),
        ),
        (
            "statistics",
            (r"\bstatistic",),
            (r"\bstatistic", r"uncertainty", r"covariance"),
        ),
        (
            "uncertainty reasoning",
            (r"\buncertaint", r"error reasoning", r"error propagation"),
            (r"\buncertaint", r"error propagation", r"covariance"),
        ),
        (
            "technical communication",
            (
                r"\bcommunicat",
                r"\bpresent",
                r"\bdocumentation\b",
                r"\breport(?:ing|s)?\b",
                r"explaining results",
            ),
            (
                r"\bcommunicat",
                r"\bpresent",
                r"\bdocumentation\b",
                r"\breport(?:ing|s)?\b",
                r"explaining (?:findings|results)",
            ),
        ),
        (
            "data quality",
            (r"data quality", r"quality control", r"quality review"),
            (
                r"data quality",
                r"quality control",
                r"quality review",
                r"quality cuts",
                r"visual inspection",
                r"categorization",
                r"review workflow",
                r"validation",
            ),
        ),
        (
            "image or data labeling",
            (r"\blabel(?:ing|led)?\b", r"image inspection", r"categorization"),
            (r"\blabel(?:ing|led)?\b", r"image inspection", r"categorization"),
        ),
        (
            "automation",
            (r"\bautomat",),
            (r"\bautomat",),
        ),
        (
            "machine learning",
            (
                r"machine learning",
                r"\bml\b",
            ),
            (r"machine learning", r"\bml\b", r"trained model"),
        ),
        ("AWS", (r"\baws\b",), (r"\baws\b",)),
        ("Azure", (r"\bazure\b",), (r"\bazure\b",)),
        ("GCP", (r"\bgcp\b", r"google cloud"), (r"\bgcp\b", r"google cloud")),
        (
            "cloud infrastructure",
            (r"cloud infrastructure", r"cloud platform", r"cloud services"),
            (r"cloud infrastructure", r"cloud platform", r"cloud services"),
        ),
        (
            "Kubernetes",
            (r"\bkubernetes\b", r"\bk8s\b"),
            (r"\bkubernetes\b", r"\bk8s\b"),
        ),
        ("Docker", (r"\bdocker\b",), (r"\bdocker\b",)),
        ("Java", (r"\bjava\b",), (r"\bjava\b",)),
        (
            "LLMs",
            (r"\bllms?\b", r"large language model"),
            (r"\bllms?\b", r"large language model"),
        ),
        (
            "RAG",
            (r"\brag\b", r"retrieval[- ]augmented"),
            (r"\brag\b", r"retrieval[- ]augmented"),
        ),
        (
            "agents",
            (r"\bai agents?\b", r"\bagentic\b"),
            (r"\bai agents?\b", r"\bagentic\b"),
        ),
        (
            "research problem solving",
            (
                r"problem solving",
                r"hypothesis testing",
                r"research design",
                r"experimentation",
                r"debugging",
                r"interpreting uncertainty",
            ),
            (
                r"problem solving",
                r"hypothesis",
                r"research design",
                r"experiment",
                r"debug",
                r"uncertaint",
            ),
        ),
        (
            "production ML deployment",
            (
                r"production (?:ml|machine learning|ai)",
                r"(?:deploy|deployed|deployment)\w* (?:ml|model|ai)",
                r"model deployment",
                r"\bmlops\b",
            ),
            (r"\bdeploy", r"production model", r"\bmlops\b"),
        ),
        (
            "deployment",
            (r"\bdeploy(?:ed|ing|ment|ments)?\b",),
            (r"\bdeploy(?:ed|ing|ment|ments)?\b",),
        ),
        (
            "leadership",
            (r"\bleadership\b", r"\blead (?:a |the )?team\b"),
            (r"\bleadership\b", r"\bled (?:a |the )?team\b"),
        ),
    )

    def __init__(
        self,
        user_id: uuid.UUID = DEMO_USER_ID,
        compiler: CareerMemoryCompiler | None = None,
        settings: Settings | None = None,
        writing_provider: ApplicationWritingProvider | None = None,
    ) -> None:
        self.user_id = user_id
        self.compiler = compiler or CareerMemoryCompiler(user_id=user_id)
        self.settings = settings or get_settings()
        self.writing_provider = writing_provider

    def list_eligible_memories(
        self,
        session: Session,
        target_role: str | None = None,
    ) -> list[ApplicationPackageMemoryOption]:
        records = session.scalars(
            select(CanonicalMemoryRecord)
            .join(
                ReviewProposal,
                ReviewProposal.id == CanonicalMemoryRecord.review_proposal_id,
            )
            .where(
                CanonicalMemoryRecord.user_id == self.user_id,
                ReviewProposal.user_id == self.user_id,
                ReviewProposal.decision.in_(
                    (
                        DurableReviewStatus.APPROVED.value,
                        DurableReviewStatus.EDITED_APPROVED.value,
                    )
                ),
                CanonicalMemoryRecord.memory_type.notin_(
                    ("CONTACT", "ORGANIZATION", "NEEDS_CLASSIFICATION")
                ),
            )
            .order_by(CanonicalMemoryRecord.updated_at.desc())
        ).all()
        ready_artifact_memory_ids = set(
            session.scalars(
                select(ProofArtifact.source_memory_id).where(
                    ProofArtifact.user_id == self.user_id,
                    ProofArtifact.status == "READY",
                )
            ).all()
        )
        options: list[tuple[float, ApplicationPackageMemoryOption]] = []
        target_text = target_role or ""
        for recency_rank, memory in enumerate(records):
            profile = self.compiler.compile(session, memory.id, target_role)
            ranked = self._rank_profile(profile, target_text)
            effective_score = ranked.score
            if target_role:
                effective_score += max(0.0, 0.04 - recency_rank * 0.005)
                if memory.id in ready_artifact_memory_ids:
                    effective_score += 0.08
            options.append(
                (
                    round(min(effective_score, 1.0), 3),
                    ApplicationPackageMemoryOption(
                        id=memory.id,
                        title=memory.title,
                        memory_type=memory.memory_type,
                        evidence_count=len(profile.evidence_used),
                        source_labels=self._unique(
                            item.source_label for item in profile.evidence_used
                        ),
                        confidence=profile.confidence,
                        target_reason=(ranked.target_reason if target_role else None),
                    ),
                )
            )
        if target_role:
            options.sort(key=lambda item: item[0], reverse=True)
            substantive = [
                (score, option)
                for score, option in options
                if option.evidence_count > 0 and option.confidence >= 0.45
            ]
            recommendation_count = (
                min(4, len(substantive)) if len(substantive) >= 2 else 0
            )
            if recommendation_count > 2:
                cutoff_score = substantive[2][0]
                recommendation_count = min(
                    4,
                    max(
                        2,
                        sum(
                            score >= max(cutoff_score * 0.72, 0.12)
                            for score, _ in substantive
                        ),
                    ),
                )
            for rank, (_, option) in enumerate(
                substantive[:recommendation_count], start=1
            ):
                option.recommended = True
                option.recommendation_rank = rank
        return [item for _, item in options]

    def create(
        self,
        session: Session,
        request: ApplicationPackageCreateRequest,
    ) -> ApplicationPackageView:
        self._ensure_user(session)
        self._validate_opportunity(session, request.opportunity_id)
        if request.selected_memory_ids:
            self._compile_selected(
                session,
                request.selected_memory_ids,
                request.role_title,
            )
        display_name = request.display_name or self._display_name(
            request.role_title,
            request.company,
        )
        package = ApplicationPackage(
            user_id=self.user_id,
            opportunity_id=request.opportunity_id,
            display_name=display_name,
            role_title=request.role_title,
            company=request.company or None,
            location=request.location or None,
            job_type=request.job_type or None,
            target_description=request.target_description.strip(),
            required_skills=self._clean_list(request.required_skills),
            preferred_skills=self._clean_list(request.preferred_skills),
            responsibilities=self._clean_list(request.responsibilities),
            application_questions=[
                question.model_dump(mode="json")
                for question in request.application_questions
            ],
            selected_memory_ids=[str(item) for item in request.selected_memory_ids],
            status=ApplicationPackageStatus.DRAFT.value,
        )
        session.add(package)
        session.commit()
        return self.get(session, package.id)

    def list(
        self,
        session: Session,
        *,
        include_archived: bool = False,
    ) -> list[ApplicationPackageListItem]:
        statement = select(ApplicationPackage).where(
            ApplicationPackage.user_id == self.user_id
        )
        if not include_archived:
            statement = statement.where(
                ApplicationPackage.status != ApplicationPackageStatus.ARCHIVED.value
            )
        records = session.scalars(
            statement.order_by(ApplicationPackage.updated_at.desc())
        ).all()
        return [self._list_item(session, record) for record in records]

    def get(
        self,
        session: Session,
        package_id: uuid.UUID,
    ) -> ApplicationPackageView:
        return self._view(session, self._get_package(session, package_id))

    def update(
        self,
        session: Session,
        package_id: uuid.UUID,
        request: ApplicationPackageUpdateRequest,
    ) -> ApplicationPackageView:
        package = self._get_package(session, package_id, lock=True)
        fields = request.model_fields_set
        if "opportunity_id" in fields:
            self._validate_opportunity(session, request.opportunity_id)
            package.opportunity_id = request.opportunity_id
        if "display_name" in fields and request.display_name is not None:
            package.display_name = request.display_name
        if "role_title" in fields and request.role_title is not None:
            package.role_title = request.role_title
        if "company" in fields:
            package.company = request.company or None
        if "location" in fields:
            package.location = request.location or None
        if "job_type" in fields:
            package.job_type = request.job_type or None
        if "target_description" in fields and request.target_description is not None:
            package.target_description = request.target_description.strip()
        if "required_skills" in fields and request.required_skills is not None:
            package.required_skills = self._clean_list(request.required_skills)
        if "preferred_skills" in fields and request.preferred_skills is not None:
            package.preferred_skills = self._clean_list(request.preferred_skills)
        if "responsibilities" in fields and request.responsibilities is not None:
            package.responsibilities = self._clean_list(request.responsibilities)
        if (
            "application_questions" in fields
            and request.application_questions is not None
        ):
            package.application_questions = [
                question.model_dump(mode="json")
                for question in request.application_questions
            ]
        if "selected_memory_ids" in fields and request.selected_memory_ids is not None:
            if request.selected_memory_ids:
                self._compile_selected(
                    session,
                    request.selected_memory_ids,
                    package.role_title,
                )
            package.selected_memory_ids = [
                str(item) for item in request.selected_memory_ids
            ]
        generation_input_fields = {
            "opportunity_id",
            "role_title",
            "company",
            "location",
            "job_type",
            "target_description",
            "required_skills",
            "preferred_skills",
            "responsibilities",
            "application_questions",
            "selected_memory_ids",
        }
        if (
            package.status == ApplicationPackageStatus.READY.value
            and fields & generation_input_fields
        ):
            latest = self._latest_version(session, package.id)
            if latest is not None and self._is_stale(session, package, latest):
                package.status = ApplicationPackageStatus.DRAFT.value
        if "status" in fields and request.status is not None:
            if request.status == ApplicationPackageStatus.READY:
                latest = self._latest_version(session, package.id)
                if latest is None:
                    raise ApplicationPackageValidationError(
                        "Generate and review this package before marking it ready."
                    )
                if self._is_stale(session, package, latest):
                    raise ApplicationPackageValidationError(
                        "Regenerate this stale package before marking it ready."
                    )
                blocking = [
                    ApplicationPackageWarning.model_validate(item)
                    for item in latest.warnings_json
                    if item.get("severity") == ApplicationWarningSeverity.BLOCKING.value
                ]
                if blocking:
                    raise ApplicationPackageValidationError(
                        "Resolve blocking claim warnings before marking this package "
                        "ready."
                    )
            package.status = request.status.value
        session.commit()
        return self.get(session, package.id)

    def generate(
        self,
        session: Session,
        package_id: uuid.UUID,
        request: ApplicationPackageGenerateRequest | None = None,
    ) -> ApplicationPackageView:
        package = self._get_package(session, package_id, lock=True)
        existing = self._latest_version(session, package.id)
        reason = (
            ApplicationPackageGenerationReason.REGENERATED
            if existing is not None
            else ApplicationPackageGenerationReason.GENERATED
        )
        return self._generate(session, package, request, reason)

    def regenerate(
        self,
        session: Session,
        package_id: uuid.UUID,
        request: ApplicationPackageGenerateRequest | None = None,
    ) -> ApplicationPackageView:
        package = self._get_package(session, package_id, lock=True)
        if self._latest_version(session, package.id) is None:
            raise ApplicationPackageValidationError(
                "Generate the first package version before regenerating."
            )
        return self._generate(
            session,
            package,
            request,
            ApplicationPackageGenerationReason.REGENERATED,
        )

    def update_outputs(
        self,
        session: Session,
        package_id: uuid.UUID,
        request: ApplicationPackageOutputsUpdateRequest,
    ) -> ApplicationPackageView:
        package = self._get_package(session, package_id, lock=True)
        latest = self._latest_version(session, package.id)
        if latest is None:
            raise ApplicationPackageValidationError(
                "Generate the package before saving output edits."
            )
        if self._is_stale(session, package, latest):
            raise ApplicationPackageValidationError(
                "Target or selected proof changed. Regenerate before saving edits."
            )

        base_outputs = ApplicationPackageOutputs.model_validate(
            latest.generated_outputs_json
        )
        outputs, changed_fields, newly_edited_ids = self._merge_output_edits(
            base_outputs,
            request,
            self._uuid_list(latest.selected_memory_ids_json),
        )
        previously_edited_ids = {
            str(item.get("claim_id"))
            for item in latest.claim_ledger_json
            if item.get("user_edited") and item.get("claim_id")
        }
        edited_claim_ids = previously_edited_ids | newly_edited_ids
        edited_claims = self._edited_claims(
            outputs,
            edited_claim_ids,
            self._uuid_list(latest.selected_memory_ids_json),
        )
        generated_baseline = self._latest_generated_version(session, package.id)
        if generated_baseline is None:
            raise ApplicationPackageValidationError(
                "The generated baseline for this package could not be found."
            )
        baseline_outputs = ApplicationPackageOutputs.model_validate(
            generated_baseline.generated_outputs_json
        )
        baseline_claims = {
            claim.claim_id: claim.text
            for claim in self._edited_claims(
                baseline_outputs,
                edited_claim_ids,
                self._uuid_list(generated_baseline.selected_memory_ids_json),
            )
        }
        audited_claims = [
            _EditedClaim(
                claim_id=claim.claim_id,
                surface=claim.surface,
                text=self._changed_claim_text(
                    baseline_claims.get(claim.claim_id, ""), claim.text
                ),
                memory_ids=claim.memory_ids,
            )
            for claim in edited_claims
        ]
        audited_claims = [claim for claim in audited_claims if claim.text]

        edit_warning_codes = {
            "USER_EDIT_REVIEW",
            "UNSUPPORTED_EDITED_NUMBER",
            "UNSUPPORTED_EDITED_CLAIM",
            "CROSS_MEMORY_EDITED_CLAIM",
        }
        warnings = [
            ApplicationPackageWarning.model_validate(item)
            for item in latest.warnings_json
            if item.get("code") not in edit_warning_codes
        ]
        warnings = self._dedupe_warnings(
            [
                *warnings,
                ApplicationPackageWarning(
                    code="USER_EDIT_REVIEW",
                    message=(
                        "This version includes user-edited application text. Review "
                        "new factual wording against the preserved evidence trace."
                    ),
                    severity=ApplicationWarningSeverity.CAUTION,
                ),
            ]
        )
        unsupported_numbers = self._unsupported_numbers_for_claims(
            audited_claims,
            latest.compiled_profile_snapshots_json,
            latest.target_snapshot_json,
        )
        unsupported_terms = self._unsupported_terms_for_claims(
            audited_claims,
            latest.compiled_profile_snapshots_json,
            [item.requirement for item in warnings if item.requirement],
        )
        unsupported_terms = self._unique(
            [
                *unsupported_terms,
                *self._unsupported_outcomes_for_claims(
                    audited_claims,
                    latest.compiled_profile_snapshots_json,
                ),
            ]
        )
        cross_memory_terms = self._cross_memory_terms_for_claims(
            audited_claims,
            latest.compiled_profile_snapshots_json,
        )
        outputs.unsupported_claims = [
            item
            for item in outputs.unsupported_claims
            if not item.startswith(
                (
                    "Unverified numeric claim:",
                    "Unverified edited claim:",
                    "Cross-memory edited claim:",
                )
            )
        ]
        if unsupported_numbers:
            warnings = self._dedupe_warnings(
                [
                    *warnings,
                    ApplicationPackageWarning(
                        code="UNSUPPORTED_EDITED_NUMBER",
                        message=(
                            "Edited text contains numbers not found in the selected "
                            "source evidence: " + ", ".join(unsupported_numbers) + "."
                        ),
                        severity=ApplicationWarningSeverity.BLOCKING,
                    ),
                ]
            )
            outputs.unsupported_claims = self._unique(
                [
                    *outputs.unsupported_claims,
                    *(
                        f"Unverified numeric claim: {item}"
                        for item in unsupported_numbers
                    ),
                ]
            )
        if unsupported_terms:
            warnings = self._dedupe_warnings(
                [
                    *warnings,
                    ApplicationPackageWarning(
                        code="UNSUPPORTED_EDITED_CLAIM",
                        message=(
                            "Edited text appears to make unsupported first-person "
                            "claims about: " + ", ".join(unsupported_terms) + "."
                        ),
                        severity=ApplicationWarningSeverity.BLOCKING,
                    ),
                ]
            )
            outputs.unsupported_claims = self._unique(
                [
                    *outputs.unsupported_claims,
                    *(f"Unverified edited claim: {item}" for item in unsupported_terms),
                ]
            )
        if cross_memory_terms:
            warnings = self._dedupe_warnings(
                [
                    *warnings,
                    ApplicationPackageWarning(
                        code="CROSS_MEMORY_EDITED_CLAIM",
                        message=(
                            "Edited resume wording appears to borrow facts from a "
                            "different selected memory: "
                            + ", ".join(cross_memory_terms)
                            + "."
                        ),
                        severity=ApplicationWarningSeverity.BLOCKING,
                    ),
                ]
            )
            outputs.unsupported_claims = self._unique(
                [
                    *outputs.unsupported_claims,
                    *(
                        f"Cross-memory edited claim: {item}"
                        for item in cross_memory_terms
                    ),
                ]
            )

        ledger = self._claim_ledger(outputs, edited_claim_ids=edited_claim_ids)

        next_version = self._next_version_number(session, package.id)
        version = ApplicationPackageVersion(
            user_id=self.user_id,
            package_id=package.id,
            version_number=next_version,
            target_snapshot_json=latest.target_snapshot_json,
            selected_memory_ids_json=latest.selected_memory_ids_json,
            input_fingerprint=latest.input_fingerprint,
            compiled_profile_snapshots_json=latest.compiled_profile_snapshots_json,
            generated_outputs_json=outputs.model_dump(mode="json"),
            evidence_trace_json=latest.evidence_trace_json,
            warnings_json=[item.model_dump(mode="json") for item in warnings],
            claim_ledger_json=[item.model_dump(mode="json") for item in ledger],
            memory_ids_used_json=latest.memory_ids_used_json,
            enrichment_ids_used_json=latest.enrichment_ids_used_json,
            outcome_signal_ids_used_json=latest.outcome_signal_ids_used_json,
            user_edits_json={
                "base_version_id": str(latest.id),
                "changed_fields": changed_fields,
                "changed_claim_ids": sorted(newly_edited_ids),
                "user_edited_claim_ids": sorted(edited_claim_ids),
                "edit_summary": request.edit_summary,
                "unsupported_numbers": unsupported_numbers,
                "unsupported_terms": unsupported_terms,
                "cross_memory_terms": cross_memory_terms,
            },
            writing_intelligence_json=latest.writing_intelligence_json,
            quality_review_json=self._evaluate_output_quality(outputs).model_dump(
                mode="json"
            ),
            provider_metadata_json=latest.provider_metadata_json,
            validation_summary_json={
                **latest.validation_summary_json,
                "status": "PASS"
                if not any(
                    item.severity == ApplicationWarningSeverity.BLOCKING
                    for item in warnings
                )
                else "BLOCKED",
                "blocking_issue_count": sum(
                    item.severity == ApplicationWarningSeverity.BLOCKING
                    for item in warnings
                ),
                "notes": ["User edits were re-audited against the generated baseline."],
            },
            generator_version=self.generator_version,
            generation_reason=ApplicationPackageGenerationReason.USER_EDIT.value,
        )
        package.status = ApplicationPackageStatus.DRAFT.value
        package.updated_at = datetime.now(UTC)
        session.add(version)
        session.commit()
        return self.get(session, package.id)

    def _merge_output_edits(
        self,
        base: ApplicationPackageOutputs,
        request: ApplicationPackageOutputsUpdateRequest,
        selected_memory_ids: list[uuid.UUID],
    ) -> tuple[ApplicationPackageOutputs, list[str], set[str]]:
        """Apply applicant-authored text while keeping provenance server-owned."""

        outputs = base.model_copy(deep=True)
        changed_fields: list[str] = []
        changed_claim_ids: set[str] = set()
        edit_caveat = (
            "User-edited wording; preserved traces are reference context, not "
            "claim-level validation."
        )

        def changed(field: str) -> None:
            if field not in changed_fields:
                changed_fields.append(field)

        if "positioning_summary" in request.model_fields_set:
            requested = request.positioning_summary
            assert requested is not None
            positioning = outputs.positioning_summary
            if requested.primary_positioning != positioning.primary_positioning:
                positioning.primary_positioning = requested.primary_positioning
                changed("positioning_summary")
                changed_claim_ids.add("positioning-summary")
            if requested.strongest_evidence != positioning.strongest_evidence:
                positioning.strongest_evidence = requested.strongest_evidence
                changed("positioning_summary")
                changed_claim_ids.add("positioning-evidence")
            if "positioning_summary" in changed_fields:
                positioning.risks_and_gaps = self._unique(
                    [*positioning.risks_and_gaps, edit_caveat]
                )

        if "resume_bullets" in request.model_fields_set:
            requested_groups = request.resume_bullets
            assert requested_groups is not None
            if len(requested_groups) != len(outputs.resume_bullets):
                raise ApplicationPackageValidationError(
                    "Resume edit structure must match the generated memory groups."
                )
            for group_index, (requested_group, group) in enumerate(
                zip(requested_groups, outputs.resume_bullets, strict=True),
                start=1,
            ):
                if len(requested_group.bullets) != len(group.bullets):
                    raise ApplicationPackageValidationError(
                        "Resume edit structure must preserve generated bullet counts."
                    )
                for bullet_index, (requested_bullet, bullet) in enumerate(
                    zip(requested_group.bullets, group.bullets, strict=True),
                    start=1,
                ):
                    if requested_bullet.bullet_text == bullet.bullet_text:
                        continue
                    bullet.bullet_text = requested_bullet.bullet_text
                    bullet.warnings = self._unique([*bullet.warnings, edit_caveat])
                    changed("resume_bullets")
                    changed_claim_ids.add(f"resume-{group_index}-{bullet_index}")

        if "cover_letter" in request.model_fields_set:
            requested = request.cover_letter
            assert requested is not None
            if requested.full_text != outputs.cover_letter.full_text:
                outputs.cover_letter.full_text = requested.full_text
                outputs.cover_letter.warnings = self._unique(
                    [*outputs.cover_letter.warnings, edit_caveat]
                )
                changed("cover_letter")
                changed_claim_ids.add("cover-letter-full")

        if "application_snippets" in request.model_fields_set:
            requested_snippets = request.application_snippets
            assert requested_snippets is not None
            if len(requested_snippets) != len(outputs.application_snippets):
                raise ApplicationPackageValidationError(
                    "Snippet edit structure must match the generated questions."
                )
            for index, (requested_snippet, snippet) in enumerate(
                zip(requested_snippets, outputs.application_snippets, strict=True),
                start=1,
            ):
                if (
                    requested_snippet.question_id != snippet.question_id
                    or requested_snippet.question != snippet.question
                ):
                    raise ApplicationPackageValidationError(
                        "Snippet edits must preserve generated question IDs and order."
                    )
                if requested_snippet.text == snippet.text:
                    continue
                snippet.text = requested_snippet.text
                snippet.warnings = self._unique([*snippet.warnings, edit_caveat])
                changed("application_snippets")
                changed_claim_ids.add(f"snippet-{snippet.question_id or index}")

        if "suggested_proof_artifacts" in request.model_fields_set:
            requested = request.suggested_proof_artifacts
            assert requested is not None
            if self._json_value(requested) != self._json_value(
                outputs.suggested_proof_artifacts
            ):
                raise ApplicationPackageValidationError(
                    "Suggested proof artifact identities are server-owned and cannot "
                    "be edited here."
                )

        if "reviewer_questions" in request.model_fields_set:
            requested = request.reviewer_questions
            assert requested is not None
            cleaned = self._clean_list(requested)
            if cleaned != outputs.reviewer_questions:
                outputs.reviewer_questions = cleaned
                changed("reviewer_questions")

        if not changed_fields:
            raise ApplicationPackageValidationError(
                "No editable application text changed. Provenance fields are "
                "server-owned."
            )
        if not selected_memory_ids:
            raise ApplicationPackageValidationError(
                "Edited output no longer has a selected-memory boundary."
            )
        return outputs, changed_fields, changed_claim_ids

    def _edited_claims(
        self,
        outputs: ApplicationPackageOutputs,
        claim_ids: set[str],
        selected_memory_ids: list[uuid.UUID],
    ) -> list[_EditedClaim]:
        claims: list[_EditedClaim] = []
        all_ids = tuple(selected_memory_ids)

        def add(
            claim_id: str,
            surface: str,
            value: str,
            memory_ids: Iterable[uuid.UUID],
        ) -> None:
            if claim_id in claim_ids:
                claims.append(
                    _EditedClaim(
                        claim_id=claim_id,
                        surface=surface,
                        text=value,
                        memory_ids=tuple(self._unique_uuid(memory_ids)),
                    )
                )

        add(
            "positioning-summary",
            "positioning",
            outputs.positioning_summary.primary_positioning,
            all_ids,
        )
        add(
            "positioning-evidence",
            "positioning",
            outputs.positioning_summary.strongest_evidence,
            all_ids,
        )
        for group_index, group in enumerate(outputs.resume_bullets, start=1):
            for bullet_index, bullet in enumerate(group.bullets, start=1):
                add(
                    f"resume-{group_index}-{bullet_index}",
                    "resume",
                    bullet.bullet_text,
                    (group.memory_id,),
                )
        add(
            "cover-letter-full",
            "cover_letter",
            outputs.cover_letter.full_text,
            all_ids,
        )
        for index, snippet in enumerate(outputs.application_snippets, start=1):
            memory_ids = self._unique_uuid(
                trace.memory_id
                for trace in snippet.evidence_trace
                if trace.memory_id is not None
                and trace.source_type != EvidenceSourceType.TARGET_CONTEXT
            )
            add(
                f"snippet-{snippet.question_id or index}",
                "snippet",
                snippet.text,
                memory_ids or all_ids,
            )
        return claims

    def _generate(
        self,
        session: Session,
        package: ApplicationPackage,
        request: ApplicationPackageGenerateRequest | None,
        reason: ApplicationPackageGenerationReason,
    ) -> ApplicationPackageView:
        if request is not None and request.selected_memory_ids is not None:
            package.selected_memory_ids = [
                str(item) for item in request.selected_memory_ids
            ]
        if request is not None and request.application_questions is not None:
            package.application_questions = [
                question.model_dump(mode="json")
                for question in request.application_questions
            ]
        selected_ids = self._uuid_list(package.selected_memory_ids)
        if not selected_ids:
            raise ApplicationPackageValidationError(
                "Select at least one approved Career Memory before generating."
            )
        if len(selected_ids) > self.settings.openai_application_max_selected_memories:
            raise ApplicationPackageValidationError(
                "Select no more than four Career Memories for a focused draft."
            )
        profiles = self._compile_selected(session, selected_ids, package.role_title)
        target_text = self._target_text(package)
        ranked = sorted(
            (self._rank_profile(profile, target_text) for profile in profiles),
            key=lambda item: item.score,
            reverse=True,
        )
        max_memories = self.settings.openai_application_max_selected_memories
        writing_ranked = ranked[:max_memories]
        target_snapshot = self._target_snapshot(package)
        profile_snapshots = [item.model_dump(mode="json") for item in profiles]
        fingerprint = self._fingerprint(
            target_snapshot,
            selected_ids,
            profile_snapshots,
        )
        evidence_trace = self._aggregate_evidence_trace(package, writing_ranked)
        warnings, unsupported_requirements = self._warnings(package, writing_ranked)
        coverage = self._requirement_coverage(package, writing_ranked)
        writing_input = self._application_writing_input(
            session,
            package,
            writing_ranked,
            warnings,
            coverage,
        )
        try:
            provider = self.writing_provider or build_application_writing_provider(
                self.settings,
                local_generator=lambda provider_input: self._local_writing_output(
                    session,
                    package,
                    writing_ranked,
                    warnings,
                    unsupported_requirements,
                    coverage,
                    provider_input,
                ),
            )
            # The server-authored ledger remains the validation authority. Give the
            # provider an isolated copy so an in-process implementation cannot
            # mutate approved atoms before the returned draft is checked.
            writing_output = provider.generate_application_draft(
                writing_input.model_copy(deep=True)
            )
            writing_output = sanitize_application_writing_output(
                writing_input,
                writing_output,
            )
            outputs = self._materialize_provider_outputs(
                session,
                package,
                writing_ranked,
                warnings,
                coverage,
                writing_output,
                writing_input,
            )
            self._validate_generated_outputs(
                outputs,
                writing_output,
                writing_input,
                profile_snapshots,
                target_snapshot,
                warnings,
            )
        except ApplicationWritingProviderError as exc:
            session.rollback()
            raise ApplicationPackageValidationError(exc.safe_message) from exc
        ledger = self._claim_ledger(
            outputs,
            candidate_claims=writing_output.candidate_claims,
        )
        intelligence = self._writing_intelligence(
            package,
            writing_ranked,
            coverage,
            writing_output,
            outputs,
        )
        quality_review = self._evaluate_output_quality(outputs)
        if writing_output.quality_review_notes:
            quality_review.notes = self._unique(
                [*quality_review.notes, *writing_output.quality_review_notes]
            )[:4]
            if (
                quality_review.primary_issue
                == "No material writing-quality issue detected."
            ):
                quality_review.primary_issue = writing_output.quality_review_notes[0]
        provider_metadata = ApplicationProviderMetadata(
            provider=writing_output.provider_metadata.provider,
            model=writing_output.provider_metadata.model,
            review_model=writing_output.provider_metadata.review_model,
            review_pass_ran=writing_output.provider_metadata.review_pass_ran,
            request_id=writing_output.provider_metadata.request_id,
            input_tokens=writing_output.provider_metadata.input_tokens,
            cached_input_tokens=(writing_output.provider_metadata.cached_input_tokens),
            output_tokens=writing_output.provider_metadata.output_tokens,
            latency_ms=writing_output.provider_metadata.latency_ms,
        )
        validation_repairs = [
            ApplicationValidationRepair.model_validate(repair.model_dump(mode="json"))
            for repair in writing_output.validation_metadata.repairs
        ]
        unsupported_repairs = [
            repair
            for repair in validation_repairs
            if repair.code == "REMOVE_OPTIONAL_UNSUPPORTED_WARNING"
        ]
        answer_repairs = [
            repair
            for repair in validation_repairs
            if repair.code == "MISSING_REQUIRED_APPLICATION_ANSWER"
        ]
        validation_summary = ApplicationValidationSummary(
            status="PASS",
            unsupported_claims_removed=len(unsupported_repairs),
            blocking_issue_count=0,
            notes=[
                "Structured output and evidence references passed server validation.",
                "Tools, metrics, memory boundaries, and strategy-only signals "
                "were audited.",
                *(
                    ["Optional unsupported warning language was removed and recorded."]
                    if unsupported_repairs
                    else []
                ),
                *(
                    ["Missing required application answers were repaired in place."]
                    if answer_repairs
                    else []
                ),
            ],
            repairs=validation_repairs,
        )
        memory_ids = [item.profile.memory_id for item in writing_ranked]
        enrichment_ids = self._unique_uuid(
            enrichment_id
            for item in writing_ranked
            for enrichment_id in item.profile.enrichment_ids_used
        )
        outcome_ids = self._unique_uuid(
            signal_id
            for item in writing_ranked
            for signal_id in item.profile.outcome_signal_ids_used
        )
        version = ApplicationPackageVersion(
            user_id=self.user_id,
            package_id=package.id,
            version_number=self._next_version_number(session, package.id),
            target_snapshot_json=target_snapshot,
            selected_memory_ids_json=[str(item) for item in selected_ids],
            input_fingerprint=fingerprint,
            compiled_profile_snapshots_json=profile_snapshots,
            generated_outputs_json=outputs.model_dump(mode="json"),
            evidence_trace_json=[
                item.model_dump(mode="json") for item in evidence_trace
            ],
            warnings_json=[item.model_dump(mode="json") for item in warnings],
            claim_ledger_json=[item.model_dump(mode="json") for item in ledger],
            memory_ids_used_json=[str(item) for item in memory_ids],
            enrichment_ids_used_json=[str(item) for item in enrichment_ids],
            outcome_signal_ids_used_json=[str(item) for item in outcome_ids],
            user_edits_json={},
            writing_intelligence_json=intelligence.model_dump(mode="json"),
            quality_review_json=quality_review.model_dump(mode="json"),
            provider_metadata_json=provider_metadata.model_dump(mode="json"),
            validation_summary_json=validation_summary.model_dump(mode="json"),
            generator_version=self.generator_version,
            generation_reason=reason.value,
        )
        package.status = ApplicationPackageStatus.DRAFT.value
        package.updated_at = datetime.now(UTC)
        session.add(version)
        session.commit()
        return self.get(session, package.id)

    def _application_writing_input(
        self,
        session: Session,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        warnings: list[ApplicationPackageWarning],
        coverage: RequirementCoverage,
    ) -> ApplicationWritingInput:
        selected_memories: list[SelectedCompiledMemory] = []
        enrichment_inputs: list[ApprovedEnrichmentInput] = []
        outcome_signals: list[StrategyOutcomeSignal] = []
        for item in ranked:
            profile = item.profile
            has_claim_support = self._profile_has_claim_support(profile)
            supported_capabilities = self._profile_supported_capabilities(profile)
            supported_methods = self._profile_supported_values(
                profile, profile.methods
            )
            supported_outcomes = self._profile_supported_values(
                profile, profile.findings_or_results
            )
            traces = self._claim_trace_for_profile(profile)
            reference_ids = [trace.trace_id for trace in traces]
            selected_memories.append(
                SelectedCompiledMemory(
                    memory_id=str(profile.memory_id),
                    title=profile.canonical_title,
                    memory_type=profile.memory_type,
                    summary=self._profile_evidence_summary(profile)[:5000],
                    approved_claims=(
                        self._unique(
                            self._profile_supported_values(
                                profile,
                                [
                                    *profile.proof_claims,
                                    *profile.resume_bullet_claims,
                                    *profile.findings_or_results,
                                ],
                            )
                        )[:50]
                        if has_claim_support
                        else []
                    ),
                    skills_and_tools=supported_capabilities[:50],
                    methods=supported_methods[:50],
                    outcomes=supported_outcomes[:25],
                    evidence_reference_ids=reference_ids[:100],
                    confidence=profile.confidence,
                )
            )
            for evidence, trace in zip(
                profile.evidence_used,
                self._all_profile_trace(profile),
                strict=False,
            ):
                if evidence.kind != CompiledEvidenceKind.APPROVED_ENRICHMENT:
                    continue
                enrichment_inputs.append(
                    ApprovedEnrichmentInput(
                        enrichment_id=evidence.evidence_id,
                        memory_id=str(profile.memory_id),
                        label=evidence.source_label[:300],
                        content=(evidence.excerpt or "Approved enrichment detail")[
                            :3000
                        ],
                        evidence_reference_ids=[trace.trace_id],
                    )
                )
            outcome_signals.extend(
                StrategyOutcomeSignal(
                    signal_id=str(signal.feedback_event_id),
                    label=signal.summary[:300],
                    content=f"{signal.guidance} ({signal.caveat})"[:2000],
                    strategy_only=True,
                )
                for signal in profile.outcome_signals[:25]
            )

        selected_ids = [item.profile.memory_id for item in ranked]
        artifacts = session.scalars(
            select(ProofArtifact)
            .where(
                ProofArtifact.user_id == self.user_id,
                ProofArtifact.source_memory_id.in_(selected_ids),
                ProofArtifact.status == "READY",
            )
            .order_by(ProofArtifact.updated_at.desc())
            .limit(25)
        ).all()
        proof_inputs = [
            ProofArtifactInput(
                artifact_id=str(artifact.id),
                title=artifact.title,
                artifact_type=artifact.artifact_type,
                summary=f"Existing {artifact.status.lower()} proof artifact.",
                memory_ids=[str(artifact.source_memory_id)],
            )
            for artifact in artifacts
        ]
        evidence_ledger = self._application_evidence_ledger(
            package,
            ranked,
            enrichment_inputs,
            artifacts,
        )
        classification = self._application_data_classification(session, selected_ids)
        unsupported_labels = [item.requirement for item in coverage.unsupported]
        concrete = {
            "Python",
            "SQL",
            "R",
            "Java",
            "AWS",
            "Azure",
            "GCP",
            "Docker",
            "Kubernetes",
            "cloud infrastructure",
            "deployment",
            "production ML deployment",
            "LLMs",
            "RAG",
            "agents",
            "Tableau",
            "Power BI",
        }
        requested = [
            item.requirement
            for group in (
                coverage.strongly_supported,
                coverage.partially_supported,
                coverage.unsupported,
                coverage.not_relevant_enough,
            )
            for item in group
        ]
        return ApplicationWritingInput(
            target_role=package.role_title,
            company=package.company,
            job_description=package.target_description[:30_000],
            grouped_requirements=ApplicationWritingRequirements(
                must_have=package.required_skills[:50],
                preferred=package.preferred_skills[:50],
                technical=[label for label in requested if label in concrete][:50],
                communication=[
                    label for label in requested if "communication" in label.casefold()
                ][:50],
                concrete_tools_requiring_direct_proof=[
                    label for label in requested if label in concrete
                ][:50],
                broad_semantic_concepts=[
                    label for label in requested if label not in concrete
                ][:50],
            ),
            central_responsibilities=package.responsibilities[:50],
            application_questions=[
                ApplicationQuestionInput.model_validate(question)
                for question in package.application_questions
            ],
            selected_memories=selected_memories,
            evidence_ledger=evidence_ledger,
            approved_enrichment=enrichment_inputs[:50],
            proof_artifacts=proof_inputs,
            outcome_signals=outcome_signals[:25],
            prohibited_claims=self._unique(
                [
                    *(
                        warning
                        for item in ranked
                        for warning in item.profile.warnings_not_to_claim
                    ),
                    *(
                        f"Do not claim unsupported {label}."
                        for label in unsupported_labels
                    ),
                ]
            )[:100],
            missing_proof_warnings=[
                MissingProofWarningInput(
                    requirement=warning.requirement or warning.code,
                    explanation=warning.message,
                    blocking_if_claimed=warning.code.startswith("UNSUPPORTED"),
                )
                for warning in warnings
                if warning.severity != ApplicationWarningSeverity.INFO
            ][:50],
            desired_tone="direct, professional, internship-appropriate, and natural",
            desired_output_length=(
                "250-400 word letter; 20-35 word bullets; concise answers"
            ),
            generator_version=self.generator_version,
            data_classification=classification,
        )

    def _application_evidence_ledger(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        enrichment_inputs: list[ApprovedEnrichmentInput],
        artifacts: list[ProofArtifact],
    ) -> list[ApprovedEvidenceAtom]:
        """Compile an immutable, order-independent claim ledger for the writer."""

        target_snapshot = self._target_snapshot(package)
        target_source = json.dumps(
            target_snapshot,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        company = f" at {package.company}" if package.company else ""
        atoms = [
            ApprovedEvidenceAtom(
                evidence_atom_id=self._stable_contract_id(
                    "atom-target", str(package.id), target_source
                ),
                approved_claim_id=self._stable_contract_id(
                    "claim-target", str(package.id), target_source
                ),
                support_type=EvidenceAtomSupportType.TARGET_CONTEXT,
                factual_statement=(
                    f"The target is the {package.role_title} role{company}."
                ),
                allowed_certainty=ClaimCertainty.ASPIRATIONAL,
                prohibited_expansions=[
                    "Target-job wording is relevance context, not candidate proof."
                ],
            )
        ]

        ranked_by_memory = {str(item.profile.memory_id): item for item in ranked}
        for item in ranked:
            profile = item.profile
            memory_id = str(profile.memory_id)
            has_claim_support = self._profile_has_claim_support(profile)
            supported_capabilities = self._profile_supported_capabilities(profile)
            supported_methods = self._profile_supported_values(
                profile, profile.methods
            )
            references = sorted(
                self._unique(
                    trace.trace_id for trace in self._factual_trace_for_profile(profile)
                )
            )[:100]
            tools = self._unique(
                [*supported_capabilities, *supported_methods]
            )[:50]
            methods = self._unique(supported_methods)[:50]
            prohibitions = self._unique(profile.warnings_not_to_claim)[:50]
            context = self._profile_evidence_summary(profile)[:5000]
            atoms.append(
                ApprovedEvidenceAtom(
                    evidence_atom_id=self._stable_contract_id(
                        "atom-memory", memory_id, "context", context
                    ),
                    canonical_memory_id=memory_id,
                    approved_claim_id=self._stable_contract_id(
                        "claim-memory", memory_id, "context", context
                    ),
                    evidence_reference_ids=references,
                    support_type=EvidenceAtomSupportType.DIRECT,
                    factual_statement=context,
                    supported_tools=tools,
                    supported_methods=methods,
                    allowed_certainty=ClaimCertainty.OBSERVED,
                    prohibited_expansions=prohibitions,
                )
            )
            component_statements: list[tuple[str, str]] = []
            if (
                has_claim_support
                and profile.research_question_or_problem
                and self._profile_value_has_claim_support(
                    profile, profile.research_question_or_problem
                )
            ):
                component_statements.append(
                    ("problem", profile.research_question_or_problem)
                )
            if has_claim_support:
                component_statements.extend(
                    ("input", value)
                    for value in self._profile_supported_values(
                        profile, profile.data_or_inputs
                    )
                )
                component_statements.extend(
                    ("workflow", value)
                    for value in self._profile_supported_values(
                        profile, profile.workflow_steps
                    )
                )
                component_statements.extend(
                    ("limitation", value)
                    for value in self._profile_supported_values(
                        profile, profile.limitations
                    )
                )
            for component_kind, statement in component_statements:
                rendered_statement = " ".join(statement.split()).strip()
                if not rendered_statement:
                    continue
                atoms.append(
                    ApprovedEvidenceAtom(
                        evidence_atom_id=self._stable_contract_id(
                            "atom-component",
                            memory_id,
                            component_kind,
                            rendered_statement,
                        ),
                        canonical_memory_id=memory_id,
                        approved_claim_id=self._stable_contract_id(
                            "claim-component",
                            memory_id,
                            component_kind,
                            rendered_statement,
                        ),
                        evidence_reference_ids=references,
                        support_type=EvidenceAtomSupportType.DIRECT,
                        factual_statement=rendered_statement[:5000],
                        supported_tools=[
                            tool
                            for tool in supported_capabilities
                            if self._literal_in_text(tool, rendered_statement)
                        ][:50],
                        supported_methods=[
                            method
                            for method in methods
                            if self._literal_in_text(method, rendered_statement)
                        ][:50],
                        allowed_certainty=self._claim_certainty(rendered_statement),
                        prohibited_expansions=prohibitions,
                    )
                )
            approved_claims = (
                self._profile_supported_values(
                    profile,
                    self._unique(
                        [*profile.proof_claims, *profile.resume_bullet_claims]
                    ),
                )
                if has_claim_support
                else []
            )
            for claim in approved_claims:
                atoms.append(
                    ApprovedEvidenceAtom(
                        evidence_atom_id=self._stable_contract_id(
                            "atom-claim", memory_id, claim
                        ),
                        canonical_memory_id=memory_id,
                        approved_claim_id=self._stable_contract_id(
                            "claim-approved", memory_id, claim
                        ),
                        evidence_reference_ids=references,
                        support_type=EvidenceAtomSupportType.DIRECT,
                        factual_statement=claim[:5000],
                        supported_tools=[
                            tool
                            for tool in supported_capabilities
                            if self._literal_in_text(tool, claim)
                        ][:50],
                        supported_methods=[
                            method
                            for method in methods
                            if self._literal_in_text(method, claim)
                        ][:50],
                        allowed_certainty=self._claim_certainty(claim),
                        prohibited_expansions=prohibitions,
                    )
                )
            for outcome_text in (
                self._profile_supported_values(
                    profile, self._unique(profile.findings_or_results)
                )
                if has_claim_support
                else []
            ):
                outcome_source_id = references[0] if references else memory_id
                outcome = self._structured_outcome(
                    self._candidate_result_phrase(outcome_text), outcome_source_id
                )
                atoms.append(
                    ApprovedEvidenceAtom(
                        evidence_atom_id=self._stable_contract_id(
                            "atom-outcome",
                            memory_id,
                            outcome_source_id,
                            outcome_text,
                        ),
                        canonical_memory_id=memory_id,
                        approved_claim_id=self._stable_contract_id(
                            "claim-outcome", memory_id, outcome_text
                        ),
                        evidence_reference_ids=references,
                        support_type=EvidenceAtomSupportType.DIRECT,
                        factual_statement=outcome_text[:5000],
                        supported_tools=[
                            tool
                            for tool in supported_capabilities
                            if self._literal_in_text(tool, outcome_text)
                        ][:50],
                        supported_methods=[
                            method
                            for method in methods
                            if self._literal_in_text(method, outcome_text)
                        ][:50],
                        supported_outcome=outcome,
                        allowed_certainty=outcome.certainty,
                        prohibited_expansions=prohibitions,
                    )
                )

        for enrichment in enrichment_inputs:
            ranked_item = ranked_by_memory.get(enrichment.memory_id)
            profile = ranked_item.profile if ranked_item is not None else None
            content = enrichment.content[:5000]
            atoms.append(
                ApprovedEvidenceAtom(
                    evidence_atom_id=self._stable_contract_id(
                        "atom-enrichment",
                        enrichment.memory_id,
                        enrichment.enrichment_id,
                        content,
                    ),
                    canonical_memory_id=enrichment.memory_id,
                    enrichment_id=enrichment.enrichment_id,
                    approved_claim_id=self._stable_contract_id(
                        "claim-enrichment",
                        enrichment.memory_id,
                        enrichment.enrichment_id,
                        content,
                    ),
                    evidence_reference_ids=enrichment.evidence_reference_ids,
                    support_type=EvidenceAtomSupportType.APPROVED_ENRICHMENT,
                    factual_statement=content,
                    supported_tools=(
                        self._tools_explicit_in_text(profile, content)
                        if profile is not None
                        else []
                    ),
                    supported_methods=(
                        [
                            method
                            for method in profile.methods
                            if self._literal_in_text(method, content)
                        ][:50]
                        if profile is not None
                        else []
                    ),
                    allowed_certainty=self._claim_certainty(content),
                    prohibited_expansions=(
                        self._unique(profile.warnings_not_to_claim)[:50]
                        if profile is not None
                        else []
                    ),
                )
            )

        for artifact in artifacts:
            artifact_statement = (
                f"A ready {artifact.artifact_type} proof artifact titled "
                f"{artifact.title} exists for the selected memory."
            )
            memory_id = str(artifact.source_memory_id)
            atoms.append(
                ApprovedEvidenceAtom(
                    evidence_atom_id=self._stable_contract_id(
                        "atom-artifact", str(artifact.id), artifact_statement
                    ),
                    canonical_memory_id=memory_id,
                    proof_artifact_id=str(artifact.id),
                    approved_claim_id=self._stable_contract_id(
                        "claim-artifact", str(artifact.id), artifact_statement
                    ),
                    support_type=EvidenceAtomSupportType.PROOF_ARTIFACT,
                    factual_statement=artifact_statement,
                    allowed_certainty=ClaimCertainty.OBSERVED,
                    prohibited_expansions=[
                        "Artifact availability does not add tools, metrics, or "
                        "outcomes."
                    ],
                )
            )

        if len(atoms) > 250:
            raise ApplicationPackageValidationError(
                "Selected evidence expands beyond the application-writer claim limit."
            )
        return atoms

    @staticmethod
    def _claim_certainty(value: str) -> ClaimCertainty:
        lowered = value.casefold()
        if any(
            token in lowered for token in ("exploratory", "explored", "investigated")
        ):
            return ClaimCertainty.EXPLORATORY
        if any(
            token in lowered
            for token in (
                "inconclusive",
                "no clear",
                "uncertain",
                "ambiguous",
                "qualitative",
                "without overstating",
            )
        ):
            return ClaimCertainty.QUALIFIED
        if any(token in lowered for token in ("resulted in", "led to", "drove")):
            return ClaimCertainty.CAUSAL
        return ClaimCertainty.OBSERVED

    @classmethod
    def _structured_outcome(
        cls,
        value: str,
        evidence_source_id: str,
    ) -> StructuredOutcome:
        rendered = " ".join(value.split()).strip().rstrip(".")
        action_pattern = re.compile(
            r"\b(?:improv\w*|increas\w*|reduc\w*|boost\w*|sav(?:ed|ing)|"
            r"earn\w*|won|achiev\w*|accelerat\w*|resulted\s+in|led\s+to|"
            r"drove|produced|helped|showed|found|reported|documented)\b",
            re.I,
        )
        match = action_pattern.search(rendered)
        if match is None:
            parts = rendered.split(maxsplit=1)
            action = parts[0] if parts else "reported"
            object_text = parts[1] if len(parts) > 1 else rendered
        else:
            action = match.group(0)
            object_text = rendered[match.end() :].strip(" :,-") or rendered
        metric_match = re.search(
            r"(?<!\w)(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
            r"(?:%|[kmbx])?(?!\w)",
            rendered,
            re.I,
        )
        qualifier = None
        lowered = rendered.casefold()
        if "no clear" in lowered:
            qualifier = "no clear result"
        elif "inconclusive" in lowered:
            qualifier = "inconclusive result"
        elif "qualitative" in lowered:
            qualifier = "qualitative result"
        return StructuredOutcome(
            evidence_source_id=evidence_source_id,
            action=action,
            object=object_text[:500],
            outcome=rendered[:1000],
            qualifier=qualifier,
            certainty=cls._claim_certainty(rendered),
            metric=metric_match.group(0) if metric_match else None,
        )

    @classmethod
    def _tools_explicit_in_text(
        cls,
        profile: CompiledCareerMemoryProfile,
        value: str,
    ) -> list[str]:
        return [
            tool
            for tool in cls._unique(
                [*profile.tools, *profile.skills_demonstrated, *profile.methods]
            )
            if cls._literal_in_text(tool, value)
        ][:50]

    @staticmethod
    def _literal_in_text(label: str, value: str) -> bool:
        normalized = " ".join(label.split()).strip()
        if not normalized:
            return False
        return bool(
            re.search(
                rf"(?<![A-Za-z0-9_]){re.escape(normalized)}(?![A-Za-z0-9_])",
                value,
                re.I,
            )
        )

    def _application_data_classification(
        self,
        session: Session,
        memory_ids: list[uuid.UUID],
    ) -> ApplicationWritingDataClassification:
        memories = session.scalars(
            select(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.user_id == self.user_id,
                CanonicalMemoryRecord.id.in_(memory_ids),
            )
        ).all()
        is_demo = bool(memories) and all(
            memory.structured_fields.get("demo_profile") is True for memory in memories
        )
        profile_names = self._unique(
            str(memory.structured_fields.get("demo_candidate_name") or "").strip()
            for memory in memories
            if memory.structured_fields.get("demo_candidate_name")
        )
        return ApplicationWritingDataClassification(
            profile_id=(
                str(memories[0].structured_fields.get("demo_profile_id"))
                if is_demo and memories[0].structured_fields.get("demo_profile_id")
                else str(self.user_id)
            ),
            profile_name=(profile_names[0] if profile_names else "CareerOS profile"),
            is_demo=is_demo,
            source=(
                ApplicationWritingDataSource.SEEDED_FICTIONAL
                if is_demo
                else ApplicationWritingDataSource.PERSONAL
            ),
        )

    def _local_writing_output(
        self,
        session: Session,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        warnings: list[ApplicationPackageWarning],
        unsupported_requirements: list[str],
        coverage: RequirementCoverage,
        writing_input: ApplicationWritingInput,
    ) -> ApplicationWritingOutput:
        outputs = self._compose_outputs(
            session,
            package,
            ranked,
            warnings,
            unsupported_requirements,
            writing_input.application_questions,
        )
        primary = ranked[0]
        provider_coverage: list[ProviderRequirementCoverageItem] = []
        for level, items in (
            (RequirementCoverageLevel.STRONGLY_SUPPORTED, coverage.strongly_supported),
            (
                RequirementCoverageLevel.PARTIALLY_SUPPORTED,
                coverage.partially_supported,
            ),
            (RequirementCoverageLevel.UNSUPPORTED, coverage.unsupported),
            (RequirementCoverageLevel.NOT_RELEVANT, coverage.not_relevant_enough),
        ):
            for item in items:
                refs = self._unique(
                    trace.trace_id
                    for ranked_item in ranked
                    if ranked_item.profile.memory_id in item.memory_ids
                    for trace in self._claim_trace_for_profile(ranked_item.profile)
                )
                provider_coverage.append(
                    ProviderRequirementCoverageItem(
                        requirement=item.requirement,
                        level=level,
                        explanation=(
                            item.evidence[0]
                            if item.evidence
                            else "No direct selected proof is currently available."
                        ),
                        evidence_reference_ids=refs[:30],
                    )
                )
        resume_groups = [
            ResumeBulletGroupOutput(
                memory_id=str(group.memory_id),
                heading=group.section_suggestion,
                bullets=[
                    ResumeBulletOutput(
                        text=bullet.bullet_text,
                        evidence_reference_ids=[
                            trace.trace_id
                            for trace in bullet.evidence_trace
                            if trace.support_type == EvidenceSupportType.DIRECT
                        ][:20],
                    )
                    for bullet in group.bullets
                ],
            )
            for group in outputs.resume_bullets
        ]
        cover = outputs.cover_letter
        cover_refs = self._unique(
            trace.trace_id
            for paragraph in cover.evidence_trace_by_paragraph
            for trace in paragraph.evidence_trace
            if trace.memory_id is not None
            and trace.support_type == EvidenceSupportType.DIRECT
        )
        fallback_answer_atom = next(
            atom
            for atom in writing_input.evidence_ledger
            if atom.canonical_memory_id == str(primary.profile.memory_id)
            and atom.support_type
            in {
                EvidenceAtomSupportType.DIRECT,
                EvidenceAtomSupportType.APPROVED_ENRICHMENT,
            }
        )
        snippets = [
            ApplicationSnippetOutput(
                question_id=snippet.question_id,
                answer=snippet.text,
                evidence_reference_ids=[
                    trace.trace_id
                    for trace in snippet.evidence_trace
                    if trace.memory_id is not None
                    and trace.support_type == EvidenceSupportType.DIRECT
                ][:20],
                evidence_atom_ids=[fallback_answer_atom.evidence_atom_id],
                tools_claimed=[],
                outcome_claimed=None,
                certainty=fallback_answer_atom.allowed_certainty,
            )
            for snippet in outputs.application_snippets
        ]
        used_refs = self._unique(
            [
                *(
                    ref
                    for group in resume_groups
                    for bullet in group.bullets
                    for ref in bullet.evidence_reference_ids
                ),
                *cover_refs,
                *(
                    ref
                    for snippet in snippets
                    for ref in snippet.evidence_reference_ids
                ),
            ]
        )
        memory_by_ref = {
            trace.trace_id: str(item.profile.memory_id)
            for item in ranked
            for trace in self._claim_trace_for_profile(item.profile)
        }
        primary_evidence = cover.body_paragraphs[0]
        secondary_evidence = (
            cover.body_paragraphs[1]
            if len(cover.body_paragraphs) > 1
            else cover.body_paragraphs[0]
        )
        cover_sections = CoverLetterSectionsOutput(
            opening=cover.opening_paragraph,
            primary_evidence=primary_evidence,
            secondary_evidence=secondary_evidence,
            closing=cover.closing_paragraph,
            full_text="\n\n".join(
                [
                    cover.opening_paragraph,
                    primary_evidence,
                    secondary_evidence,
                    cover.closing_paragraph,
                ]
            ),
            evidence_reference_ids=cover_refs[:40],
        )
        draft = ApplicationWritingOutput(
            job_understanding=self._job_understanding_output(package, coverage),
            requirement_coverage=provider_coverage,
            claim_plan=ClaimPlanOutput(
                primary_positioning=outputs.positioning_summary.primary_positioning,
                primary_proof_memory_id=str(primary.profile.memory_id),
                secondary_proof_memory_ids=[
                    str(item.profile.memory_id) for item in ranked[1:3]
                ],
                supported_requirements=[
                    item.requirement for item in coverage.strongly_supported
                ],
                partially_supported_requirements=[
                    item.requirement for item in coverage.partially_supported
                ],
                unsupported_requirements=[
                    item.requirement for item in coverage.unsupported
                ],
                claims_not_to_make=outputs.positioning_summary.do_not_claim,
                missing_evidence=outputs.positioning_summary.risks_and_gaps,
                resume_strategy="Use one evidence-backed idea per concise bullet.",
                cover_letter_strategy=(
                    "Connect the strongest two proof points in a natural narrative."
                ),
                snippet_strategy="Answer directly with one relevant example.",
                tone=writing_input.desired_tone,
            ),
            unsupported_requirements=[
                UnsupportedRequirementOutput(
                    requirement=item.requirement,
                    explanation=(
                        item.evidence[0]
                        if item.evidence
                        else "No direct selected proof is currently available."
                    ),
                    must_not_be_claimed=True,
                )
                for item in coverage.unsupported
            ],
            positioning_summary=outputs.positioning_summary.primary_positioning,
            resume_bullet_groups=resume_groups,
            cover_letter=cover_sections,
            application_snippets=snippets,
            reviewer_questions=outputs.reviewer_questions,
            evidence_references_used=[
                EvidenceReferenceUsed(
                    evidence_reference_id=reference,
                    memory_id=memory_by_ref[reference],
                    usage="Supports application-writing output.",
                )
                for reference in used_refs
                if reference in memory_by_ref
            ],
            unsupported_claim_candidates=[],
            strategy_notes=cover.strategy_notes,
            quality_review_notes=self._evaluate_output_quality(outputs).notes,
        )
        claims = self._local_candidate_claims(draft, writing_input, ranked)
        claim_by_path = {claim.field_path: claim for claim in claims}
        aligned_snippets = []
        for index, snippet in enumerate(draft.application_snippets):
            claim = claim_by_path[f"application_snippets.{index}.answer"]
            aligned_snippets.append(
                snippet.model_copy(
                    update={
                        "evidence_atom_ids": claim.evidence_atom_ids,
                        "tools_claimed": claim.tools_claimed,
                        "outcome_claimed": claim.outcome_claimed,
                        "certainty": claim.certainty,
                    }
                )
            )
        return draft.model_copy(
            update={
                "application_snippets": aligned_snippets,
                "candidate_claims": claims,
            }
        )

    def _local_candidate_claims(
        self,
        draft: ApplicationWritingOutput,
        writing_input: ApplicationWritingInput,
        ranked: list[_RankedProfile],
    ) -> list[CandidateFacingClaim]:
        """Attach one immutable claim contract to every local candidate surface."""

        claims: list[CandidateFacingClaim] = []
        primary_id = str(ranked[0].profile.memory_id)

        def add(
            field_path: str,
            text: str,
            claim_type: CandidateClaimType,
            memory_ids: Iterable[str],
            *,
            include_target: bool = False,
            strict_memory_scope: bool = False,
        ) -> None:
            atoms = self._local_claim_atoms(
                writing_input,
                text,
                set(memory_ids),
                include_target=include_target,
                strict_memory_scope=strict_memory_scope,
            )
            outcome_atom = self._matching_outcome_atom(text, atoms)
            if outcome_atom is not None and outcome_atom.supported_outcome is not None:
                certainty = outcome_atom.supported_outcome.certainty
            else:
                factual_atoms = [
                    atom
                    for atom in atoms
                    if atom.support_type
                    in {
                        EvidenceAtomSupportType.DIRECT,
                        EvidenceAtomSupportType.APPROVED_ENRICHMENT,
                        EvidenceAtomSupportType.PROOF_ARTIFACT,
                    }
                ]
                certainty_order = list(ClaimCertainty)
                certainty = (
                    min(
                        (atom.allowed_certainty for atom in factual_atoms),
                        key=certainty_order.index,
                    )
                    if factual_atoms
                    else ClaimCertainty.ASPIRATIONAL
                )
            claims.append(
                CandidateFacingClaim(
                    field_path=field_path,
                    claim_text=text,
                    evidence_atom_ids=[atom.evidence_atom_id for atom in atoms],
                    claim_type=claim_type,
                    tools_claimed=[
                        label
                        for label, pattern in _direct_proof_patterns(
                            writing_input.grouped_requirements.concrete_tools_requiring_direct_proof
                        ).items()
                        if pattern.search(
                            _mask_target_role_framing(
                                text,
                                writing_input.target_role,
                                atoms,
                                writing_input.company,
                            )
                        )
                    ],
                    outcome_claimed=(
                        outcome_atom.supported_outcome
                        if outcome_atom is not None
                        else None
                    ),
                    certainty=certainty,
                )
            )

        add(
            "positioning_summary",
            draft.positioning_summary,
            CandidateClaimType.POSITIONING,
            (primary_id,),
        )
        for group_index, group in enumerate(draft.resume_bullet_groups):
            for bullet_index, bullet in enumerate(group.bullets):
                add(
                    f"resume_bullet_groups.{group_index}.bullets.{bullet_index}.text",
                    bullet.text,
                    CandidateClaimType.RESUME_BULLET,
                    (group.memory_id,),
                    strict_memory_scope=True,
                )

        secondary_id = (
            str(ranked[1].profile.memory_id) if len(ranked) > 1 else primary_id
        )
        add(
            "cover_letter.opening",
            draft.cover_letter.opening,
            CandidateClaimType.COVER_LETTER,
            (primary_id,),
            include_target=True,
        )
        add(
            "cover_letter.primary_evidence",
            draft.cover_letter.primary_evidence,
            CandidateClaimType.COVER_LETTER,
            (primary_id,),
        )
        add(
            "cover_letter.secondary_evidence",
            draft.cover_letter.secondary_evidence,
            CandidateClaimType.COVER_LETTER,
            (secondary_id,),
        )
        add(
            "cover_letter.closing",
            draft.cover_letter.closing,
            CandidateClaimType.COVER_LETTER,
            (),
            include_target=True,
        )
        question_by_id = {
            question.question_id: question
            for question in writing_input.application_questions
        }
        for snippet_index, snippet in enumerate(draft.application_snippets):
            question = question_by_id[snippet.question_id]
            add(
                f"application_snippets.{snippet_index}.answer",
                snippet.answer,
                CandidateClaimType.APPLICATION_ANSWER,
                (primary_id,),
                include_target=self._is_motivation_question(question),
            )
        return claims

    def _local_claim_atoms(
        self,
        writing_input: ApplicationWritingInput,
        text: str,
        memory_ids: set[str],
        *,
        include_target: bool,
        strict_memory_scope: bool = False,
    ) -> list[ApprovedEvidenceAtom]:
        normalized_role = " ".join(writing_input.target_role.split()).strip()
        include_target = include_target or bool(
            not strict_memory_scope
            and normalized_role
            and re.search(re.escape(normalized_role), text, re.I)
        )
        eligible = [
            atom
            for atom in writing_input.evidence_ledger
            if (
                atom.canonical_memory_id in memory_ids
                or (
                    include_target
                    and atom.support_type is EvidenceAtomSupportType.TARGET_CONTEXT
                )
            )
        ]
        selected: list[ApprovedEvidenceAtom] = []
        if include_target:
            selected.extend(
                atom
                for atom in eligible
                if atom.support_type is EvidenceAtomSupportType.TARGET_CONTEXT
            )
        text_terms = self._contract_terms(text)
        for memory_id in sorted(memory_ids):
            candidates = [
                atom
                for atom in eligible
                if atom.canonical_memory_id == memory_id
                and atom.support_type
                in {
                    EvidenceAtomSupportType.DIRECT,
                    EvidenceAtomSupportType.APPROVED_ENRICHMENT,
                    EvidenceAtomSupportType.PROOF_ARTIFACT,
                }
                and atom.supported_outcome is None
            ]
            scored = sorted(
                (
                    (
                        len(self._contract_terms(atom.factual_statement) & text_terms),
                        atom,
                    )
                    for atom in candidates
                ),
                key=lambda item: (-item[0], item[1].evidence_atom_id),
            )
            matching = [atom for score, atom in scored if score >= 2]
            if not matching and scored:
                matching = [scored[0][1]]
            selected.extend(matching[:10])

        outcome_atom = self._matching_outcome_atom(text, eligible)
        if outcome_atom is not None:
            selected.append(outcome_atom)
        unique: list[ApprovedEvidenceAtom] = []
        seen: set[str] = set()
        for atom in selected:
            if atom.evidence_atom_id in seen:
                continue
            seen.add(atom.evidence_atom_id)
            unique.append(atom)
        if not unique:
            raise ApplicationPackageValidationError(
                "Local candidate text could not be linked to an evidence atom."
            )
        return unique[:20]

    @classmethod
    def _matching_outcome_atom(
        cls,
        text: str,
        atoms: Iterable[ApprovedEvidenceAtom],
    ) -> ApprovedEvidenceAtom | None:
        if not re.search(
            r"\b(?:improv\w*|increas\w*|reduc\w*|boost\w*|sav(?:ed|ing)|"
            r"earn\w*|won|achiev\w*|accelerat\w*|resulted\s+in|led\s+to|"
            r"drove|(?:i|we|analysis|study|research|results?|findings?|comparison|"
            r"model|evaluation)\s+(?:found|show(?:ed|n|s)?|observ(?:e|ed|es)|"
            r"report(?:ed|s)?)|impact\w*|perform(?:ance|ed|ing)?)\b",
            text,
            re.I,
        ):
            return None
        text_terms = cls._contract_terms(text)
        candidates = [atom for atom in atoms if atom.supported_outcome is not None]
        scored = sorted(
            (
                (
                    len(cls._contract_terms(atom.supported_outcome.object) & text_terms)
                    / max(len(cls._contract_terms(atom.supported_outcome.object)), 1),
                    atom,
                )
                for atom in candidates
                if atom.supported_outcome is not None
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        return scored[0][1] if scored and scored[0][0] >= 0.6 else None

    @staticmethod
    def _contract_terms(value: str) -> set[str]:
        stop = {"a", "an", "and", "for", "in", "of", "the", "to", "with"}
        return {
            token
            for token in re.findall(r"[a-z][a-z0-9+-]{1,}", value.casefold())
            if token not in stop
        }

    @staticmethod
    def _concrete_tools_in_text(value: str) -> list[str]:
        patterns = (
            ("python", r"\bpython\b"),
            ("sql", r"\bsql\b"),
            ("r", r"(?<![a-z])r(?![a-z])"),
            ("aws", r"\baws\b"),
            ("azure", r"\bazure\b"),
            ("gcp", r"\b(?:gcp|google cloud)\b"),
            ("kubernetes", r"\b(?:kubernetes|k8s)\b"),
            ("docker", r"\bdocker\b"),
            ("tableau", r"\btableau\b"),
            ("power bi", r"\bpower\s*bi\b"),
            (
                "production deployment",
                r"\b(?:production(?:-grade)?\s+)?deploy(?:ed|ing|ment|ments)?\b",
            ),
            ("model monitoring", r"\bmodel\s+monitor(?:ing|ed)?\b"),
            ("cloud infrastructure", r"\bcloud\s+infrastructure\b"),
        )
        return [label for label, pattern in patterns if re.search(pattern, value, re.I)]

    def _job_understanding_output(
        self,
        package: ApplicationPackage,
        coverage: RequirementCoverage,
    ) -> JobUnderstandingOutput:
        requested = [
            item.requirement
            for group in (
                coverage.strongly_supported,
                coverage.partially_supported,
                coverage.unsupported,
                coverage.not_relevant_enough,
            )
            for item in group
        ]
        concrete_names = {
            "python",
            "sql",
            "r",
            "java",
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "cloud infrastructure",
            "deployment",
            "production ml deployment",
            "llms",
            "rag",
            "agents",
            "tableau",
            "power bi",
        }
        concrete = [item for item in requested if item.casefold() in concrete_names]
        communication = [
            item
            for item in requested
            if any(
                token in item.casefold()
                for token in ("communication", "report", "presentation", "document")
            )
        ]
        central = (
            package.responsibilities[0]
            if package.responsibilities
            else (
                "Support the central responsibilities of the "
                f"{package.role_title} role."
            )
        )
        return JobUnderstandingOutput(
            role_family=self._role_family(package.role_title),
            seniority=self._role_seniority(package.role_title),
            central_objective=central,
            core_responsibilities=package.responsibilities[:20],
            must_have_requirements=package.required_skills[:30],
            preferred_requirements=package.preferred_skills[:30],
            technical_expectations=[
                item for item in requested if item not in communication
            ][:30],
            communication_expectations=communication[:20],
            concrete_tools_requiring_direct_proof=concrete[:30],
            broad_semantic_concepts=[
                item for item in requested if item.casefold() not in concrete_names
            ][:30],
        )

    def _materialize_provider_outputs(
        self,
        session: Session,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        warnings: list[ApplicationPackageWarning],
        coverage: RequirementCoverage,
        writing_output: ApplicationWritingOutput,
        writing_input: ApplicationWritingInput,
    ) -> ApplicationPackageOutputs:
        ranked_by_id = {str(item.profile.memory_id): item for item in ranked}
        trace_map = {
            trace.trace_id: trace
            for item in ranked
            for trace in self._claim_trace_for_profile(item.profile)
        }
        resume_groups: list[ResumeBulletGroup] = []
        for group in writing_output.resume_bullet_groups:
            ranked_item = ranked_by_id.get(group.memory_id)
            if ranked_item is None:
                self._raise_invalid_provider_draft(
                    "The writer referenced an unselected memory."
                )
            assert ranked_item is not None
            bullets: list[ResumeBullet] = []
            for bullet in group.bullets:
                traces = self._provider_traces(
                    bullet.evidence_reference_ids,
                    trace_map,
                    expected_memory_id=ranked_item.profile.memory_id,
                )
                bullets.append(
                    ResumeBullet(
                        # Preserve the exact candidate surface covered by the
                        # provider claim contract. Validation already enforces the
                        # text/metadata pairing before materialization.
                        bullet_text=bullet.text,
                        evidence_trace=traces,
                        confidence=ranked_item.profile.confidence,
                        warnings=[],
                        why_this_bullet=ranked_item.target_reason,
                    )
                )
            if bullets:
                resume_groups.append(
                    ResumeBulletGroup(
                        section_suggestion=self._section_suggestion(
                            ranked_item.profile.memory_type
                        ),
                        memory_id=ranked_item.profile.memory_id,
                        memory_title=ranked_item.profile.canonical_title,
                        target_reason=ranked_item.target_reason,
                        bullets=bullets,
                    )
                )

        primary = ranked_by_id.get(
            writing_output.claim_plan.primary_proof_memory_id,
            ranked[0],
        )
        secondary_items = [
            ranked_by_id[memory_id]
            for memory_id in writing_output.claim_plan.secondary_proof_memory_ids
            if memory_id in ranked_by_id
        ][:3]
        cover_traces = self._provider_traces(
            writing_output.cover_letter.evidence_reference_ids,
            trace_map,
        )
        primary_cover_traces = [
            trace
            for trace in cover_traces
            if trace.memory_id == primary.profile.memory_id
        ] or cover_traces
        secondary_memory_ids = {item.profile.memory_id for item in secondary_items}
        secondary_cover_traces = [
            trace for trace in cover_traces if trace.memory_id in secondary_memory_ids
        ] or primary_cover_traces
        target_trace = self._target_context_trace(package)
        greeting = (
            f"Dear {package.company} Hiring Team,"
            if package.company
            else "Dear Hiring Team,"
        )
        cover_sections = writing_output.cover_letter
        body = [cover_sections.primary_evidence]
        if (
            cover_sections.secondary_evidence.strip()
            and cover_sections.secondary_evidence.strip()
            != cover_sections.primary_evidence.strip()
        ):
            body.append(cover_sections.secondary_evidence)
        full_text = "\n\n".join(
            [
                greeting,
                cover_sections.opening,
                *body,
                cover_sections.closing,
            ]
        )
        cover_letter = CoverLetterDraft(
            subject_or_heading=f"Application for {package.role_title}",
            greeting=greeting,
            opening_paragraph=cover_sections.opening,
            body_paragraphs=body,
            closing_paragraph=cover_sections.closing,
            full_text=full_text,
            evidence_trace_by_paragraph=[
                CoverLetterParagraphTrace(
                    paragraph_label="opening",
                    paragraph_text=cover_sections.opening,
                    evidence_trace=[target_trace, *primary_cover_traces],
                ),
                *[
                    CoverLetterParagraphTrace(
                        paragraph_label=f"body_{index}",
                        paragraph_text=paragraph,
                        evidence_trace=(
                            primary_cover_traces
                            if index == 1
                            else secondary_cover_traces
                        ),
                    )
                    for index, paragraph in enumerate(body, start=1)
                ],
                CoverLetterParagraphTrace(
                    paragraph_label="closing",
                    paragraph_text=cover_sections.closing,
                    evidence_trace=[target_trace],
                ),
            ],
            warnings=[
                warning.message
                for warning in warnings
                if warning.severity != ApplicationWarningSeverity.INFO
            ][:5],
            strategy_notes=writing_output.strategy_notes,
        )
        question_by_id = {
            question.question_id: question
            for question in writing_input.application_questions
        }
        snippets = [
            ApplicationSnippet(
                question_id=snippet.question_id,
                question=question_by_id[snippet.question_id].question_text,
                text=snippet.answer,
                evidence_trace=self._provider_traces(
                    snippet.evidence_reference_ids,
                    trace_map,
                ),
                warnings=[],
            )
            for snippet in writing_output.application_snippets
        ]
        unsupported = self._unique(
            [
                *(
                    f"Unsupported target requirement: {item.requirement}"
                    for item in coverage.unsupported
                ),
                *(
                    f"{item.claim} — {item.reason}"
                    for item in writing_output.unsupported_claim_candidates
                ),
            ]
        )
        return ApplicationPackageOutputs(
            positioning_summary=PositioningSummary(
                primary_positioning=writing_output.positioning_summary,
                strongest_evidence=self._profile_evidence_summary(primary.profile),
                secondary_evidence=[
                    self._profile_evidence_summary(item.profile)
                    for item in secondary_items
                ],
                risks_and_gaps=self._unique(
                    [
                        *(warning.message for warning in warnings),
                        *writing_output.claim_plan.missing_evidence,
                    ]
                ),
                recommended_emphasis=self._unique(
                    [
                        *(item.requirement for item in coverage.strongly_supported),
                        *(item.requirement for item in coverage.partially_supported),
                    ]
                ),
                do_not_claim=self._unique(
                    [
                        *writing_output.claim_plan.claims_not_to_make,
                        *(
                            f"Do not claim unsupported {item.requirement}."
                            for item in coverage.unsupported
                        ),
                    ]
                ),
            ),
            resume_bullets=resume_groups,
            cover_letter=cover_letter,
            application_snippets=snippets,
            suggested_proof_artifacts=self._proof_suggestions(session, ranked[:3]),
            reviewer_questions=writing_output.reviewer_questions[:5],
            unsupported_claims=unsupported,
        )

    @staticmethod
    def _provider_traces(
        references: list[str],
        trace_map: dict[str, ApplicationEvidenceTrace],
        expected_memory_id: uuid.UUID | None = None,
    ) -> list[ApplicationEvidenceTrace]:
        traces: list[ApplicationEvidenceTrace] = []
        for reference in references:
            trace = trace_map.get(reference)
            if trace is None or (
                expected_memory_id is not None and trace.memory_id != expected_memory_id
            ):
                ApplicationPackageService._raise_invalid_provider_draft(
                    "The writer returned an invalid evidence reference."
                )
            assert trace is not None
            if trace.trace_id not in {item.trace_id for item in traces}:
                traces.append(trace)
        if not traces:
            ApplicationPackageService._raise_invalid_provider_draft(
                "Every factual writing surface must reference selected evidence."
            )
        return traces

    @staticmethod
    def _raise_invalid_provider_draft(message: str) -> None:
        raise ApplicationWritingMalformedOutputError(
            ApplicationWritingErrorCode.MALFORMED_OUTPUT,
            message,
        )

    def _validate_generated_outputs(
        self,
        outputs: ApplicationPackageOutputs,
        writing_output: ApplicationWritingOutput,
        writing_input: ApplicationWritingInput,
        profile_snapshots: list[dict[str, Any]],
        target_snapshot: dict[str, Any],
        warnings: list[ApplicationPackageWarning],
    ) -> None:
        validate_application_writing_output_contract(writing_input, writing_output)
        allowed_refs = {
            reference
            for memory in writing_input.selected_memories
            for reference in memory.evidence_reference_ids
        }
        selected_ids = {memory.memory_id for memory in writing_input.selected_memories}
        used_refs = {
            item.evidence_reference_id
            for item in writing_output.evidence_references_used
        }
        surface_refs = (
            {
                reference
                for group in writing_output.resume_bullet_groups
                for bullet in group.bullets
                for reference in bullet.evidence_reference_ids
            }
            | set(writing_output.cover_letter.evidence_reference_ids)
            | {
                reference
                for snippet in writing_output.application_snippets
                for reference in snippet.evidence_reference_ids
            }
        )
        evidence_memory = {
            item.evidence_reference_id: item.memory_id
            for item in writing_output.evidence_references_used
        }
        reference_owner = {
            reference: memory.memory_id
            for memory in writing_input.selected_memories
            for reference in memory.evidence_reference_ids
        }
        if (
            not used_refs
            or not surface_refs
            or not (used_refs | surface_refs).issubset(allowed_refs)
            or any(
                reference_owner.get(reference) != memory_id
                for reference, memory_id in evidence_memory.items()
            )
            or writing_output.claim_plan.primary_proof_memory_id not in selected_ids
            or not set(writing_output.claim_plan.secondary_proof_memory_ids).issubset(
                selected_ids
            )
        ):
            self._raise_invalid_provider_draft(
                "The writer returned evidence or memory references outside the "
                "selected proof."
            )
        if writing_output.unsupported_claim_candidates:
            self._raise_invalid_provider_draft(
                "The writer reported an unresolved unsupported claim; no version "
                "was saved."
            )
        if self._contains_mechanical_phrase(
            " ".join(
                [
                    outputs.positioning_summary.primary_positioning,
                    outputs.positioning_summary.strongest_evidence,
                    *outputs.positioning_summary.secondary_evidence,
                    outputs.cover_letter.full_text,
                    *(
                        bullet.bullet_text
                        for group in outputs.resume_bullets
                        for bullet in group.bullets
                    ),
                    *(snippet.text for snippet in outputs.application_snippets),
                ]
            )
        ):
            self._raise_invalid_provider_draft(
                "The writer returned mechanical source-field language; no version "
                "was saved."
            )

        ledger = self._claim_ledger(outputs)
        claim_ids = {item.claim_id for item in ledger}
        claims = self._edited_claims(
            outputs,
            claim_ids,
            [uuid.UUID(item) for item in selected_ids],
        )
        audited_claims = [
            _EditedClaim(
                claim_id=claim.claim_id,
                surface=claim.surface,
                text=self._mask_generated_target_labels(
                    claim.text,
                    target_snapshot,
                ),
                memory_ids=claim.memory_ids,
            )
            for claim in claims
        ]
        unsupported_numbers = self._unsupported_numbers_for_claims(
            audited_claims,
            profile_snapshots,
            target_snapshot,
        )
        unsupported_terms = self._unsupported_terms_for_claims(
            audited_claims,
            profile_snapshots,
            [warning.requirement for warning in warnings if warning.requirement],
        )
        cross_memory = self._cross_memory_terms_for_claims(
            audited_claims,
            profile_snapshots,
        )
        unsupported_outcomes = self._unsupported_outcomes_for_claims(
            audited_claims,
            profile_snapshots,
        )
        strategy_signal_leakage = self._strategy_signal_leakage_for_claims(
            audited_claims,
            profile_snapshots,
            writing_input,
        )
        if (
            unsupported_numbers
            or unsupported_terms
            or cross_memory
            or unsupported_outcomes
            or strategy_signal_leakage
        ):
            self._raise_invalid_provider_draft(
                "The generated draft introduced an unsupported claim and was not saved."
            )

    @staticmethod
    def _mask_generated_target_labels(
        value: str,
        target_snapshot: dict[str, Any],
    ) -> str:
        masked = value
        role_title = str(target_snapshot.get("role_title") or "").strip()
        if role_title:
            masked = re.sub(
                rf"(?<!\w){re.escape(role_title)}\s+"
                r"(?P<context>role|position|application|team)\b",
                lambda match: f"target {match.group('context')}",
                masked,
                flags=re.I,
            )
        company = str(target_snapshot.get("company") or "").strip()
        if company:
            masked = re.sub(
                rf"\b(?P<prefix>at|with|dear)\s+{re.escape(company)}\b",
                lambda match: f"{match.group('prefix')} target company",
                masked,
                flags=re.I,
            )
        return masked

    def _writing_intelligence(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        coverage: RequirementCoverage,
        writing_output: ApplicationWritingOutput,
        outputs: ApplicationPackageOutputs,
    ) -> ApplicationWritingIntelligence:
        job = writing_output.job_understanding
        plan = writing_output.claim_plan
        primary = next(
            (
                item
                for item in ranked
                if str(item.profile.memory_id) == plan.primary_proof_memory_id
            ),
            ranked[0],
        )
        secondary = [
            item
            for item in ranked
            if str(item.profile.memory_id) in plan.secondary_proof_memory_ids
        ]
        return ApplicationWritingIntelligence(
            job_understanding=ApplicationJobUnderstanding(
                role_family=job.role_family,
                seniority=job.seniority,
                central_objective=job.central_objective,
                core_responsibilities=job.core_responsibilities,
                must_have_requirements=job.must_have_requirements,
                preferred_requirements=job.preferred_requirements,
                technical_expectations=job.technical_expectations,
                communication_expectations=job.communication_expectations,
                concrete_tools_requiring_direct_proof=(
                    job.concrete_tools_requiring_direct_proof
                ),
                generic_concepts=job.broad_semantic_concepts,
            ),
            requirement_coverage=coverage,
            claim_plan=ApplicationClaimPlan(
                primary_positioning=plan.primary_positioning,
                primary_proof=self._profile_evidence_summary(primary.profile),
                secondary_proof=[
                    self._profile_evidence_summary(item.profile) for item in secondary
                ],
                supported_requirements=[
                    item.requirement for item in coverage.strongly_supported
                ],
                partially_supported_requirements=[
                    item.requirement for item in coverage.partially_supported
                ],
                unsupported_requirements=[
                    item.requirement for item in coverage.unsupported
                ],
                claims_not_to_make=plan.claims_not_to_make,
                missing_evidence=plan.missing_evidence,
                resume_strategy=plan.resume_strategy,
                cover_letter_narrative_strategy=plan.cover_letter_strategy,
                snippet_strategy=plan.snippet_strategy,
                tone=plan.tone,
            ),
            strategy_notes=self._unique(
                [
                    *writing_output.strategy_notes,
                    f"Selected {len(ranked)} of the strongest compiled memories for "
                    f"{package.role_title}.",
                    outputs.positioning_summary.primary_positioning,
                ]
            )[:10],
        )

    def _compose_outputs(
        self,
        session: Session,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        warnings: list[ApplicationPackageWarning],
        unsupported_requirements: list[str],
        application_questions: list[ApplicationQuestionInput],
    ) -> ApplicationPackageOutputs:
        resume_bullets: list[ResumeBulletGroup] = []
        for item in ranked[:4]:
            group = self._resume_group(item)
            if group.bullets:
                resume_bullets.append(group)
        cover_letter = self._cover_letter(package, ranked, warnings)
        positioning = self._positioning(
            package,
            ranked,
            warnings,
            unsupported_requirements,
        )
        snippets = self._snippets(
            package,
            ranked,
            warnings,
            application_questions,
        )
        suggestions = self._proof_suggestions(session, ranked[:3])
        reviewer_questions = self._reviewer_questions(
            package,
            ranked,
            unsupported_requirements,
        )
        unsupported_claims = self._unique(
            [
                *(
                    f"Unsupported target requirement: {item}"
                    for item in unsupported_requirements
                ),
                *(
                    warning
                    for item in ranked
                    for warning in item.profile.warnings_not_to_claim
                ),
            ]
        )
        return ApplicationPackageOutputs(
            positioning_summary=positioning,
            resume_bullets=resume_bullets,
            cover_letter=cover_letter,
            application_snippets=snippets,
            suggested_proof_artifacts=suggestions,
            reviewer_questions=reviewer_questions,
            unsupported_claims=unsupported_claims,
        )

    def _resume_group(self, ranked: _RankedProfile) -> ResumeBulletGroup:
        profile = ranked.profile
        trace = self._claim_trace_for_profile(profile)
        bullet_texts = self._derived_resume_bullets(profile)
        if len(bullet_texts) < 2:
            safe_compiled = [
                self._candidate_source_phrase(claim)
                for claim in self._profile_supported_values(
                    profile, profile.resume_bullet_claims
                )
                if 12 <= len(claim.split()) <= 38
                and not self._contains_mechanical_phrase(claim)
            ]
            bullet_texts = self._unique([*bullet_texts, *safe_compiled])[:2]
        bullets = [
            ResumeBullet(
                bullet_text=self._sentence(text),
                evidence_trace=trace,
                confidence=profile.confidence,
                warnings=[],
                why_this_bullet=ranked.target_reason,
            )
            for text in bullet_texts
            if text.strip()
        ]
        return ResumeBulletGroup(
            section_suggestion=self._section_suggestion(profile.memory_type),
            memory_id=profile.memory_id,
            memory_title=profile.canonical_title,
            target_reason=ranked.target_reason,
            bullets=bullets,
        )

    def _derived_resume_bullets(
        self,
        profile: CompiledCareerMemoryProfile,
    ) -> list[str]:
        if not self._profile_has_claim_support(profile):
            return []
        supported_capabilities = self._profile_supported_capabilities(profile)
        if profile.memory_type == "SKILL_SET" and supported_capabilities:
            skills = self._join(supported_capabilities[:4])
            return [f"Used {skills} in documented technical work"]

        bullets: list[str] = []
        supported_problems = self._profile_supported_values(
            profile, [profile.research_question_or_problem or ""]
        )
        supported_methods = self._profile_supported_values(profile, profile.methods)
        supported_inputs = self._profile_supported_values(
            profile, profile.data_or_inputs
        )
        supported_workflow = self._profile_supported_values(
            profile, profile.workflow_steps
        )
        supported_results = self._profile_supported_values(
            profile, profile.findings_or_results
        )
        problem = self._compact_phrase(
            self._problem_phrase(supported_problems[0] if supported_problems else None),
            7,
        )
        method = self._join(
            [self._compact_phrase(value, 3) for value in supported_methods[:2]]
        )
        data = (
            self._compact_phrase(supported_inputs[0], 5)
            if supported_inputs
            else ""
        )
        if method and data and problem:
            bullets.append(
                f"Analyzed {data} through {method} to address the documented goal "
                f"of {problem}, keeping the final interpretation grounded in evidence"
            )
        elif method and problem:
            bullets.append(
                f"Applied {method} to address the documented goal of {problem}, "
                "recording the choices that shaped the final interpretation"
            )
        elif supported_workflow and problem:
            step = self._compact_phrase(supported_workflow[0], 9)
            bullets.append(
                f"Built a project workflow around {step} to address the documented "
                f"goal of {problem} and connect the work to the final conclusion"
            )

        if supported_workflow:
            checks = self._join(
                [
                    self._gerund_action_phrase(self._compact_phrase(value, 5))
                    for value in supported_workflow[:2]
                ]
            )
            if supported_results:
                result = self._compact_phrase(
                    self._candidate_result_phrase(
                        supported_results[0],
                        supported_context=[
                            *supported_capabilities,
                            *supported_methods,
                        ],
                    ),
                    7,
                )
                bullets.append(
                    f"Validated the work by {checks}, then reported "
                    f"{self._lower_first(result)} without overstating the result"
                )
            else:
                bullets.append(
                    f"Validated the project workflow by {checks}, preserving quality "
                    "checks and limitations in the final interpretation"
                )
        return bullets

    def _cover_letter(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        warnings: list[ApplicationPackageWarning],
    ) -> CoverLetterDraft:
        primary = ranked[0]
        company_phrase = f" at {package.company}" if package.company else ""
        supported = self._supported_summary(primary.profile)
        if self._has_substantive_profile(primary.profile):
            if primary.profile.memory_type == "SKILL_SET":
                opening = (
                    f"I am applying for the {package.role_title} role{company_phrase}. "
                    "The selected record for "
                    f"{self._contextual_title(primary.profile.canonical_title)} "
                    "documents "
                    f"technical experience with {supported}."
                )
            else:
                if len(ranked) == 1:
                    subject = (
                        "This project"
                        if primary.profile.memory_type == "PROJECT"
                        else "This experience"
                    )
                else:
                    subject = (
                        "The selected projects"
                        if all(
                            item.profile.memory_type == "PROJECT" for item in ranked
                        )
                        else "The selected experiences"
                    )
                opening = (
                    f"I am applying for the {package.role_title} role{company_phrase}. "
                    f"{subject} required {supported}, along with "
                    "the discipline to test assumptions and explain what the evidence "
                    "does and does not show. That combination would let me contribute "
                    "thoughtfully while continuing to grow in the role."
                )
        else:
            opening = (
                f"I am applying for the {package.role_title} role{company_phrase}. "
                "The current record for "
                f"{self._contextual_title(primary.profile.canonical_title)} is too "
                "limited to support stronger method or result claims."
            )
        body_profiles = ranked[:2]
        body = [self._profile_narrative(item.profile) for item in body_profiles]
        if len(body) == 1 and self._has_substantive_profile(primary.profile):
            if primary.profile.memory_type == "SKILL_SET":
                body.append(
                    "The selected record for "
                    f"{self._contextual_title(primary.profile.canonical_title)} "
                    f"documents technical experience with {supported}."
                )
            else:
                methods = self._profile_supported_values(
                    primary.profile, primary.profile.methods
                )
                capabilities = self._profile_supported_capabilities(primary.profile)
                habit_anchor = (
                    methods[0]
                    if methods
                    else self._candidate_capability_phrase(capabilities[0])
                    if capabilities
                    else "the supported work"
                )
                body.append(
                    f"More broadly, working through {habit_anchor} reinforced the "
                    "habit of keeping the final interpretation grounded in evidence "
                    "and explaining the result without overstating it or extending "
                    "it beyond the evidence. I would bring the same measured "
                    "approach to the day-to-day "
                    f"responsibilities of the {package.role_title} role."
                )
        elif len(body) == 1:
            body.append(
                "I have limited this letter to the selected context and have not "
                "made specific capability, method, project, or result claims."
            )
        if self._has_substantive_profile(primary.profile):
            closing = (
                "I would welcome the opportunity to discuss the responsibilities of "
                "this role and consider how a careful, evidence-aware approach could "
                "contribute. Thank you for your time and consideration."
            )
        else:
            closing = "Thank you for considering my application."
        greeting = (
            f"Dear {package.company} Hiring Team,"
            if package.company
            else "Dear Hiring Team,"
        )
        full_text = "\n\n".join([greeting, opening, *body, closing])
        target_trace = self._target_context_trace(package)
        paragraph_trace = [
            CoverLetterParagraphTrace(
                paragraph_label="opening",
                paragraph_text=opening,
                evidence_trace=[
                    target_trace,
                    *self._claim_trace_for_profile(primary.profile),
                ],
            )
        ]
        paragraph_trace.extend(
            CoverLetterParagraphTrace(
                paragraph_label=f"body_{index}",
                paragraph_text=paragraph,
                evidence_trace=self._claim_trace_for_profile(item.profile),
            )
            for index, (item, paragraph) in enumerate(
                zip(body_profiles, body, strict=False), start=1
            )
        )
        if len(body) > len(body_profiles):
            paragraph_trace.append(
                CoverLetterParagraphTrace(
                    paragraph_label=f"body_{len(body)}",
                    paragraph_text=body[-1],
                    evidence_trace=self._claim_trace_for_profile(primary.profile),
                )
            )
        paragraph_trace.append(
            CoverLetterParagraphTrace(
                paragraph_label="closing",
                paragraph_text=closing,
                evidence_trace=[target_trace],
            )
        )
        strategy_notes = self._unique(
            f"Strategy signal only: {signal.guidance} ({signal.caveat})"
            for item in ranked
            for signal in item.profile.outcome_signals
        )
        return CoverLetterDraft(
            subject_or_heading=f"Application for {package.role_title}",
            greeting=greeting,
            opening_paragraph=opening,
            body_paragraphs=body,
            closing_paragraph=closing,
            full_text=full_text,
            evidence_trace_by_paragraph=paragraph_trace,
            warnings=[item.message for item in warnings],
            strategy_notes=strategy_notes,
        )

    def _profile_narrative(self, profile: CompiledCareerMemoryProfile) -> str:
        if not self._has_substantive_profile(profile):
            supported_inputs = self._profile_supported_values(
                profile, profile.data_or_inputs
            )
            if self._profile_has_claim_support(profile) and supported_inputs:
                return (
                    "The selected record for "
                    f"{self._contextual_title(profile.canonical_title)} is limited "
                    "context: its current source detail names "
                    f"{self._join(supported_inputs[:3])}, but does not support "
                    "specific capability, method, project, or result claims."
                )
            return (
                "The selected record for "
                f"{self._contextual_title(profile.canonical_title)} provides only "
                "limited "
                "context without direct source proof for specific capability, "
                "method, project, or result claims."
            )

        sentences: list[str] = []
        supported_problem = self._profile_supported_values(
            profile, [profile.research_question_or_problem or ""]
        )
        supported_capabilities = self._profile_supported_capabilities(profile)
        supported_methods = self._profile_supported_values(profile, profile.methods)
        supported_inputs = self._profile_supported_values(
            profile, profile.data_or_inputs
        )
        supported_results = self._profile_supported_values(
            profile, profile.findings_or_results
        )
        supported_limitations = self._profile_supported_values(
            profile, profile.limitations
        )
        if supported_problem:
            sentences.append(
                f"In {self._contextual_title(profile.canonical_title)}, I investigated "
                f"{self._problem_phrase(supported_problem[0])}"
            )
        elif profile.memory_type == "SKILL_SET" and supported_capabilities:
            sentences.append(
                "My technical experience includes "
                + self._join(supported_capabilities[:4])
            )
        elif supported_methods:
            sentences.append(
                f"In {self._contextual_title(profile.canonical_title)}, I used "
                f"{self._join(supported_methods[:2])}"
            )
        elif supported_inputs:
            sentences.append(
                f"My {profile.canonical_title} involved "
                f"{self._join(supported_inputs[:2])}"
            )
        if supported_methods:
            method = self._join(supported_methods[:2])
            if supported_inputs:
                sentences.append(
                    f"I built the workflow around {method} using "
                    f"{self._join(supported_inputs[:2])}, selecting only the "
                    "steps needed to answer the central question"
                )
            else:
                sentences.append(
                    f"I used {method} as the core of a focused analytical workflow"
                )
        if supported_results:
            source_result = supported_results[0]
            result = self._candidate_result_phrase(
                source_result,
                supported_context=[*supported_capabilities, *supported_methods],
            )
            if result:
                connector = (
                    "The analysis indicated "
                    if result != self._lower_first(source_result)
                    else "The analysis showed that "
                )
                sentences.append(connector + result)
        if supported_limitations:
            sentences.append(
                "I treated "
                + self._join(supported_limitations[:1])
                + " as a constraint on the conclusion and communicated it directly"
            )
        elif supported_capabilities and profile.memory_type != "SKILL_SET":
            capabilities = self._join(
                [
                    self._candidate_capability_phrase(value)
                    for value in supported_capabilities[:2]
                ]
            )
            sentences.append(
                "The project gave me experience with "
                + capabilities
                + " while keeping the final explanation accessible"
            )
        return " ".join(self._sentence(item) for item in sentences)

    def _positioning(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        warnings: list[ApplicationPackageWarning],
        unsupported_requirements: list[str],
    ) -> PositioningSummary:
        primary = ranked[0]
        primary_summary = self._supported_summary(primary.profile)
        if self._has_substantive_profile(primary.profile):
            primary_positioning = (
                f"Lead with {primary.profile.canonical_title} as the primary proof of "
                f"{primary_summary} for this {package.role_title} application."
            )
        else:
            primary_positioning = (
                f"Use {primary.profile.canonical_title} only as limited project "
                "context; the current record does not support a strong role-specific "
                "capability claim."
            )
        strongest = self._profile_evidence_summary(primary.profile)
        secondary = [
            self._profile_evidence_summary(item.profile) for item in ranked[1:3]
        ]
        gaps = self._unique(
            [
                *(item.message for item in warnings),
                *(
                    f"{item.profile.canonical_title}: {gap}"
                    for item in ranked[:3]
                    for gap in item.profile.missing_or_weak_sections
                ),
            ]
        )
        emphasis = self._unique(
            [
                primary.target_reason,
                *self._profile_supported_capabilities(primary.profile)[:4],
                *self._profile_supported_values(
                    primary.profile, primary.profile.methods
                )[:3],
            ]
        )
        do_not_claim = self._unique(
            [
                *(item.profile.warnings_not_to_claim for item in ranked[:3]),
                *(
                    f"Do not claim unsupported {item}."
                    for item in unsupported_requirements
                ),
            ]
        )
        return PositioningSummary(
            primary_positioning=primary_positioning,
            strongest_evidence=strongest,
            secondary_evidence=secondary,
            risks_and_gaps=gaps,
            recommended_emphasis=emphasis,
            do_not_claim=do_not_claim,
        )

    def _snippets(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        warnings: list[ApplicationPackageWarning],
        application_questions: list[ApplicationQuestionInput],
    ) -> list[ApplicationSnippet]:
        if not application_questions:
            return []

        primary = ranked[0]
        profile = primary.profile
        trace = self._claim_trace_for_profile(profile)
        target_trace = self._target_context_trace(package)
        bullet = self._resume_group(primary).bullets
        fit_text = (
            bullet[0].bullet_text if bullet else self._profile_evidence_summary(profile)
        )
        technical = self._supported_summary(profile)
        common_warnings = [
            item.message
            for item in warnings
            if item.severity != ApplicationWarningSeverity.INFO
        ][:2]
        snippets: list[ApplicationSnippet] = []
        for question in application_questions:
            if not question.required:
                continue
            lowered = f"{question.question_id} {question.question_text}".casefold()
            if self._is_motivation_question(question):
                answer = (
                    f"I am interested in the {package.role_title} role. A relevant "
                    "example is "
                    f"{self._contextual_title(profile.canonical_title)}, where I "
                    "practiced "
                    f"{technical}."
                )
                answer_trace = [target_trace, *trace]
            elif any(
                token in lowered
                for token in ("quality", "reliab", "validat", "accur", "check")
            ):
                answer = self._quality_reliability_answer(profile)
                answer_trace = trace
            elif any(
                token in lowered
                for token in ("project", "complex", "analy", "data", "example")
            ):
                answer = self._profile_narrative(profile)
                answer_trace = trace
            elif any(token in lowered for token in ("technical", "skill", "tool")):
                answer = (
                    f"I developed {technical} through "
                    f"{self._contextual_title(profile.canonical_title)}."
                )
                answer_trace = trace
            else:
                answer = (
                    f"In {self._contextual_title(profile.canonical_title)}, "
                    f"{self._lower_first(fit_text)}"
                )
                answer_trace = trace
            snippets.append(
                ApplicationSnippet(
                    question_id=question.question_id,
                    question=question.question_text,
                    text=self._fit_application_answer_length(
                        answer,
                        question.maximum_length,
                    ),
                    evidence_trace=answer_trace,
                    warnings=common_warnings,
                )
            )
        return snippets

    @staticmethod
    def _is_motivation_question(question: ApplicationQuestionInput) -> bool:
        rendered = f"{question.question_id} {question.question_text}".casefold()
        return any(
            token in rendered
            for token in ("motivation", "interested", "interest", "why this role")
        )

    def _quality_reliability_answer(
        self,
        profile: CompiledCareerMemoryProfile,
    ) -> str:
        limitations = self._profile_supported_values(profile, profile.limitations)
        workflow_steps = self._profile_supported_values(
            profile, profile.workflow_steps
        )
        methods = self._profile_supported_values(profile, profile.methods)
        if limitations:
            return (
                f"In {self._contextual_title(profile.canonical_title)}, I accounted "
                "for "
                f"{self._join(limitations[:2])} and kept that limitation "
                "visible in the interpretation."
            )
        if workflow_steps or methods:
            workflow = self._lower_first(
                self._join_action_steps((workflow_steps or methods)[:3])
            )
            return (
                f"In {self._contextual_title(profile.canonical_title)}, I {workflow}."
            )
        return self._profile_evidence_summary(profile)

    @staticmethod
    def _fit_application_answer_length(text: str, maximum_length: int | None) -> str:
        rendered = " ".join(text.split()).strip()
        if maximum_length is None or len(rendered) <= maximum_length:
            return rendered
        complete_sentences = re.findall(r"[^.!?]+[.!?]", rendered)
        retained = ""
        for sentence in complete_sentences:
            candidate = f"{retained} {sentence.strip()}".strip()
            if len(candidate) > maximum_length:
                break
            retained = candidate
        if retained:
            return retained
        shortened = rendered[: maximum_length - 1].rsplit(" ", 1)[0].rstrip(".,;: ")
        return f"{shortened}." if shortened else rendered[:maximum_length]

    def _proof_suggestions(
        self,
        session: Session,
        ranked: list[_RankedProfile],
    ) -> list[SuggestedProofArtifact]:
        suggestions: list[SuggestedProofArtifact] = []
        for item in ranked:
            ready_artifact = session.scalar(
                select(ProofArtifact)
                .where(
                    ProofArtifact.user_id == self.user_id,
                    ProofArtifact.source_memory_id == item.profile.memory_id,
                    ProofArtifact.status == "READY",
                )
                .order_by(ProofArtifact.updated_at.desc())
            )
            if ready_artifact is not None:
                suggestions.append(
                    SuggestedProofArtifact(
                        memory_id=item.profile.memory_id,
                        memory_title=item.profile.canonical_title,
                        artifact_id=ready_artifact.id,
                        artifact_title=ready_artifact.title,
                        action="ATTACH",
                        reason=(
                            "Attach this ready proof artifact because it documents the "
                            "selected project evidence used in the package."
                        ),
                    )
                )
                continue

            draft_artifact = session.scalar(
                select(ProofArtifact)
                .where(
                    ProofArtifact.user_id == self.user_id,
                    ProofArtifact.source_memory_id == item.profile.memory_id,
                    ProofArtifact.status != "ARCHIVED",
                )
                .order_by(ProofArtifact.updated_at.desc())
            )
            if draft_artifact is not None:
                suggestions.append(
                    SuggestedProofArtifact(
                        memory_id=item.profile.memory_id,
                        memory_title=item.profile.canonical_title,
                        artifact_id=draft_artifact.id,
                        artifact_title=draft_artifact.title,
                        action="REVIEW",
                        reason=(
                            "Finish reviewing this existing draft before treating it "
                            "as an application attachment."
                        ),
                    )
                )
            else:
                suggestions.append(
                    SuggestedProofArtifact(
                        memory_id=item.profile.memory_id,
                        memory_title=item.profile.canonical_title,
                        artifact_title=f"{item.profile.canonical_title} proof artifact",
                        action="BUILD",
                        reason=(
                            "Build a short case study from this selected project for "
                            "an optional portfolio or application upload."
                        ),
                    )
                )
        return suggestions

    def _reviewer_questions(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        unsupported_requirements: list[str],
    ) -> list[str]:
        questions: list[str] = []
        for item in ranked[:2]:
            shortcut_supported = self._has_project_shortcut_evidence(item.profile)
            if shortcut_supported and item.profile.project_kind == "GAS_KINEMATICS":
                questions.append(
                    "Is it clear in the first 30 seconds that Gas Kinematics "
                    f"demonstrates {self._supported_summary(item.profile)}?"
                )
            elif shortcut_supported and item.profile.project_kind == "UNICORN":
                questions.append(
                    "Is it clear in the first 30 seconds that UNICORN demonstrates "
                    f"{self._supported_summary(item.profile)}?"
                )
            elif item.profile.missing_or_weak_sections:
                questions.append(
                    f"Can you add supporting evidence for "
                    f"{item.profile.missing_or_weak_sections[0].lower()} in "
                    f"{item.profile.canonical_title}?"
                )
        questions.extend(
            f"Do you have reviewable evidence for {item}, or should it stay out of "
            f"this {package.role_title} package?"
            for item in unsupported_requirements[:3]
        )
        return self._unique(questions)[:5]

    def _warnings(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
    ) -> tuple[list[ApplicationPackageWarning], list[str]]:
        coverage = self._requirement_coverage(package, ranked)
        unsupported = [item.requirement for item in coverage.unsupported]
        warnings: list[ApplicationPackageWarning] = []
        for requirement in unsupported:
            if requirement == "production ML deployment":
                message = (
                    "The job asks for production ML deployment, but the selected "
                    "proof does not currently support deployment."
                )
            elif requirement in {"AWS", "Azure", "GCP", "cloud infrastructure"}:
                message = (
                    f"The job asks for {requirement}, but the selected proof does not "
                    "currently support that cloud experience."
                )
            else:
                message = (
                    f"The target asks for {requirement}, but the selected proof does "
                    "not currently support that claim."
                )
            warnings.append(
                ApplicationPackageWarning(
                    code="UNSUPPORTED_TARGET_REQUIREMENT",
                    message=message,
                    severity=ApplicationWarningSeverity.CAUTION,
                    requirement=requirement,
                    memory_ids=[item.profile.memory_id for item in ranked],
                )
            )
        for item in ranked:
            if not self._has_substantive_profile(item.profile):
                warnings.append(
                    ApplicationPackageWarning(
                        code="SPARSE_APPROVED_MEMORY",
                        message=(
                            f"{item.profile.canonical_title} has limited supporting "
                            "method, skill, and result detail. Stronger capability "
                            "claims stay out of this draft."
                        ),
                        severity=ApplicationWarningSeverity.CAUTION,
                        memory_ids=[item.profile.memory_id],
                    )
                )
            if not self._has_quantified_result(item.profile):
                warnings.append(
                    ApplicationPackageWarning(
                        code="NO_QUANTIFIED_OUTCOME",
                        message=(
                            f"No quantified outcome is currently supported for "
                            f"{item.profile.canonical_title}."
                        ),
                        severity=ApplicationWarningSeverity.INFO,
                        memory_ids=[item.profile.memory_id],
                    )
                )
            for message in item.profile.warnings_not_to_claim:
                warnings.append(
                    ApplicationPackageWarning(
                        code="MEMORY_CLAIM_BOUNDARY",
                        message=f"{item.profile.canonical_title}: {message}",
                        severity=ApplicationWarningSeverity.CAUTION,
                        memory_ids=[item.profile.memory_id],
                    )
                )
            if item.profile.outcome_signals:
                warnings.append(
                    ApplicationPackageWarning(
                        code="STRATEGY_SIGNAL_NOT_PROOF",
                        message=(
                            "Outcome feedback may guide emphasis, but it is a strategy "
                            "signal only and is not proof of the underlying skill."
                        ),
                        severity=ApplicationWarningSeverity.INFO,
                        memory_ids=[item.profile.memory_id],
                    )
                )
        return self._dedupe_warnings(warnings), self._unique(unsupported)

    def _requirement_coverage(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
    ) -> RequirementCoverage:
        requirements = self._requested_requirements(package)
        explicit = {
            item.casefold()
            for item in [*package.required_skills, *package.preferred_skills]
        }
        direct_proof = {
            "python",
            "sql",
            "r",
            "java",
            "aws",
            "azure",
            "gcp",
            "docker",
            "kubernetes",
            "cloud infrastructure",
            "deployment",
            "production ml deployment",
            "llms",
            "rag",
            "agents",
            "tableau",
            "power bi",
            "excel",
        }
        partial_patterns: dict[str, tuple[str, ...]] = {
            "data analysis": ("analysis", "analytical", "research", "statistics"),
            "modeling": ("fit", "uncertainty", "validation", "statistical"),
            "statistics": ("analysis", "measurement", "uncertainty"),
            "technical communication": (
                "documentation",
                "report",
                "presentation",
                "explain",
                "communicat",
            ),
            "data quality": ("inspection", "review", "validation", "categor"),
            "research problem solving": (
                "research",
                "hypothesis",
                "debug",
                "uncertainty",
                "experiment",
            ),
        }
        strongly: list[RequirementCoverageItem] = []
        partially: list[RequirementCoverageItem] = []
        unsupported: list[RequirementCoverageItem] = []
        not_relevant: list[RequirementCoverageItem] = []
        for label, patterns in requirements:
            supporting = [
                item
                for item in ranked
                if self._profile_has_claim_support(item.profile)
                and self._patterns_supported(
                    self._profile_capability_text(item.profile), patterns
                )
            ]
            if supporting:
                strongly.append(
                    RequirementCoverageItem(
                        requirement=label,
                        evidence=[
                            f"{item.profile.canonical_title}: "
                            f"{self._supported_summary(item.profile)}"
                            for item in supporting[:3]
                        ],
                        memory_ids=[item.profile.memory_id for item in supporting[:3]],
                    )
                )
                continue
            related = [
                item
                for item in ranked
                if any(
                    token in self._profile_relevance_text(item.profile).casefold()
                    for token in partial_patterns.get(label.casefold(), ())
                )
            ]
            coverage_item = RequirementCoverageItem(
                requirement=label,
                evidence=[
                    f"{item.profile.canonical_title}: related but indirect proof"
                    for item in related[:2]
                ],
                memory_ids=[item.profile.memory_id for item in related[:2]],
            )
            if related and label.casefold() not in direct_proof:
                partially.append(coverage_item)
            elif label.casefold() in explicit or label.casefold() in direct_proof:
                unsupported.append(coverage_item)
            else:
                not_relevant.append(coverage_item)
        return RequirementCoverage(
            strongly_supported=strongly,
            partially_supported=partially,
            unsupported=unsupported,
            not_relevant_enough=not_relevant,
        )

    def _requested_requirements(
        self,
        package: ApplicationPackage,
    ) -> list[tuple[str, tuple[str, ...]]]:
        description = " ".join(
            [
                package.target_description,
                *package.required_skills,
                *package.preferred_skills,
                *package.responsibilities,
            ]
        )
        explicit = [*package.required_skills, *package.preferred_skills]
        found: list[tuple[str, tuple[str, ...]]] = []
        for label, target_patterns, support_patterns in self._requirement_rules:
            if any(
                re.search(pattern, description, re.I) for pattern in target_patterns
            ):
                if label == "deployment" and any(
                    existing_label == "production ML deployment"
                    for existing_label, _ in found
                ):
                    continue
                found.append((label, support_patterns))
        for value in explicit:
            if any(value.casefold() == label.casefold() for label, _ in found):
                continue
            found.append((value, (self._literal_pattern(value),)))
        return found

    def _aggregate_evidence_trace(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
    ) -> list[ApplicationEvidenceTrace]:
        entries = [self._target_context_trace(package)]
        for item in ranked:
            entries.extend(self._all_profile_trace(item.profile))
            entries.append(self._framing_trace(item.profile))
        unique: list[ApplicationEvidenceTrace] = []
        seen: set[str] = set()
        for entry in entries:
            if entry.trace_id in seen:
                continue
            seen.add(entry.trace_id)
            unique.append(entry)
        return unique

    def _all_profile_trace(
        self,
        profile: CompiledCareerMemoryProfile,
    ) -> list[ApplicationEvidenceTrace]:
        entries: list[ApplicationEvidenceTrace] = []
        enrichment_ids = {str(item) for item in profile.enrichment_ids_used}
        for evidence in profile.evidence_used:
            is_enrichment = evidence.kind == CompiledEvidenceKind.APPROVED_ENRICHMENT
            enrichment_id = (
                uuid.UUID(evidence.evidence_id)
                if is_enrichment and evidence.evidence_id in enrichment_ids
                else None
            )
            source_type = (
                EvidenceSourceType.APPROVED_ENRICHMENT
                if is_enrichment
                else EvidenceSourceType.APPROVED_MEMORY
            )
            detail = evidence.excerpt or "Approved source reference."
            label = (
                f"{profile.canonical_title} — approved enrichment: "
                f"{evidence.source_label}"
                if is_enrichment
                else (
                    f"{profile.canonical_title} — approved memory: "
                    f"{evidence.source_label}"
                )
            )
            entries.append(
                ApplicationEvidenceTrace(
                    trace_id=self._stable_contract_id(
                        "trace",
                        str(profile.memory_id),
                        evidence.kind.value,
                        evidence.evidence_id,
                    ),
                    source_type=source_type,
                    support_type=EvidenceSupportType.DIRECT,
                    source_label=label,
                    detail=detail,
                    memory_id=profile.memory_id,
                    memory_title=profile.canonical_title,
                    evidence_id=(
                        evidence.evidence_id
                        if evidence.kind != CompiledEvidenceKind.CANONICAL_MEMORY
                        and enrichment_id is None
                        else None
                    ),
                    enrichment_id=enrichment_id,
                )
            )
        for signal in profile.outcome_signals:
            entries.append(
                ApplicationEvidenceTrace(
                    trace_id=f"strategy-{signal.feedback_event_id}",
                    source_type=EvidenceSourceType.STRATEGY_SIGNAL,
                    support_type=EvidenceSupportType.STRATEGY_ONLY,
                    source_label=(
                        f"{profile.canonical_title} — approved outcome feedback"
                    ),
                    detail=f"{signal.summary} Strategy guidance: {signal.guidance}",
                    memory_id=profile.memory_id,
                    memory_title=profile.canonical_title,
                    outcome_signal_id=signal.feedback_event_id,
                    caveat=signal.caveat,
                )
            )
        return entries

    def _factual_trace_for_profile(
        self,
        profile: CompiledCareerMemoryProfile,
    ) -> list[ApplicationEvidenceTrace]:
        return [
            item
            for item in self._all_profile_trace(profile)
            if item.support_type == EvidenceSupportType.DIRECT
        ]

    def _claim_trace_for_profile(
        self,
        profile: CompiledCareerMemoryProfile,
    ) -> list[ApplicationEvidenceTrace]:
        return [*self._factual_trace_for_profile(profile), self._framing_trace(profile)]

    @staticmethod
    def _framing_trace(
        profile: CompiledCareerMemoryProfile,
    ) -> ApplicationEvidenceTrace:
        return ApplicationEvidenceTrace(
            trace_id=f"framing-{profile.memory_id}",
            source_type=EvidenceSourceType.APPROVED_MEMORY,
            support_type=EvidenceSupportType.INFERRED_FRAMING,
            source_label=f"{profile.canonical_title} — role-aware framing",
            detail=(
                "CareerOS reframed approved claim ingredients for relevance. This "
                "trace does not introduce a new tool, metric, result, or experience."
            ),
            memory_id=profile.memory_id,
            memory_title=profile.canonical_title,
            caveat="Inferred framing backed by direct approved proof.",
        )

    def _target_context_trace(
        self,
        package: ApplicationPackage,
    ) -> ApplicationEvidenceTrace:
        company = f" at {package.company}" if package.company else ""
        return ApplicationEvidenceTrace(
            trace_id=f"target-{package.id}",
            source_type=EvidenceSourceType.TARGET_CONTEXT,
            support_type=EvidenceSupportType.RELEVANCE_ONLY,
            source_label=f"Target role: {package.role_title}{company}",
            detail=(
                "The target description and requirements influence relevance and "
                "emphasis only; they do not support factual career claims."
            ),
            caveat="Target context is relevance, not proof.",
        )

    def _claim_ledger(
        self,
        outputs: ApplicationPackageOutputs,
        *,
        edited_claim_ids: set[str] | None = None,
        candidate_claims: list[CandidateFacingClaim] | None = None,
    ) -> list[ApplicationClaimLedgerEntry]:
        edited_claim_ids = edited_claim_ids or set()
        provider_claims = {
            claim.field_path: claim for claim in (candidate_claims or [])
        }
        entries: list[ApplicationClaimLedgerEntry] = []
        positioning_traces = [
            trace
            for paragraph in outputs.cover_letter.evidence_trace_by_paragraph
            if paragraph.paragraph_label == "opening"
            for trace in paragraph.evidence_trace
        ]
        if not positioning_traces:
            positioning_traces = [
                trace
                for group in outputs.resume_bullets[:1]
                for bullet in group.bullets[:1]
                for trace in bullet.evidence_trace
            ]
        entries.append(
            self._ledger_entry(
                "positioning-summary",
                "positioning",
                outputs.positioning_summary.primary_positioning,
                positioning_traces,
                outputs.positioning_summary.risks_and_gaps,
                user_edited="positioning-summary" in edited_claim_ids,
                candidate_claim=provider_claims.get("positioning_summary"),
            )
        )
        entries.append(
            self._ledger_entry(
                "positioning-evidence",
                "positioning",
                outputs.positioning_summary.strongest_evidence,
                positioning_traces,
                outputs.positioning_summary.risks_and_gaps,
                user_edited="positioning-evidence" in edited_claim_ids,
            )
        )
        for group_index, group in enumerate(outputs.resume_bullets, start=1):
            for bullet_index, bullet in enumerate(group.bullets, start=1):
                field_path = (
                    f"resume_bullet_groups.{group_index - 1}.bullets."
                    f"{bullet_index - 1}.text"
                )
                entries.append(
                    self._ledger_entry(
                        f"resume-{group_index}-{bullet_index}",
                        "resume",
                        bullet.bullet_text,
                        bullet.evidence_trace,
                        bullet.warnings,
                        user_edited=(
                            f"resume-{group_index}-{bullet_index}" in edited_claim_ids
                        ),
                        candidate_claim=provider_claims.get(field_path),
                    )
                )
        cover_traces = [
            trace
            for paragraph in outputs.cover_letter.evidence_trace_by_paragraph
            for trace in paragraph.evidence_trace
        ]
        entries.append(
            self._ledger_entry(
                "cover-letter-full",
                "cover_letter",
                outputs.cover_letter.full_text,
                cover_traces,
                outputs.cover_letter.warnings,
                user_edited="cover-letter-full" in edited_claim_ids,
            )
        )
        for index, paragraph in enumerate(
            outputs.cover_letter.evidence_trace_by_paragraph,
            start=1,
        ):
            cover_field_path = {
                "opening": "cover_letter.opening",
                "body_1": "cover_letter.primary_evidence",
                "body_2": "cover_letter.secondary_evidence",
                "closing": "cover_letter.closing",
            }.get(paragraph.paragraph_label)
            entries.append(
                self._ledger_entry(
                    f"cover-letter-{index}",
                    "cover_letter",
                    paragraph.paragraph_text,
                    paragraph.evidence_trace,
                    outputs.cover_letter.warnings,
                    user_edited=(f"cover-letter-{index}" in edited_claim_ids),
                    candidate_claim=(
                        provider_claims.get(cover_field_path)
                        if cover_field_path is not None
                        else None
                    ),
                )
            )
        for index, snippet in enumerate(outputs.application_snippets, start=1):
            claim_id = f"snippet-{snippet.question_id or index}"
            entries.append(
                self._ledger_entry(
                    claim_id,
                    "snippet",
                    snippet.text,
                    snippet.evidence_trace,
                    snippet.warnings,
                    user_edited=claim_id in edited_claim_ids,
                    candidate_claim=provider_claims.get(
                        f"application_snippets.{index - 1}.answer"
                    ),
                )
            )
        return entries

    def _ledger_entry(
        self,
        claim_id: str,
        surface: str,
        text: str,
        traces: list[ApplicationEvidenceTrace],
        warnings: list[str],
        *,
        user_edited: bool = False,
        candidate_claim: CandidateFacingClaim | None = None,
    ) -> ApplicationClaimLedgerEntry:
        factual = [
            item for item in traces if item.support_type == EvidenceSupportType.DIRECT
        ]
        strategy = [
            item
            for item in traces
            if item.support_type == EvidenceSupportType.STRATEGY_ONLY
        ]
        memory_ids = self._unique_uuid(
            item.memory_id for item in factual if item.memory_id is not None
        )
        evidence_ids = self._unique(
            item.evidence_id for item in factual if item.evidence_id is not None
        )
        enrichment_ids = self._unique_uuid(
            item.enrichment_id for item in factual if item.enrichment_id is not None
        )
        strategy_ids = self._unique_uuid(
            item.outcome_signal_id
            for item in strategy
            if item.outcome_signal_id is not None
        )
        support_level = "strong" if factual and not warnings else "partial"
        if not factual:
            support_level = "context_only"
        if user_edited:
            memory_ids = []
            evidence_ids = []
            enrichment_ids = []
            strategy_ids = []
            support_level = "user_review_required"
            warnings = self._unique(
                [
                    *warnings,
                    "User-edited wording is not certified by the preserved trace; "
                    "review it against approved proof.",
                ]
            )
        return ApplicationClaimLedgerEntry(
            claim_id=claim_id,
            surface=surface,
            text=text,
            memory_ids=memory_ids,
            evidence_ids=evidence_ids,
            enrichment_ids=enrichment_ids,
            support_level=support_level,
            warnings=warnings,
            user_edited=user_edited,
            strategy_signal_ids=strategy_ids,
            strategy_signal_caveat=(
                "Strategy signal, not proof of causality." if strategy_ids else None
            ),
            evidence_atom_ids=(
                candidate_claim.evidence_atom_ids if candidate_claim is not None else []
            ),
            claim_type=(
                candidate_claim.claim_type.value
                if candidate_claim is not None
                else None
            ),
            tools_claimed=(
                candidate_claim.tools_claimed if candidate_claim is not None else []
            ),
            outcome_claimed=(
                candidate_claim.outcome_claimed.model_dump(mode="json")
                if candidate_claim is not None
                and candidate_claim.outcome_claimed is not None
                else None
            ),
            certainty=(
                candidate_claim.certainty.value if candidate_claim is not None else None
            ),
        )

    def _rank_profile(
        self,
        profile: CompiledCareerMemoryProfile,
        target_text: str,
    ) -> _RankedProfile:
        target_terms = self._terms(target_text)
        factual = self._profile_relevance_text(profile)
        factual_terms = self._terms(factual)
        overlap = len(target_terms & factual_terms) / max(len(target_terms), 1)
        target_rules = [
            support_patterns
            for _, target_patterns, support_patterns in self._requirement_rules
            if any(re.search(pattern, target_text, re.I) for pattern in target_patterns)
        ]
        semantic_overlap = (
            sum(
                self._patterns_supported(factual, support_patterns)
                for support_patterns in target_rules
            )
            / len(target_rules)
            if target_rules
            else 0.0
        )
        specificity = min(
            (
                len(profile.methods)
                + len(profile.tools)
                + len(profile.workflow_steps)
                + len(profile.findings_or_results)
                + len(profile.proof_claims)
            )
            / 12,
            1.0,
        )
        evidence_breadth = min(len(profile.evidence_used) / 4, 1.0)
        target_lower = target_text.casefold()
        bonus = 0.0
        title_match_bonus = (
            0.35
            if profile.canonical_title.casefold() in target_lower
            and len(profile.canonical_title.strip()) >= 8
            else 0.0
        )
        shortcut_supported = self._has_project_shortcut_evidence(profile)
        if (
            shortcut_supported
            and profile.project_kind == "GAS_KINEMATICS"
            and any(
                value in target_lower
                for value in (
                    "data science",
                    "data scientist",
                    "data analyst",
                    "analytics",
                    "modeling",
                    "uncertainty",
                )
            )
        ):
            bonus = 0.2
        elif (
            shortcut_supported
            and profile.project_kind == "UNICORN"
            and any(
                value in target_lower
                for value in (
                    "ai engineer",
                    "data quality",
                    "image",
                    "labeling",
                    "human-in-the-loop",
                )
            )
        ):
            bonus = 0.2
        score = round(
            min(
                overlap * 0.3
                + semantic_overlap * 0.3
                + profile.confidence * 0.15
                + specificity * 0.15
                + evidence_breadth * 0.1
                + bonus
                + title_match_bonus,
                1,
            ),
            3,
        )
        supported = self._supported_summary(profile)
        if bonus:
            reason = (
                f"{profile.canonical_title} is a strong role match because it "
                f"demonstrates {supported}."
            )
        elif overlap:
            reason = (
                f"{profile.canonical_title} overlaps with the target through "
                f"{supported}."
            )
        else:
            reason = (
                f"{profile.canonical_title} supplies supporting project context, "
                "though its target overlap is limited."
            )
        return _RankedProfile(profile=profile, score=score, target_reason=reason)

    def _supported_summary(self, profile: CompiledCareerMemoryProfile) -> str:
        if not self._profile_has_claim_support(profile):
            return "limited memory context without direct source proof"
        values = self._unique(
            [
                *self._profile_supported_capabilities(profile)[:4],
                *self._profile_supported_values(profile, profile.methods)[:4],
            ]
        )
        if values:
            return self._join(
                [self._candidate_capability_phrase(value) for value in values[:5]]
            )
        return "limited project context"

    @classmethod
    def _has_substantive_profile(cls, profile: CompiledCareerMemoryProfile) -> bool:
        return bool(
            cls._profile_has_claim_support(profile)
            and (
                cls._profile_supported_capabilities(profile)
                or cls._profile_supported_values(profile, profile.methods)
                or cls._profile_supported_values(profile, profile.workflow_steps)
                or cls._profile_supported_values(
                    profile, profile.resume_bullet_claims
                )
            )
        )

    @staticmethod
    def _profile_has_claim_support(profile: CompiledCareerMemoryProfile) -> bool:
        """Return whether the profile has any approved factual claim support."""

        return any(
            item.kind
            in {
                CompiledEvidenceKind.CANONICAL_EVIDENCE,
                CompiledEvidenceKind.APPROVED_ENRICHMENT,
            }
            for item in profile.evidence_used
        )

    @staticmethod
    def _profile_claim_support_excerpts(
        profile: CompiledCareerMemoryProfile,
    ) -> list[str]:
        return [
            " ".join((item.excerpt or "").split()).strip()
            for item in profile.evidence_used
            if item.kind
            in {
                CompiledEvidenceKind.CANONICAL_EVIDENCE,
                CompiledEvidenceKind.APPROVED_ENRICHMENT,
            }
            and (item.excerpt or "").strip()
        ]

    @classmethod
    def _profile_value_has_claim_support(
        cls,
        profile: CompiledCareerMemoryProfile,
        value: str,
    ) -> bool:
        """Require each exposed profile value to match approved source material."""

        rendered = " ".join(value.split()).strip().rstrip(".")
        if not rendered:
            return False
        candidate_values = cls._unique(
            [rendered, cls._candidate_result_phrase(rendered)]
        )
        excerpts = cls._profile_claim_support_excerpts(profile)
        if any(
            re.search(cls._literal_pattern(candidate), excerpt, re.I)
            for candidate in candidate_values
            for excerpt in excerpts
            if candidate
        ):
            return True

        candidate_terms = cls._profile_support_terms(candidate_values[-1])
        if not candidate_terms:
            return False
        support_terms = cls._profile_support_terms(" ".join(excerpts))
        overlap = candidate_terms & support_terms
        return len(overlap) >= 2 and len(overlap) / len(candidate_terms) >= 0.6

    @classmethod
    def _profile_support_terms(cls, value: str) -> set[str]:
        aliases = {
            "categorization": "categorize",
            "categorized": "categorize",
            "categorizing": "categorize",
            "inspection": "inspect",
            "inspected": "inspect",
            "inspecting": "inspect",
            "manually": "manual",
            "organization": "organize",
            "organized": "organize",
            "organizing": "organize",
            "reviewed": "review",
            "reviewing": "review",
        }
        normalized: set[str] = set()
        for token in cls._terms(value.replace("-", " ")):
            rendered = aliases.get(token, token)
            if rendered == token and len(token) > 4:
                if token.endswith("ies"):
                    rendered = f"{token[:-3]}y"
                elif token.endswith("ing"):
                    rendered = token[:-3]
                elif token.endswith("ed"):
                    rendered = token[:-2]
                elif token.endswith("s"):
                    rendered = token[:-1]
            normalized.add(rendered)
        return normalized

    @classmethod
    def _profile_supported_values(
        cls,
        profile: CompiledCareerMemoryProfile,
        values: Iterable[str],
    ) -> list[str]:
        return cls._unique(
            value
            for value in values
            if value and cls._profile_value_has_claim_support(profile, value)
        )

    @classmethod
    def _profile_supported_capabilities(
        cls,
        profile: CompiledCareerMemoryProfile,
    ) -> list[str]:
        support_text = " ".join(cls._profile_claim_support_excerpts(profile))
        return cls._unique(
            value
            for value in [*profile.skills_demonstrated, *profile.tools]
            if cls._literal_in_text(value, support_text)
            or (
                len(cls._profile_support_terms(value)) >= 2
                and cls._profile_value_has_claim_support(profile, value)
            )
        )

    @classmethod
    def _has_project_shortcut_evidence(
        cls, profile: CompiledCareerMemoryProfile
    ) -> bool:
        if not cls._has_substantive_profile(profile):
            return False
        capability = cls._profile_capability_text(profile).casefold()
        if profile.project_kind == "GAS_KINEMATICS":
            return any(
                term in capability
                for term in (
                    "uncertainty",
                    "gaussian",
                    "validation",
                    "velocity dispersion",
                    "instrumental broadening",
                )
            )
        if profile.project_kind == "UNICORN":
            quality = any(
                term in capability
                for term in (
                    "data quality",
                    "data-quality",
                    "manual inspection",
                    "detection review",
                    "image-data quality",
                )
            )
            human_review = any(
                term in capability
                for term in (
                    "human-in-the-loop",
                    "labeling",
                    "categorization",
                    "manual inspection",
                )
            )
            return quality and human_review
        return False

    def _profile_evidence_summary(
        self,
        profile: CompiledCareerMemoryProfile,
    ) -> str:
        if not self._profile_has_claim_support(profile):
            return (
                f"{profile.canonical_title} is selected only for limited use as "
                "context; its current record does not support role-specific "
                "capability, method, project, or result claims without direct "
                "source proof."
            )
        if not self._has_substantive_profile(profile):
            inputs = (
                self._join(
                    self._profile_supported_values(
                        profile, profile.data_or_inputs
                    )[:3]
                )
                or "limited source detail"
            )
            return (
                f"{profile.canonical_title} is limited context: the current source "
                f"detail names {inputs}, but does not support specific capability, "
                "method, project, or result claims."
            )
        parts: list[str] = []
        supported_capabilities = self._profile_supported_capabilities(profile)
        supported_inputs = self._profile_supported_values(
            profile, profile.data_or_inputs
        )
        supported_methods = self._profile_supported_values(profile, profile.methods)
        supported_results = self._profile_supported_values(
            profile, profile.findings_or_results
        )
        if profile.memory_type == "SKILL_SET" and supported_capabilities:
            parts.append(
                "documented technical experience with "
                + self._join(supported_capabilities[:4])
            )
        if supported_inputs:
            parts.append(self._join(supported_inputs[:3]))
        if supported_methods:
            parts.append(self._join(supported_methods[:4]))
        if supported_results:
            parts.append(
                self._candidate_result_phrase(
                    supported_results[0],
                    supported_context=[
                        *supported_capabilities,
                        *supported_methods,
                    ],
                )
            )
        detail = "; ".join(parts) or "project context"
        return f"{profile.canonical_title} — {detail}."

    def _target_focus(
        self,
        package: ApplicationPackage,
        profile: CompiledCareerMemoryProfile | None = None,
    ) -> str:
        requirements = self._requested_requirements(package)
        if profile is not None:
            factual_text = self._profile_capability_text(profile)
            supported = [
                label
                for label, patterns in requirements
                if self._patterns_supported(factual_text, patterns)
            ]
            if supported:
                return self._join(supported[:3])
        elif requirements:
            return self._join([label for label, _ in requirements[:3]])
        return "the responsibilities described in the posting"

    def _compile_selected(
        self,
        session: Session,
        memory_ids: Iterable[uuid.UUID],
        target_role: str,
    ) -> list[CompiledCareerMemoryProfile]:
        profiles: list[CompiledCareerMemoryProfile] = []
        for memory_id in memory_ids:
            try:
                profiles.append(self.compiler.compile(session, memory_id, target_role))
            except CareerMemoryCompilationError as exc:
                raise ApplicationPackageValidationError(
                    "Every selected memory must be current-user approved Career Memory."
                ) from exc
        return profiles

    def _get_package(
        self,
        session: Session,
        package_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> ApplicationPackage:
        statement = select(ApplicationPackage).where(
            ApplicationPackage.id == package_id,
            ApplicationPackage.user_id == self.user_id,
        )
        if lock:
            statement = statement.with_for_update()
        package = session.scalar(statement)
        if package is None:
            raise ApplicationPackageNotFoundError("Application package not found.")
        return package

    def _latest_version(
        self,
        session: Session,
        package_id: uuid.UUID,
    ) -> ApplicationPackageVersion | None:
        return session.scalar(
            select(ApplicationPackageVersion)
            .where(
                ApplicationPackageVersion.package_id == package_id,
                ApplicationPackageVersion.user_id == self.user_id,
            )
            .order_by(ApplicationPackageVersion.version_number.desc())
            .limit(1)
        )

    def _latest_generated_version(
        self,
        session: Session,
        package_id: uuid.UUID,
    ) -> ApplicationPackageVersion | None:
        return session.scalar(
            select(ApplicationPackageVersion)
            .where(
                ApplicationPackageVersion.package_id == package_id,
                ApplicationPackageVersion.user_id == self.user_id,
                ApplicationPackageVersion.generation_reason.in_(
                    (
                        ApplicationPackageGenerationReason.GENERATED.value,
                        ApplicationPackageGenerationReason.REGENERATED.value,
                    )
                ),
            )
            .order_by(ApplicationPackageVersion.version_number.desc())
            .limit(1)
        )

    def _versions(
        self,
        session: Session,
        package_id: uuid.UUID,
    ) -> list[ApplicationPackageVersion]:
        return list(
            session.scalars(
                select(ApplicationPackageVersion)
                .where(
                    ApplicationPackageVersion.package_id == package_id,
                    ApplicationPackageVersion.user_id == self.user_id,
                )
                .order_by(ApplicationPackageVersion.version_number.desc())
            ).all()
        )

    def _next_version_number(
        self,
        session: Session,
        package_id: uuid.UUID,
    ) -> int:
        current = session.scalar(
            select(func.max(ApplicationPackageVersion.version_number)).where(
                ApplicationPackageVersion.package_id == package_id,
                ApplicationPackageVersion.user_id == self.user_id,
            )
        )
        return int(current or 0) + 1

    def _view(
        self,
        session: Session,
        package: ApplicationPackage,
    ) -> ApplicationPackageView:
        records = self._versions(session, package.id)
        versions = [self._version_view(record) for record in records]
        latest = versions[0] if versions else None
        latest_record = records[0] if records else None
        stale = (
            self._is_stale(session, package, latest_record)
            if latest_record is not None
            else False
        )
        outputs = latest.outputs if latest else None
        effective_status = ApplicationPackageStatus(package.status)
        if effective_status == ApplicationPackageStatus.READY and stale:
            effective_status = ApplicationPackageStatus.DRAFT
        return ApplicationPackageView(
            package_id=package.id,
            opportunity_id=package.opportunity_id,
            display_name=package.display_name,
            role_title=package.role_title,
            company=package.company,
            location=package.location,
            job_type=package.job_type,
            target_description=package.target_description,
            required_skills=package.required_skills,
            preferred_skills=package.preferred_skills,
            responsibilities=package.responsibilities,
            application_questions=[
                ApplicationQuestion.model_validate(question)
                for question in package.application_questions
            ],
            selected_memory_ids=self._uuid_list(package.selected_memory_ids),
            status=effective_status,
            latest_version=latest,
            versions=versions,
            version_count=len(versions),
            is_stale=stale,
            positioning_summary=outputs.positioning_summary if outputs else None,
            resume_bullets=outputs.resume_bullets if outputs else [],
            cover_letter=outputs.cover_letter if outputs else None,
            application_snippets=outputs.application_snippets if outputs else [],
            suggested_proof_artifacts=(
                outputs.suggested_proof_artifacts if outputs else []
            ),
            evidence_trace=latest.evidence_trace if latest else [],
            warnings=latest.warnings if latest else [],
            reviewer_questions=outputs.reviewer_questions if outputs else [],
            memory_ids_used=latest.memory_ids_used if latest else [],
            enrichment_ids_used=latest.enrichment_ids_used if latest else [],
            outcome_signal_ids_used=(latest.outcome_signal_ids_used if latest else []),
            unsupported_claims=outputs.unsupported_claims if outputs else [],
            writing_intelligence=(latest.writing_intelligence if latest else None),
            requirement_coverage=(latest.requirement_coverage if latest else None),
            quality_review=(latest.quality_review if latest else None),
            provider_metadata=(latest.provider_metadata if latest else None),
            validation_summary=(latest.validation_summary if latest else None),
            evidence_groups=(
                self._group_evidence(latest.evidence_trace) if latest else []
            ),
            warning_groups=(
                self._group_warnings(
                    latest.warnings,
                    latest.requirement_coverage,
                )
                if latest
                else ApplicationWarningGroups()
            ),
            created_at=package.created_at,
            updated_at=package.updated_at,
        )

    def _version_view(
        self,
        version: ApplicationPackageVersion,
    ) -> ApplicationPackageVersionView:
        outputs = ApplicationPackageOutputs.model_validate(
            version.generated_outputs_json
        )
        intelligence = self._stored_intelligence(version, outputs)
        quality = (
            ApplicationWritingQualityReview.model_validate(version.quality_review_json)
            if version.quality_review_json
            else self._evaluate_output_quality(outputs)
        )
        metadata = (
            ApplicationProviderMetadata.model_validate(version.provider_metadata_json)
            if version.provider_metadata_json
            else ApplicationProviderMetadata(
                provider="local-deterministic",
                model=None,
                review_pass_ran=False,
            )
        )
        validation = (
            ApplicationValidationSummary.model_validate(version.validation_summary_json)
            if version.validation_summary_json
            else ApplicationValidationSummary(
                status="PASS",
                notes=["Legacy Sprint 14 version; deterministic trust checks apply."],
            )
        )
        return ApplicationPackageVersionView(
            id=version.id,
            package_id=version.package_id,
            version_number=version.version_number,
            target_snapshot=version.target_snapshot_json,
            selected_memory_ids=self._uuid_list(version.selected_memory_ids_json),
            input_fingerprint=version.input_fingerprint,
            outputs=outputs,
            evidence_trace=[
                ApplicationEvidenceTrace.model_validate(item)
                for item in version.evidence_trace_json
            ],
            warnings=[
                ApplicationPackageWarning.model_validate(item)
                for item in version.warnings_json
            ],
            claim_ledger=[
                ApplicationClaimLedgerEntry.model_validate(item)
                for item in version.claim_ledger_json
            ],
            memory_ids_used=self._uuid_list(version.memory_ids_used_json),
            enrichment_ids_used=self._uuid_list(version.enrichment_ids_used_json),
            outcome_signal_ids_used=self._uuid_list(
                version.outcome_signal_ids_used_json
            ),
            user_edits=version.user_edits_json,
            generator_version=version.generator_version,
            generation_reason=ApplicationPackageGenerationReason(
                version.generation_reason
            ),
            writing_intelligence=intelligence,
            requirement_coverage=intelligence.requirement_coverage,
            quality_review=quality,
            provider_metadata=metadata,
            validation_summary=validation,
            created_at=version.created_at,
        )

    def _stored_intelligence(
        self,
        version: ApplicationPackageVersion,
        outputs: ApplicationPackageOutputs,
    ) -> ApplicationWritingIntelligence:
        if version.writing_intelligence_json:
            return ApplicationWritingIntelligence.model_validate(
                version.writing_intelligence_json
            )
        target = version.target_snapshot_json
        role = str(target.get("role_title") or "target role")
        coverage = RequirementCoverage(
            unsupported=[
                RequirementCoverageItem(
                    requirement=str(item.get("requirement")),
                    evidence=[],
                    memory_ids=self._uuid_list(item.get("memory_ids") or []),
                )
                for item in version.warnings_json
                if item.get("code") == "UNSUPPORTED_TARGET_REQUIREMENT"
                and item.get("requirement")
            ]
        )
        return ApplicationWritingIntelligence(
            job_understanding=ApplicationJobUnderstanding(
                role_family=self._role_family(role),
                seniority=self._role_seniority(role),
                central_objective=f"Contribute to the {role} responsibilities.",
                core_responsibilities=[
                    str(item) for item in target.get("responsibilities") or []
                ],
                must_have_requirements=[
                    str(item) for item in target.get("required_skills") or []
                ],
                preferred_requirements=[
                    str(item) for item in target.get("preferred_skills") or []
                ],
            ),
            requirement_coverage=coverage,
            claim_plan=ApplicationClaimPlan(
                primary_positioning=outputs.positioning_summary.primary_positioning,
                primary_proof=outputs.positioning_summary.strongest_evidence,
                secondary_proof=outputs.positioning_summary.secondary_evidence,
                unsupported_requirements=[
                    item.requirement for item in coverage.unsupported
                ],
                claims_not_to_make=outputs.positioning_summary.do_not_claim,
                missing_evidence=outputs.positioning_summary.risks_and_gaps,
                resume_strategy="Lead with the strongest supported project proof.",
                cover_letter_narrative_strategy=(
                    "Connect two concise proof points to the target role."
                ),
                snippet_strategy="Answer directly with one supported example.",
                tone="Direct, professional, and evidence-aware.",
            ),
            strategy_notes=["Legacy Sprint 14 version with derived intelligence."],
        )

    @classmethod
    def _group_evidence(
        cls,
        traces: list[ApplicationEvidenceTrace],
    ) -> list[ApplicationEvidenceGroup]:
        grouped: dict[str, dict[str, Any]] = {}
        for trace in traces:
            key = str(trace.memory_id) if trace.memory_id else "target-context"
            group = grouped.setdefault(
                key,
                {
                    "memory_id": trace.memory_id,
                    "memory_title": trace.memory_title or "Target role context",
                    "direct_proof": [],
                    "approved_enrichment": [],
                    "supported_framing": [],
                    "strategy_signals": [],
                    "target_relevance": [],
                },
            )
            if trace.support_type == EvidenceSupportType.STRATEGY_ONLY:
                bucket = "strategy_signals"
            elif trace.support_type == EvidenceSupportType.RELEVANCE_ONLY:
                bucket = "target_relevance"
            elif trace.support_type == EvidenceSupportType.INFERRED_FRAMING:
                bucket = "supported_framing"
            elif trace.source_type == EvidenceSourceType.APPROVED_ENRICHMENT:
                bucket = "approved_enrichment"
            else:
                bucket = "direct_proof"
            detail = " ".join(trace.detail.split()).strip()
            if detail and detail not in group[bucket]:
                group[bucket].append(detail)
        return [
            ApplicationEvidenceGroup.model_validate(value)
            for value in grouped.values()
            if any(
                value[name]
                for name in (
                    "direct_proof",
                    "approved_enrichment",
                    "supported_framing",
                    "strategy_signals",
                    "target_relevance",
                )
            )
        ]

    @staticmethod
    def _group_warnings(
        warnings: list[ApplicationPackageWarning],
        coverage: RequirementCoverage,
    ) -> ApplicationWarningGroups:
        unsupported_codes = {
            "UNSUPPORTED_TARGET_REQUIREMENT",
            "UNSUPPORTED_EDITED_NUMBER",
            "UNSUPPORTED_EDITED_CLAIM",
            "CROSS_MEMORY_EDITED_CLAIM",
            "UNSUPPORTED_GENERATED_CLAIM",
        }
        missing_codes = {
            "NO_QUANTIFIED_OUTCOME",
            "SPARSE_APPROVED_MEMORY",
            "MEMORY_CLAIM_BOUNDARY",
        }
        return ApplicationWarningGroups(
            strongly_supported=[
                item.requirement for item in coverage.strongly_supported
            ],
            partially_supported=[
                ApplicationPackageWarning(
                    code="PARTIAL_REQUIREMENT_COVERAGE",
                    message=(
                        f"{item.requirement} has related proof, but the match is not "
                        "direct enough for a stronger claim."
                    ),
                    severity=ApplicationWarningSeverity.CAUTION,
                    requirement=item.requirement,
                    memory_ids=item.memory_ids,
                )
                for item in coverage.partially_supported
            ],
            unsupported=[item for item in warnings if item.code in unsupported_codes],
            missing_proof=[item for item in warnings if item.code in missing_codes],
        )

    @classmethod
    def _evaluate_output_quality(
        cls,
        outputs: ApplicationPackageOutputs,
    ) -> ApplicationWritingQualityReview:
        bullets = [
            bullet.bullet_text
            for group in outputs.resume_bullets
            for bullet in group.bullets
        ]
        prose = " ".join(
            [
                outputs.positioning_summary.primary_positioning,
                outputs.cover_letter.full_text,
                *(snippet.text for snippet in outputs.application_snippets),
                *bullets,
            ]
        )
        lowered = prose.casefold()
        mechanical = [
            phrase
            for phrase in (
                "focused on the project tested whether",
                "the documented result was",
                "my approved work",
                "documented experience with",
                "the approved evidence reports",
                "approved memory",
                "approved evidence",
            )
            if phrase in lowered
        ]
        invalid_grammar = cls._invalid_candidate_grammar(prose)
        repeated_capability_chain = cls._has_repeated_capability_chain(
            outputs.cover_letter.full_text
        )
        long_bullets = [item for item in bullets if len(item.split()) > 38]
        comma_chains = [
            sentence
            for sentence in re.split(r"(?<=[.!?])\s+", prose)
            if sentence.count(",") >= 4
        ]
        cover_words = len(outputs.cover_letter.full_text.split())
        titles = [group.memory_title.casefold() for group in outputs.resume_bullets]
        repeated_titles = [title for title in titles if lowered.count(title) > 4]
        generic_markers = sum(
            lowered.count(phrase)
            for phrase in (
                "i am applying for",
                "i would welcome the opportunity",
                "careful analysis",
                "contribute thoughtfully",
            )
        )
        warning_overload = (
            len(outputs.cover_letter.warnings) + len(outputs.unsupported_claims) > 6
        )
        role_specific = bool(
            outputs.positioning_summary.recommended_emphasis
            and re.search(
                r"\b(?:role|application|team)\b",
                outputs.positioning_summary.primary_positioning,
                re.I,
            )
        )
        notes: list[str] = []
        if mechanical:
            notes.append("Replace mechanical source-field language with natural prose.")
        if invalid_grammar:
            notes.append(
                "Correct invalid grammar in article, title, or verb constructions."
            )
        if repeated_capability_chain:
            notes.append(
                "Remove repeated capability chains from adjacent cover-letter "
                "paragraphs."
            )
        if long_bullets:
            notes.append("Shorten resume bullets to one central idea.")
        if comma_chains:
            notes.append("Reduce technical comma chains for faster reading.")
        if not 230 <= cover_words <= 420:
            notes.append(
                f"Cover letter is {cover_words} words; aim for roughly 250–400."
            )
        if repeated_titles:
            notes.append("Reduce repeated project titles after the first reference.")
        if warning_overload:
            notes.append("Resolve or consolidate the highest-priority proof gaps.")
        if generic_markers > 4:
            notes.append("Replace generic transitions with role-specific value.")
        primary_issue = (
            notes[0] if notes else "No material writing-quality issue detected."
        )
        natural = "Needs attention" if mechanical or invalid_grammar else "Strong"
        concise = "Needs attention" if long_bullets or comma_chains else "Good"
        readable = (
            "Needs attention"
            if mechanical or invalid_grammar or comma_chains
            else "Strong"
        )
        genericness = (
            "High" if generic_markers > 4 else "Moderate" if generic_markers else "Low"
        )
        return ApplicationWritingQualityReview(
            evidence_support=("Strong" if not outputs.unsupported_claims else "Good"),
            role_relevance="Strong" if role_specific else "Good",
            specificity="Strong" if outputs.resume_bullets else "Limited",
            naturalness=natural,
            concision=concise,
            recruiter_readability=("Needs attention" if warning_overload else readable),
            genericness=genericness,
            repetition=(
                "High"
                if repeated_capability_chain
                else "Moderate"
                if repeated_titles
                else "Low"
            ),
            overclaim_risk=(
                "Review"
                if any("Unverified" in item for item in outputs.unsupported_claims)
                else "Low"
            ),
            primary_issue=primary_issue,
            notes=notes[:4],
        )

    def _list_item(
        self,
        session: Session,
        package: ApplicationPackage,
    ) -> ApplicationPackageListItem:
        versions = self._versions(session, package.id)
        latest = versions[0] if versions else None
        stale = self._is_stale(session, package, latest) if latest else False
        effective_status = ApplicationPackageStatus(package.status)
        if effective_status == ApplicationPackageStatus.READY and stale:
            effective_status = ApplicationPackageStatus.DRAFT
        return ApplicationPackageListItem(
            package_id=package.id,
            display_name=package.display_name,
            role_title=package.role_title,
            company=package.company,
            status=effective_status,
            selected_memory_ids=self._uuid_list(package.selected_memory_ids),
            version_count=len(versions),
            latest_version_number=latest.version_number if latest else None,
            is_stale=stale,
            created_at=package.created_at,
            updated_at=package.updated_at,
        )

    def _is_stale(
        self,
        session: Session,
        package: ApplicationPackage,
        version: ApplicationPackageVersion,
    ) -> bool:
        try:
            selected = self._uuid_list(package.selected_memory_ids)
            profiles = self._compile_selected(session, selected, package.role_title)
        except (ApplicationPackageValidationError, ValueError):
            return True
        current = self._fingerprint(
            self._target_snapshot(package),
            selected,
            [item.model_dump(mode="json") for item in profiles],
        )
        return current != version.input_fingerprint

    @classmethod
    def _fingerprint(
        cls,
        target_snapshot: dict[str, Any],
        selected_memory_ids: Iterable[uuid.UUID],
        profile_snapshots: list[dict[str, Any]],
    ) -> str:
        payload = {
            "target": target_snapshot,
            "selected_memory_ids": [str(item) for item in selected_memory_ids],
            "compiled_profiles": profile_snapshots,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _stable_contract_id(prefix: str, *components: object) -> str:
        """Build an order-independent ID from immutable source identity and content."""

        normalized = [
            " ".join(str(component).split()).casefold() for component in components
        ]
        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()[:32]
        return f"{prefix}-{digest}"

    @staticmethod
    def _target_snapshot(package: ApplicationPackage) -> dict[str, Any]:
        return {
            "opportunity_id": (
                str(package.opportunity_id) if package.opportunity_id else None
            ),
            "role_title": package.role_title,
            "company": package.company,
            "location": package.location,
            "job_type": package.job_type,
            "target_description": package.target_description,
            "required_skills": package.required_skills,
            "preferred_skills": package.preferred_skills,
            "responsibilities": package.responsibilities,
            "application_questions": package.application_questions,
        }

    @staticmethod
    def _target_text(package: ApplicationPackage) -> str:
        return " ".join(
            [
                package.role_title,
                package.target_description,
                *package.required_skills,
                *package.preferred_skills,
                *package.responsibilities,
            ]
        )

    def _validate_opportunity(
        self,
        session: Session,
        opportunity_id: uuid.UUID | None,
    ) -> None:
        if opportunity_id is None:
            return
        opportunity = session.get(ApplicationOpportunity, opportunity_id)
        if opportunity is None or opportunity.user_id != self.user_id:
            raise ApplicationPackageValidationError(
                "Linked application opportunity was not found for this user."
            )

    def _ensure_user(self, session: Session) -> None:
        if session.get(User, self.user_id) is None:
            session.add(
                User(
                    id=self.user_id,
                    clerk_user_id=f"application-package-demo-{self.user_id}",
                    email=f"application-package-demo-{self.user_id}@example.invalid",
                    display_name="Application Package Demo User",
                )
            )
            session.flush()

    @staticmethod
    def _changed_claim_text(baseline: str, current: str) -> str:
        """Return current sentences whose factual wording differs from generation."""

        def sentences(value: str) -> list[str]:
            return [
                item.strip()
                for item in re.split(r"(?<=[.!?])(?:\s+|$)|[\r\n]+", value)
                if item.strip()
            ]

        def key(value: str) -> str:
            return " ".join(re.findall(r"[a-z0-9%+#./-]+", value.casefold()))

        baseline_keys = {key(item) for item in sentences(baseline)}
        return " ".join(
            item for item in sentences(current) if key(item) not in baseline_keys
        )

    @classmethod
    def _unsupported_numbers_for_claims(
        cls,
        claims: list[_EditedClaim],
        profile_snapshots: list[dict[str, Any]],
        target_snapshot: dict[str, Any],
    ) -> list[str]:
        unsupported: set[str] = set()
        number_pattern = (
            r"(?<!\w)(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
            r"(?:%|[kmbx])?(?!\w)"
        )

        def numeric_tokens(value: str) -> set[str]:
            return {
                cls._normalize_numeric_token(item)
                for item in re.findall(number_pattern, value, flags=re.IGNORECASE)
            }

        for claim in claims:
            approved_text = cls._snapshot_positive_text(
                cls._snapshots_for_ids(profile_snapshots, claim.memory_ids)
            )
            audited_text = cls._remove_numeric_target_context(
                claim.text, target_snapshot, claim.surface
            )
            output_numbers = numeric_tokens(audited_text)
            approved_numbers = numeric_tokens(approved_text)
            unsupported.update(output_numbers - approved_numbers)
        return sorted(unsupported)

    @staticmethod
    def _normalize_numeric_token(value: str) -> str:
        compact = value.replace(",", "").casefold()
        suffix = compact[-1:] if compact[-1:] in {"k", "m", "b", "x", "%"} else ""
        number_text = compact[:-1] if suffix else compact
        try:
            number = Decimal(number_text)
        except InvalidOperation:
            return compact
        if suffix in {"k", "m", "b"}:
            number *= {
                "k": Decimal("1000"),
                "m": Decimal("1000000"),
                "b": Decimal("1000000000"),
            }[suffix]
            suffix = ""
        normalized = format(number.normalize(), "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        return f"{normalized}{suffix}"

    @classmethod
    def _remove_numeric_target_context(
        cls, value: str, target_snapshot: dict[str, Any], surface: str
    ) -> str:
        """Mask numeric target phrases only where text does not assert capability."""

        masked = value
        role_title = str(target_snapshot.get("role_title") or "").strip()
        if role_title:
            masked = re.sub(
                rf"{re.escape(role_title)}(?=\s+(?:role|position|application)\b)",
                " ",
                masked,
                flags=re.IGNORECASE,
            )
        company = str(target_snapshot.get("company") or "").strip()
        if company:
            masked = re.sub(
                rf"(\b(?:at|with|dear)\s+){re.escape(company)}\b",
                r"\1 ",
                masked,
                flags=re.IGNORECASE,
            )
        target_phrases = [
            str(item).strip()
            for field in ("required_skills", "preferred_skills")
            for item in (target_snapshot.get(field) or [])
            if str(item).strip()
        ]
        sentences = [
            item
            for item in re.split(r"(?<=[.!?])(?:\s+|$)|[\r\n]+", masked)
            if item.strip()
        ]
        for index, sentence in enumerate(sentences):
            if cls._target_phrase_is_factual_claim(sentence, surface):
                continue
            for phrase in target_phrases:
                sentence = re.sub(re.escape(phrase), " ", sentence, flags=re.IGNORECASE)
            sentences[index] = sentence
        return " ".join(sentences)

    @staticmethod
    def _target_phrase_is_factual_claim(value: str, surface: str) -> bool:
        if surface == "resume":
            return True
        first_person = r"(?:\bI\b|\bmy\b|\bwe\b|\bour\b)"
        factual_marker = (
            r"\b(?:use|used|built|build|deploy\w*|develop\w*|implement\w*|"
            r"manage\w*|lead|led|train\w*|automat\w*|bring|experience|"
            r"proficien\w*|skill\w*|worked|analy[sz]\w*|serv\w*|improv\w*|"
            r"achiev\w*|deliver\w*|complet\w*|earn\w*|certif\w*|obtain\w*|"
            r"support\w*|operat\w*|creat\w*|design\w*|owned|drove|familiar|"
            r"knowledge)\b"
        )
        if re.search(
            rf"(?:{first_person}.{{0,140}}{factual_marker}|"
            rf"{factual_marker}.{{0,140}}{first_person})",
            value,
            re.IGNORECASE,
        ):
            return True
        return surface == "positioning" and bool(
            re.search(
                r"\b(?:proof|experience|skill|capabilit\w*|certif\w*|knowledge)\b",
                value,
                re.IGNORECASE,
            )
        )

    @classmethod
    def _unsupported_terms_for_claims(
        cls,
        claims: list[_EditedClaim],
        profile_snapshots: list[dict[str, Any]],
        unsupported_requirements: Iterable[str],
    ) -> list[str]:
        candidates: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = list(
            cls._requirement_rules
        )
        known = {label.casefold() for label, _, _ in candidates}
        candidates.extend(
            (
                item,
                (cls._literal_pattern(item),),
                (cls._literal_pattern(item),),
            )
            for item in unsupported_requirements
            if item.casefold() not in known
        )
        first_person = r"(?:\bI\b|\bmy\b|\bwe\b|\bour\b)"
        claim_verb = (
            r"\b(?:use|used|built|build|deploy\w*|develop\w*|implement\w*|"
            r"manage\w*|lead|led|train\w*|automat\w*|bring|experience|"
            r"proficien\w*|skill\w*|worked)\b"
        )
        unsupported: list[str] = []
        for claim in claims:
            approved_text = cls._snapshot_positive_text(
                cls._snapshots_for_ids(profile_snapshots, claim.memory_ids)
            )
            for label, output_patterns, support_patterns in candidates:
                if cls._patterns_supported(approved_text, support_patterns):
                    continue
                appears_as_claim = False
                for pattern in output_patterns:
                    if claim.surface == "resume" and re.search(
                        pattern, claim.text, re.I
                    ):
                        appears_as_claim = True
                    elif re.search(
                        rf"(?:{first_person}.{{0,90}}{claim_verb}.{{0,120}}{pattern}|"
                        rf"{first_person}.{{0,90}}{pattern}.{{0,120}}{claim_verb}|"
                        rf"{pattern}.{{0,120}}{first_person}.{{0,90}}{claim_verb})",
                        claim.text,
                        re.I,
                    ):
                        appears_as_claim = True
                    elif claim.surface == "positioning" and re.search(
                        rf"(?:proof|experience|skill|capabilit).{{0,120}}{pattern}|"
                        rf"{pattern}.{{0,120}}(?:proof|experience|skill|capabilit)",
                        claim.text,
                        re.I,
                    ):
                        appears_as_claim = True
                    if appears_as_claim:
                        break
                if appears_as_claim:
                    unsupported.append(label)
        return cls._unique(unsupported)

    @classmethod
    def _cross_memory_terms_for_claims(
        cls,
        claims: list[_EditedClaim],
        profile_snapshots: list[dict[str, Any]],
    ) -> list[str]:
        selected_ids = {
            uuid.UUID(str(profile["memory_id"]))
            for profile in profile_snapshots
            if profile.get("memory_id")
        }
        unsupported: list[str] = []
        for claim in claims:
            if claim.surface != "resume":
                continue
            allowed = cls._snapshot_positive_text(
                cls._snapshots_for_ids(profile_snapshots, claim.memory_ids)
            )
            foreign = cls._snapshots_for_ids(
                profile_snapshots,
                selected_ids - set(claim.memory_ids),
            )
            markers = cls._unique(
                [
                    *cls._distinctive_snapshot_markers(foreign),
                    *cls._distinctive_markers(claim.text),
                ]
            )
            for marker in markers:
                pattern = cls._literal_pattern(marker)
                if re.search(pattern, claim.text, re.I) and not re.search(
                    pattern, allowed, re.I
                ):
                    unsupported.append(marker)
        return cls._unique(unsupported)

    @classmethod
    def _unsupported_outcomes_for_claims(
        cls,
        claims: list[_EditedClaim],
        profile_snapshots: list[dict[str, Any]],
    ) -> list[str]:
        outcome_patterns = (
            r"\bimprov\w*\b",
            r"\bincreas\w*\b",
            r"\breduc\w*\b",
            r"\bboost\w*\b",
            r"\bsav(?:ed|ing)\b",
            r"\bearn\w*\b",
            r"\bwon\b",
            r"\bachiev\w*\b",
            r"\baccelerat\w*\b",
            r"\bresulted\s+in\b",
            r"\bled\s+to\b",
            r"\bdrove\b",
        )
        object_stop = {
            "a",
            "an",
            "and",
            "for",
            "in",
            "of",
            "our",
            "the",
            "their",
            "this",
            "to",
            "with",
        }
        unsupported: list[str] = []
        for claim in claims:
            approved = cls._snapshot_positive_text(
                cls._snapshots_for_ids(profile_snapshots, claim.memory_ids)
            ).casefold()
            for pattern in outcome_patterns:
                for match in re.finditer(pattern, claim.text, re.I):
                    if not re.search(pattern, approved, re.I):
                        unsupported.append(match.group(0))
                        continue
                    tail = claim.text[match.end() :]
                    object_tokens = [
                        token
                        for token in re.findall(r"[a-z][a-z0-9+-]{2,}", tail.casefold())
                        if token not in object_stop
                    ]
                    if object_tokens and object_tokens[0] not in approved:
                        unsupported.append(f"{match.group(0)} {object_tokens[0]}")
        return cls._unique(unsupported)

    @classmethod
    def _strategy_signal_leakage_for_claims(
        cls,
        claims: list[_EditedClaim],
        profile_snapshots: list[dict[str, Any]],
        writing_input: ApplicationWritingInput,
    ) -> list[str]:
        if not writing_input.outcome_signals:
            return []
        approved = cls._snapshot_positive_text(profile_snapshots).casefold()
        signal_text = " ".join(
            f"{signal.label} {signal.content}"
            for signal in writing_input.outcome_signals
        )
        high_risk_signal_terms = {
            "acceptance",
            "accepted",
            "callback",
            "conversion",
            "hired",
            "hiring",
            "interview",
            "invitation",
            "invited",
            "offer",
            "recruiter",
            "selected",
        }
        signal_only_tokens = {
            token
            for token in re.findall(r"[a-z][a-z0-9+-]{4,}", signal_text.casefold())
            if token in high_risk_signal_terms and token not in approved
        }
        leaked = {
            token
            for claim in claims
            for token in signal_only_tokens
            if re.search(cls._literal_pattern(token), claim.text, re.I)
        }
        return sorted(leaked)

    @classmethod
    def _profile_capability_text(
        cls,
        profile: CompiledCareerMemoryProfile,
    ) -> str:
        return cls._positive_text(
            [
                *cls._profile_supported_values(profile, profile.data_or_inputs),
                *cls._profile_supported_values(profile, profile.methods),
                *cls._profile_supported_capabilities(profile),
                *cls._profile_supported_values(profile, profile.workflow_steps),
                *cls._profile_supported_values(
                    profile, profile.findings_or_results
                ),
                *cls._profile_supported_values(profile, profile.outputs),
                *cls._profile_supported_values(profile, profile.proof_claims),
                *cls._profile_supported_values(
                    profile, profile.resume_bullet_claims
                ),
            ]
        )

    @classmethod
    def _profile_relevance_text(
        cls,
        profile: CompiledCareerMemoryProfile,
    ) -> str:
        return cls._positive_text(
            [
                profile.canonical_title,
                profile.research_question_or_problem or "",
                cls._profile_capability_text(profile),
            ]
        )

    @classmethod
    def _snapshot_positive_text(
        cls,
        profile_snapshots: list[dict[str, Any]],
    ) -> str:
        positive_keys = {
            "data_or_inputs",
            "methods",
            "tools",
            "workflow_steps",
            "findings_or_results",
            "outputs",
            "collaborators_or_context",
            "skills_demonstrated",
            "proof_claims",
            "resume_bullet_claims",
        }
        return cls._positive_text(
            [profile.get(key) for profile in profile_snapshots for key in positive_keys]
        )

    @staticmethod
    def _snapshots_for_ids(
        profile_snapshots: list[dict[str, Any]],
        memory_ids: Iterable[uuid.UUID],
    ) -> list[dict[str, Any]]:
        wanted = {str(item) for item in memory_ids}
        return [
            profile
            for profile in profile_snapshots
            if str(profile.get("memory_id")) in wanted
        ]

    @classmethod
    def _positive_text(cls, values: Iterable[Any]) -> str:
        strings: list[str] = []

        def collect(value: Any) -> None:
            if isinstance(value, str):
                strings.append(value)
            elif isinstance(value, dict):
                for nested in value.values():
                    collect(nested)
            elif isinstance(value, Iterable):
                for nested in value:
                    collect(nested)

        for value in values:
            collect(value)
        clauses = [
            clause.strip()
            for value in strings
            for clause in re.split(r"[.;\n]+", value)
            if clause.strip()
        ]
        negation = re.compile(
            r"\b(?:no|not|never|without|cannot|can't|didn't|did\s+not|"
            r"wasn't|was\s+not|weren't|were\s+not|hasn't|has\s+not|"
            r"haven't|have\s+not|lack(?:ed|ing|s)?)\b",
            re.I,
        )
        return " ".join(clause for clause in clauses if not negation.search(clause))

    @staticmethod
    def _literal_pattern(value: str) -> str:
        normalized = " ".join(value.split())
        escaped = re.escape(normalized).replace(r"\ ", r"\s+")
        return rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"

    @staticmethod
    def _patterns_supported(text: str, patterns: Iterable[str]) -> bool:
        return any(re.search(pattern, text, re.I) for pattern in patterns)

    @classmethod
    def _distinctive_snapshot_markers(
        cls,
        profile_snapshots: list[dict[str, Any]],
    ) -> list[str]:
        return cls._distinctive_markers(cls._snapshot_positive_text(profile_snapshots))

    @classmethod
    def _distinctive_markers(cls, text: str) -> list[str]:
        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9+/#\[\]_.-]{2,}", text)
        generic = {
            "analysis",
            "analyzed",
            "applied",
            "data",
            "dataset",
            "evidence",
            "model",
            "modeling",
            "project",
            "review",
            "reviewed",
            "technical",
            "validation",
            "workflow",
        }
        return cls._unique(
            token
            for token in tokens
            if token.casefold() not in generic
            and (
                sum(character.isupper() for character in token) >= 2
                or any(character in token for character in "-/_[]+#")
            )
        )

    @staticmethod
    def _section_suggestion(memory_type: str) -> str:
        labels = {
            "PROJECT": "Projects",
            "EXPERIENCE": "Experience",
            "EDUCATION": "Education",
            "ACHIEVEMENT": "Leadership",
            "SKILL_SET": "Skills",
        }
        return labels.get(memory_type, "Experience")

    @staticmethod
    def _display_name(role_title: str, company: str | None) -> str:
        return f"{role_title} — {company}" if company else role_title

    @classmethod
    def _has_quantified_result(cls, profile: CompiledCareerMemoryProfile) -> bool:
        result_text = " ".join(
            cls._profile_supported_values(profile, profile.findings_or_results)
        )
        return bool(
            re.search(
                r"(?<!\w)\d+(?:\.\d+)?\s*(?:%|percent\b|x\b|samples?\b|"
                r"records?\b|objects?\b|hours?\b|days?\b)",
                result_text,
                re.I,
            )
        )

    @staticmethod
    def _terms(value: str) -> set[str]:
        stop = {
            "and",
            "the",
            "for",
            "with",
            "this",
            "that",
            "from",
            "into",
            "role",
            "work",
            "using",
            "approved",
        }
        return {
            token
            for token in re.findall(r"[a-z][a-z0-9+#-]{1,}", value.casefold())
            if token not in stop
        }

    @staticmethod
    def _sentence(value: str) -> str:
        cleaned = " ".join(value.split()).strip()
        if not cleaned:
            return cleaned
        cleaned = cleaned[0].upper() + cleaned[1:]
        return cleaned if cleaned.endswith((".", "!", "?")) else f"{cleaned}."

    @staticmethod
    def _lower_first(value: str) -> str:
        cleaned = " ".join(value.split()).strip().rstrip(".")
        return cleaned[:1].lower() + cleaned[1:] if cleaned else cleaned

    @staticmethod
    def _contextual_title(value: str) -> str:
        """Render a title after a preposition without duplicating its article."""

        cleaned = " ".join(value.split()).strip()
        return re.sub(
            r"^(?:the|a|an)\b",
            lambda match: match.group(0).casefold(),
            cleaned,
            count=1,
            flags=re.I,
        )

    @staticmethod
    def _candidate_capability_phrase(value: str) -> str:
        """Add a determiner when a supported capability is a singular workflow."""

        cleaned = " ".join(value.split()).strip().rstrip(".")
        if re.search(r"\bworkflow$", cleaned, re.I) and not re.match(
            r"^(?:a|an|the|this|that|my|our)\b", cleaned, re.I
        ):
            return f"a {cleaned}"
        return cleaned

    @staticmethod
    def _candidate_source_phrase(value: str) -> str:
        """Resolve ambiguous source labels without adding a new factual object."""

        cleaned = " ".join(value.split()).strip()
        return re.sub(
            r"\bsource\s+or\s+detection\s+candidates\b",
            "detection candidates",
            cleaned,
            flags=re.I,
        )

    @classmethod
    def _problem_phrase(cls, value: str | None) -> str:
        if value is None or not value.strip():
            return ""
        cleaned = " ".join(value.split()).strip().rstrip(".")
        cleaned = re.sub(
            r"^(?:the\s+)?project\s+(?:(?:focused|focuses)\s+on\s+|tested\s+whether\s+)",
            "",
            cleaned,
            flags=re.I,
        )
        if not cleaned:
            return ""
        return cls._lower_first(cleaned)

    @classmethod
    def _candidate_result_phrase(
        cls,
        value: str,
        *,
        supported_context: Iterable[str] = (),
    ) -> str:
        """Remove compiler provenance wrappers from candidate-facing results."""

        cleaned = " ".join(value.split()).strip().rstrip(".")
        cleaned = re.sub(
            r"^(?:(?:the\s+)?approved\s+evidence\s+reports?|"
            r"the\s+documented\s+result\s+was)\s+",
            "",
            cleaned,
            flags=re.I,
        )
        alternative_efficiency = re.fullmatch(
            r"improved\s+([a-z][\w-]*)\s+or\s+([a-z][\w-]*)\s+efficiency",
            cleaned,
            re.I,
        )
        context = " ".join(supported_context)
        if alternative_efficiency and all(
            cls._literal_in_text(term, context)
            for term in alternative_efficiency.groups()
        ):
            first, second = alternative_efficiency.groups()
            cleaned = f"improved efficiency in {first} and {second}"
        return cls._lower_first(cleaned)

    @staticmethod
    def _compact_phrase(value: str, word_limit: int) -> str:
        cleaned = " ".join(value.split()).strip().rstrip(".;")
        words = cleaned.split()
        if len(words) <= word_limit:
            return cleaned
        compacted = " ".join(words[:word_limit]).rstrip(",;:")
        return re.sub(
            r"\s+\b(?:and|or|of|to|for|with|through|around|using|as)\b$",
            "",
            compacted,
            flags=re.I,
        )

    @classmethod
    def _gerund_action_phrase(cls, value: str) -> str:
        """Render a documented workflow step naturally after the word ``by``."""

        rendered = " ".join(value.split()).strip().rstrip(".")
        if not rendered:
            return ""
        rendered = cls._candidate_source_phrase(rendered)
        trailing_adverb = re.search(r"\s+(manually|carefully)$", rendered, re.I)
        adverb = trailing_adverb.group(1).casefold() if trailing_adverb else ""
        if trailing_adverb:
            rendered = rendered[: trailing_adverb.start()].rstrip()
        first, separator, remainder = rendered.partition(" ")
        gerunds = {
            "analyzed": "analyzing",
            "applied": "applying",
            "built": "building",
            "checked": "checking",
            "compared": "comparing",
            "created": "creating",
            "documented": "documenting",
            "inspected": "inspecting",
            "reviewed": "reviewing",
            "used": "using",
            "validated": "validating",
        }
        action = gerunds.get(first.casefold(), cls._lower_first(first))
        phrase = f"{action}{separator}{remainder}".strip()
        return f"{adverb} {phrase}".strip() if adverb else phrase

    @staticmethod
    def _invalid_candidate_grammar(value: str) -> list[str]:
        patterns = {
            "possessive before title article": r"\bmy\s+(?:the|a|an)\b",
            "gerund after ability to": r"\bability\s+to\s+[a-z][\w-]*ing\b",
            "missing workflow article": (
                r"\brequir(?:e|es|ed|ing)\s+"
                r"(?!(?:a|an|the)\s+)(?:[a-z][\w-]*\s+){1,5}workflow\b"
            ),
        }
        return [
            label
            for label, pattern in patterns.items()
            if re.search(pattern, value, re.I)
        ]

    @classmethod
    def _has_repeated_capability_chain(cls, value: str) -> bool:
        """Detect a repeated multi-item phrase in adjacent cover paragraphs."""

        paragraphs = [
            paragraph
            for paragraph in re.split(r"\n\s*\n", value.casefold())
            if paragraph.strip()
        ]
        stop_words = {
            "a",
            "an",
            "and",
            "as",
            "at",
            "by",
            "for",
            "from",
            "i",
            "in",
            "it",
            "my",
            "of",
            "on",
            "or",
            "the",
            "this",
            "to",
            "with",
            "would",
        }
        phrase_size = 8
        tokenized = [
            re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", paragraph)
            for paragraph in paragraphs
        ]
        for left, right in zip(tokenized, tokenized[1:], strict=False):
            if len(left) < phrase_size or len(right) < phrase_size:
                continue
            left_phrases = {
                tuple(left[index : index + phrase_size])
                for index in range(len(left) - phrase_size + 1)
            }
            for index in range(len(right) - phrase_size + 1):
                phrase = tuple(right[index : index + phrase_size])
                if (
                    phrase in left_phrases
                    and sum(token not in stop_words for token in phrase) >= 4
                ):
                    return True
        return False

    @staticmethod
    def _contains_mechanical_phrase(value: str) -> bool:
        lowered = value.casefold()
        return any(
            phrase in lowered
            for phrase in (
                "focused on the project tested whether",
                "the documented result was",
                "my approved work",
                "documented experience with",
                "the approved evidence reports",
                "approved memory",
                "approved evidence",
            )
        )

    @staticmethod
    def _role_family(role_title: str) -> str:
        value = role_title.casefold()
        if any(token in value for token in ("data science", "data scientist")):
            return "Data science"
        if any(token in value for token in ("analytics", "data analyst")):
            return "Analytics"
        if any(token in value for token in ("machine learning", "ai ", "artificial")):
            return "AI and machine learning"
        if "research" in value:
            return "Research"
        if any(token in value for token in ("software", "engineer", "developer")):
            return "Engineering"
        if any(token in value for token in ("lead", "manager", "operations")):
            return "Leadership and operations"
        return "General professional"

    @staticmethod
    def _role_seniority(role_title: str) -> str:
        value = role_title.casefold()
        if "intern" in value:
            return "Internship"
        if any(token in value for token in ("entry", "junior", "associate")):
            return "Entry level"
        if any(token in value for token in ("senior", "staff", "principal")):
            return "Senior"
        if any(token in value for token in ("manager", "director", "lead")):
            return "Leadership"
        return "Not explicitly stated"

    @staticmethod
    def _join(values: list[str]) -> str:
        rendered = [" ".join(item.split()).strip().rstrip(".") for item in values]
        rendered = [item for item in rendered if item]
        if not rendered:
            return ""
        if len(rendered) == 1:
            return rendered[0]
        if len(rendered) == 2:
            return f"{rendered[0]} and {rendered[1]}"
        return f"{', '.join(rendered[:-1])}, and {rendered[-1]}"

    @classmethod
    def _join_action_steps(cls, values: list[str]) -> str:
        if not values:
            return ""
        rendered = [cls._candidate_source_phrase(value) for value in values]
        return cls._join(
            [rendered[0], *(cls._lower_first(value) for value in rendered[1:])]
        )

    @staticmethod
    def _clean_list(values: Iterable[str]) -> list[str]:
        return ApplicationPackageService._unique(values)

    @staticmethod
    def _uuid_list(values: Iterable[str | uuid.UUID]) -> list[uuid.UUID]:
        return [
            item if isinstance(item, uuid.UUID) else uuid.UUID(item) for item in values
        ]

    @staticmethod
    def _unique(values: Iterable[Any]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for value in values:
            if isinstance(value, (list, tuple, set)):
                candidates = value
            else:
                candidates = (value,)
            for candidate in candidates:
                rendered = " ".join(str(candidate or "").split()).strip()
                if not rendered or rendered.casefold() in seen:
                    continue
                seen.add(rendered.casefold())
                unique.append(rendered)
        return unique

    @staticmethod
    def _unique_uuid(values: Iterable[uuid.UUID]) -> list[uuid.UUID]:
        return list(dict.fromkeys(values))

    @staticmethod
    def _json_value(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [ApplicationPackageService._json_value(item) for item in value]
        return value

    @staticmethod
    def _dedupe_warnings(
        warnings: Iterable[ApplicationPackageWarning],
    ) -> list[ApplicationPackageWarning]:
        result: list[ApplicationPackageWarning] = []
        seen: set[tuple[str, str]] = set()
        for warning in warnings:
            key = (warning.code, warning.message)
            if key in seen:
                continue
            seen.add(key)
            result.append(warning)
        return result

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
    ApplicationEvidenceTrace,
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
    ApplicationSnippet,
    ApplicationWarningSeverity,
    CoverLetterDraft,
    CoverLetterParagraphTrace,
    EvidenceSourceType,
    EvidenceSupportType,
    PositioningSummary,
    ResumeBullet,
    ResumeBulletGroup,
    SuggestedProofArtifact,
)
from app.schemas.career_memory import CompiledCareerMemoryProfile, CompiledEvidenceKind
from app.schemas.knowledge import DEMO_USER_ID, DurableReviewStatus
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

    generator_version = "local-deterministic-application-package-v1"

    _requirement_rules: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
        ("Python", (r"\bpython\b",), (r"\bpython\b",)),
        ("SQL", (r"\bsql\b",), (r"\bsql\b",)),
        ("R", (r"(?<![a-z])r(?![a-z])",), (r"(?<![a-z])r(?![a-z])",)),
        ("Excel", (r"\bexcel\b",), (r"\bexcel\b",)),
        ("Tableau", (r"\btableau\b",), (r"\btableau\b",)),
        ("Power BI", (r"\bpower\s*bi\b",), (r"\bpower\s*bi\b",)),
        (
            "data analysis",
            (r"\bdata analysis\b", r"\banaly[sz](?:e|ed|ing|is)\b"),
            (r"\bdata analysis\b", r"\banaly[sz](?:e|ed|ing|is)\b"),
        ),
        (
            "modeling",
            (r"\bmodel(?:ing|ling)?\b",),
            (r"\bmodel(?:ing|ling)?\b", r"gaussian fit"),
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
            (r"\bcommunicat", r"\bpresent", r"documentation"),
            (r"\bcommunicat", r"\bpresent", r"documentation", r"report"),
        ),
        (
            "data quality",
            (r"data quality", r"quality control", r"quality review"),
            (r"data quality", r"quality control", r"quality review", r"quality cuts"),
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
            "leadership",
            (r"\bleadership\b", r"\blead (?:a |the )?team\b"),
            (r"\bleadership\b", r"\bled (?:a |the )?team\b"),
        ),
    )

    def __init__(
        self,
        user_id: uuid.UUID = DEMO_USER_ID,
        compiler: CareerMemoryCompiler | None = None,
    ) -> None:
        self.user_id = user_id
        self.compiler = compiler or CareerMemoryCompiler(user_id=user_id)

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
        options: list[tuple[float, ApplicationPackageMemoryOption]] = []
        target_text = target_role or ""
        for memory in records:
            profile = self.compiler.compile(session, memory.id, target_role)
            ranked = self._rank_profile(profile, target_text)
            options.append(
                (
                    ranked.score,
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
                            "Edited text contains numbers not found in approved "
                            "memory: " + ", ".join(unsupported_numbers) + "."
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
                if requested_snippet.text == snippet.text:
                    continue
                snippet.text = requested_snippet.text
                snippet.warnings = self._unique([*snippet.warnings, edit_caveat])
                changed("application_snippets")
                changed_claim_ids.add(f"snippet-{index}")

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
                f"snippet-{index}",
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
        selected_ids = self._uuid_list(package.selected_memory_ids)
        if not selected_ids:
            raise ApplicationPackageValidationError(
                "Select at least one approved Career Memory before generating."
            )
        profiles = self._compile_selected(session, selected_ids, package.role_title)
        target_text = self._target_text(package)
        ranked = sorted(
            (self._rank_profile(profile, target_text) for profile in profiles),
            key=lambda item: item.score,
            reverse=True,
        )
        target_snapshot = self._target_snapshot(package)
        profile_snapshots = [item.model_dump(mode="json") for item in profiles]
        fingerprint = self._fingerprint(
            target_snapshot,
            selected_ids,
            profile_snapshots,
        )
        evidence_trace = self._aggregate_evidence_trace(package, ranked)
        warnings, unsupported_requirements = self._warnings(package, ranked)
        outputs = self._compose_outputs(
            session,
            package,
            ranked,
            warnings,
            unsupported_requirements,
        )
        ledger = self._claim_ledger(outputs)
        memory_ids = [item.profile.memory_id for item in ranked]
        enrichment_ids = self._unique_uuid(
            enrichment_id
            for item in ranked
            for enrichment_id in item.profile.enrichment_ids_used
        )
        outcome_ids = self._unique_uuid(
            signal_id
            for item in ranked
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
            generator_version=self.generator_version,
            generation_reason=reason.value,
        )
        package.status = ApplicationPackageStatus.DRAFT.value
        package.updated_at = datetime.now(UTC)
        session.add(version)
        session.commit()
        return self.get(session, package.id)

    def _compose_outputs(
        self,
        session: Session,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        warnings: list[ApplicationPackageWarning],
        unsupported_requirements: list[str],
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
        snippets = self._snippets(package, ranked, warnings)
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
        bullet_texts = list(profile.resume_bullet_claims[:2])
        if len(bullet_texts) < 2:
            derived = self._derived_resume_bullets(profile)
            bullet_texts = self._unique([*bullet_texts, *derived])[:2]
        no_metric = not self._has_quantified_result(profile)
        bullets = [
            ResumeBullet(
                bullet_text=self._sentence(text),
                evidence_trace=trace,
                confidence=profile.confidence,
                warnings=(
                    ["No quantified outcome is currently supported for this claim."]
                    if no_metric
                    else []
                ),
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
        bullets: list[str] = []
        if profile.workflow_steps:
            result = (
                "; " + self._lower_first(profile.findings_or_results[0])
                if profile.findings_or_results
                else ""
            )
            bullets.append(self._join_action_steps(profile.workflow_steps[:4]) + result)
        if profile.methods and profile.data_or_inputs:
            bullets.append(
                "Applied "
                + self._join(profile.methods[:4])
                + " to "
                + self._join(profile.data_or_inputs[:3])
            )
        if profile.research_question_or_problem and (
            profile.methods or profile.workflow_steps
        ):
            bullets.append("Investigated " + profile.research_question_or_problem)
        return bullets

    def _cover_letter(
        self,
        package: ApplicationPackage,
        ranked: list[_RankedProfile],
        warnings: list[ApplicationPackageWarning],
    ) -> CoverLetterDraft:
        primary = ranked[0]
        company_phrase = f" at {package.company}" if package.company else ""
        focus = self._target_focus(package, primary.profile)
        supported = self._supported_summary(primary.profile)
        if self._has_substantive_profile(primary.profile):
            opening = (
                f"I am applying for the {package.role_title} role{company_phrase}. "
                f"The role's focus on {focus} connects directly to my approved work "
                f"on {primary.profile.canonical_title}, where I developed documented "
                f"experience with {supported}."
            )
        else:
            opening = (
                f"I am applying for the {package.role_title} role{company_phrase}. "
                f"The approved record for {primary.profile.canonical_title} currently "
                "provides limited project context, so this draft does not treat it as "
                "proof of a stronger role-specific capability."
            )
        body_profiles = ranked[:2]
        body = [self._profile_narrative(item.profile) for item in body_profiles]
        if len(body) == 1 and primary.profile.workflow_steps:
            workflow = self._lower_first(
                self._join_action_steps(primary.profile.workflow_steps[:4])
            )
            finding = (
                " I kept the documented result modest: "
                + self._lower_first(primary.profile.findings_or_results[0])
                if primary.profile.findings_or_results
                else ""
            )
            body.append(f"I {workflow}.{finding}".strip())
        if self._has_substantive_profile(primary.profile):
            closing = (
                "I would welcome the opportunity to discuss how this documented "
                f"experience could support the responsibilities described for the "
                f"{package.role_title} role. Thank you for your consideration."
            )
        else:
            closing = (
                "Thank you for considering my application. I would welcome a "
                "conversation while keeping any stronger capability claims out until "
                "they are supported by reviewed evidence."
            )
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
        sentences: list[str] = []
        if profile.research_question_or_problem:
            sentences.append(
                f"My work on {profile.canonical_title} focused on "
                f"{self._problem_phrase(profile.research_question_or_problem)}"
            )
        else:
            sentences.append(
                f"My approved work on {profile.canonical_title} provides a concrete "
                "project example"
            )
        if profile.methods:
            method = self._join(profile.methods[:4])
            if profile.data_or_inputs:
                sentences.append(
                    f"I used {method} with {self._join(profile.data_or_inputs[:3])}"
                )
            else:
                sentences.append(f"I used {method}")
        if profile.findings_or_results:
            sentences.append(
                "The documented result was "
                + self._lower_first(profile.findings_or_results[0])
            )
        if profile.limitations:
            sentences.append(
                "I kept "
                + self._join(profile.limitations[:2])
                + " visible as limitations rather than overstating the conclusion"
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
                f"Use {primary.profile.canonical_title} only as limited approved "
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
                *primary.profile.skills_demonstrated[:4],
                *primary.profile.methods[:3],
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
    ) -> list[ApplicationSnippet]:
        primary = ranked[0]
        profile = primary.profile
        trace = self._claim_trace_for_profile(profile)
        target_trace = self._target_context_trace(package)
        bullet = self._resume_group(primary).bullets
        fit_text = (
            bullet[0].bullet_text if bullet else self._profile_evidence_summary(profile)
        )
        if profile.limitations:
            challenge = (
                f"One challenge in {profile.canonical_title} was accounting for "
                f"{self._join(profile.limitations[:2])}. I kept that limitation "
                "visible in the interpretation instead of overstating the result."
            )
        elif profile.workflow_steps or profile.methods:
            workflow = self._lower_first(
                self._join_action_steps((profile.workflow_steps or profile.methods)[:3])
            )
            challenge = (
                f"In {profile.canonical_title}, I {workflow}. "
                "Those documented steps describe how I approached the review process."
            )
        else:
            challenge = (
                f"The approved record for {profile.canonical_title} is still sparse. "
                "Before making a stronger challenge claim, I would add reviewed "
                "evidence about the methods used and the result."
            )
        technical = self._supported_summary(profile)
        has_technical_detail = bool(
            profile.skills_demonstrated or profile.methods or profile.tools
        )
        common_warnings = [
            item.message
            for item in warnings
            if item.severity != ApplicationWarningSeverity.INFO
        ][:2]
        if not has_technical_detail:
            return [
                ApplicationSnippet(
                    question="Why are you interested in this role?",
                    text=(
                        f"I am interested in the {package.role_title} role. The "
                        f"approved record for {profile.canonical_title} is currently "
                        "too limited to present as proof of the requested skills."
                    ),
                    evidence_trace=[target_trace, *trace],
                    warnings=common_warnings,
                ),
                ApplicationSnippet(
                    question="Why are you a good fit?",
                    text=(
                        f"The approved record for {profile.canonical_title} provides "
                        "project context, but I would add reviewed evidence before "
                        "making a stronger fit claim."
                    ),
                    evidence_trace=trace,
                    warnings=common_warnings,
                ),
                ApplicationSnippet(
                    question="Describe a relevant project.",
                    text=(
                        f"The approved record for {profile.canonical_title} is sparse. "
                        "It does not yet document enough method or result detail for a "
                        "stronger project claim."
                    ),
                    evidence_trace=trace,
                    warnings=common_warnings,
                ),
                ApplicationSnippet(
                    question="Tell us about a challenge.",
                    text=challenge,
                    evidence_trace=trace,
                    warnings=common_warnings,
                ),
                ApplicationSnippet(
                    question="What technical skills would you bring?",
                    text=(
                        f"My approved record currently supports the project context "
                        f"for {profile.canonical_title}, but not a stronger "
                        "tool-specific technical claim yet."
                    ),
                    evidence_trace=trace,
                    warnings=common_warnings,
                ),
            ]
        return [
            ApplicationSnippet(
                question="Why are you interested in this role?",
                text=(
                    f"I am interested in the {package.role_title} role because its "
                    f"focus on {self._target_focus(package, profile)} aligns with "
                    "the kind of "
                    f"work I practiced in {profile.canonical_title}: {technical}."
                ),
                evidence_trace=[target_trace, *trace],
                warnings=common_warnings,
            ),
            ApplicationSnippet(
                question="Why are you a good fit?",
                text=(
                    f"I would bring documented experience from "
                    f"{profile.canonical_title}. {fit_text}"
                ),
                evidence_trace=trace,
                warnings=common_warnings,
            ),
            ApplicationSnippet(
                question="Describe a relevant project.",
                text=self._profile_narrative(profile),
                evidence_trace=trace,
                warnings=common_warnings,
            ),
            ApplicationSnippet(
                question="Tell us about a challenge.",
                text=challenge,
                evidence_trace=trace,
                warnings=common_warnings,
            ),
            ApplicationSnippet(
                question="What technical skills would you bring?",
                text=(
                    "The strongest technical areas supported by my approved project "
                    f"evidence are {technical}, demonstrated through "
                    f"{profile.canonical_title}."
                    if has_technical_detail
                    else (
                        f"My approved record currently supports the project context "
                        f"for {profile.canonical_title}, but not a stronger "
                        "tool-specific technical claim yet."
                    )
                ),
                evidence_trace=trace,
                warnings=common_warnings,
            ),
        ]

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
                            "approved memory used in the package."
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
                            "Build a short case study from this approved memory for an "
                            "optional portfolio or application upload."
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
                    f"Can you add approved evidence for "
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
        factual_text = " ".join(
            self._profile_capability_text(item.profile) for item in ranked
        )
        requirements = self._requested_requirements(package)
        unsupported = [
            label
            for label, support_patterns in requirements
            if not self._patterns_supported(factual_text, support_patterns)
        ]
        warnings: list[ApplicationPackageWarning] = []
        for requirement in unsupported:
            if requirement == "production ML deployment":
                message = (
                    "The job asks for production ML deployment, but no approved "
                    "memory currently supports deployment."
                )
            elif requirement in {"AWS", "Azure", "GCP", "cloud infrastructure"}:
                message = (
                    f"The job asks for {requirement}, but no approved memory currently "
                    "supports that cloud experience."
                )
            else:
                message = (
                    f"The target asks for {requirement}, but the selected approved "
                    "memory does not currently support that claim."
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
                            f"{item.profile.canonical_title} has limited approved "
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
        for index, evidence in enumerate(profile.evidence_used):
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
                    trace_id=f"{profile.memory_id}-proof-{index}-{evidence.evidence_id}",
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
    ) -> list[ApplicationClaimLedgerEntry]:
        edited_claim_ids = edited_claim_ids or set()
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
            entries.append(
                self._ledger_entry(
                    f"cover-letter-{index}",
                    "cover_letter",
                    paragraph.paragraph_text,
                    paragraph.evidence_trace,
                    outputs.cover_letter.warnings,
                    user_edited=(f"cover-letter-{index}" in edited_claim_ids),
                )
            )
        for index, snippet in enumerate(outputs.application_snippets, start=1):
            entries.append(
                self._ledger_entry(
                    f"snippet-{index}",
                    "snippet",
                    snippet.text,
                    snippet.evidence_trace,
                    snippet.warnings,
                    user_edited=f"snippet-{index}" in edited_claim_ids,
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
        target_lower = target_text.casefold()
        bonus = 0.0
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
            bonus = 0.35
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
            bonus = 0.35
        score = round(min(overlap * 0.55 + profile.confidence * 0.25 + bonus, 1), 3)
        supported = self._supported_summary(profile)
        if bonus:
            reason = (
                f"{profile.canonical_title} is a strong role match because approved "
                f"evidence supports {supported}."
            )
        elif overlap:
            reason = (
                f"Approved evidence from {profile.canonical_title} overlaps with the "
                f"target through {supported}."
            )
        else:
            reason = (
                f"{profile.canonical_title} supplies approved supporting context, "
                "though its target overlap is limited."
            )
        return _RankedProfile(profile=profile, score=score, target_reason=reason)

    def _supported_summary(self, profile: CompiledCareerMemoryProfile) -> str:
        values = self._unique(
            [
                *profile.skills_demonstrated[:4],
                *profile.methods[:4],
                *profile.tools[:2],
            ]
        )
        if values:
            return self._join(values[:5])
        return "limited approved project context"

    @staticmethod
    def _has_substantive_profile(profile: CompiledCareerMemoryProfile) -> bool:
        return bool(
            profile.skills_demonstrated
            or profile.methods
            or profile.workflow_steps
            or profile.resume_bullet_claims
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
        parts: list[str] = []
        if profile.data_or_inputs:
            parts.append(self._join(profile.data_or_inputs[:3]))
        if profile.methods:
            parts.append(self._join(profile.methods[:4]))
        if profile.findings_or_results:
            parts.append(profile.findings_or_results[0])
        detail = "; ".join(parts) or "approved project context"
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
            created_at=package.created_at,
            updated_at=package.updated_at,
        )

    def _version_view(
        self,
        version: ApplicationPackageVersion,
    ) -> ApplicationPackageVersionView:
        return ApplicationPackageVersionView(
            id=version.id,
            package_id=version.package_id,
            version_number=version.version_number,
            target_snapshot=version.target_snapshot_json,
            selected_memory_ids=self._uuid_list(version.selected_memory_ids_json),
            input_fingerprint=version.input_fingerprint,
            outputs=ApplicationPackageOutputs.model_validate(
                version.generated_outputs_json
            ),
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
            created_at=version.created_at,
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
            r"(?:use|used|built|build|deploy\w*|develop\w*|implement\w*|"
            r"manage\w*|lead|led|train\w*|automat\w*|bring|experience|"
            r"proficien\w*|skill\w*|worked)"
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
    def _profile_capability_text(
        cls,
        profile: CompiledCareerMemoryProfile,
    ) -> str:
        return cls._positive_text(
            [
                *profile.data_or_inputs,
                *profile.methods,
                *profile.tools,
                *profile.workflow_steps,
                *profile.findings_or_results,
                *profile.outputs,
                *profile.skills_demonstrated,
                *profile.proof_claims,
                *profile.resume_bullet_claims,
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

    @staticmethod
    def _has_quantified_result(profile: CompiledCareerMemoryProfile) -> bool:
        result_text = " ".join(profile.findings_or_results)
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

    @classmethod
    def _problem_phrase(cls, value: str) -> str:
        cleaned = " ".join(value.split()).strip().rstrip(".")
        cleaned = re.sub(
            r"^(?:the\s+)?project\s+(?:focused|focuses)\s+on\s+",
            "",
            cleaned,
            flags=re.I,
        )
        return cls._lower_first(cleaned)

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
        return cls._join(
            [values[0], *(cls._lower_first(value) for value in values[1:])]
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

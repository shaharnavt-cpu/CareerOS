"""Deterministic, approved-memory-only Proof Artifact Builder."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    CanonicalMemoryRecord,
    CareerFeedbackEvent,
    DiagnosisResult,
    ListeningEvidence,
    ListeningSource,
    ProofArtifact,
    ProofArtifactVersion,
    ReviewProposal,
)
from app.schemas.career_memory import (
    CompiledCareerMemoryProfile,
    CompiledEvidenceKind,
)
from app.schemas.diagnosis import FeedbackEventStatus, FeedbackEventType
from app.schemas.knowledge import DEMO_USER_ID, DurableReviewStatus
from app.schemas.proof_artifacts import (
    ProofArtifactCreateRequest,
    ProofArtifactRegenerateRequest,
    ProofArtifactStatus,
    ProofArtifactType,
    ProofArtifactUpdateRequest,
    ProofArtifactVersionUpdateRequest,
    ProofArtifactVersionView,
    ProofArtifactView,
    ProofEvidenceReference,
    ProofMemoryOption,
    ProofOutcomeSignal,
    ProofReadinessLabel,
    ProofTargetAudience,
)
from app.services.career_diagnosis import CareerFeedbackService
from app.services.career_memory_compiler import (
    CareerMemoryCompilationError,
    CareerMemoryCompiler,
)


class ProofArtifactNotFoundError(LookupError):
    """Raised when a user-scoped proof artifact object is unavailable."""


class ProofArtifactValidationError(ValueError):
    """Raised when generation would cross the approved-memory trust boundary."""


@dataclass(frozen=True)
class GeneratedProof:
    title: str
    claim: str
    content: str
    sections: dict[str, Any]
    evidence_ids: list[str]
    outcome_signal_ids: list[str]
    warnings: list[str]
    readiness_score: float
    readiness_label: ProofReadinessLabel
    supporting_variants: dict[str, Any]


class ProofArtifactService:
    """Create durable, role-specific proof without an LLM dependency."""

    generator_version = "local-deterministic-proof-v0"

    def __init__(
        self,
        user_id: uuid.UUID = DEMO_USER_ID,
        compiler: CareerMemoryCompiler | None = None,
    ) -> None:
        self.user_id = user_id
        self.compiler = compiler or CareerMemoryCompiler(user_id=user_id)

    def list_eligible_memories(self, session: Session) -> list[ProofMemoryOption]:
        memories = session.scalars(
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
            )
            .order_by(CanonicalMemoryRecord.updated_at.desc())
        ).all()
        options: list[ProofMemoryOption] = []
        for memory in memories:
            profile = self.compiler.compile(session, memory.id)
            references = self._compiled_evidence_references(profile)
            options.append(
                ProofMemoryOption(
                    id=memory.id,
                    title=memory.title,
                    memory_type=memory.memory_type,
                    evidence_count=len(references),
                    evidence_ids=profile.evidence_ids_used,
                    source_labels=list(
                        dict.fromkeys(item["source_label"] for item in references)
                    ),
                    confidence=float(memory.confidence),
                )
            )
        return options

    def create(
        self, session: Session, request: ProofArtifactCreateRequest
    ) -> ProofArtifactView:
        memory = self._get_memory(session, request.source_memory_id)
        diagnosis = self._get_diagnosis(
            session, request.source_diagnosis_result_id, memory.id
        )
        generated = self._generate(
            session,
            memory,
            request.target_role,
            request.target_audience,
            request.artifact_type,
            diagnosis,
        )
        artifact = ProofArtifact(
            user_id=self.user_id,
            title=generated.title,
            artifact_type=request.artifact_type.value,
            target_role=request.target_role,
            target_audience=request.target_audience.value,
            source_memory_id=memory.id,
            source_diagnosis_result_id=diagnosis.id if diagnosis else None,
            status=ProofArtifactStatus.DRAFT.value,
        )
        session.add(artifact)
        session.flush()
        session.add(self._version_record(artifact.id, 1, generated))
        session.commit()
        return self.get(session, artifact.id)

    def list(self, session: Session) -> list[ProofArtifactView]:
        records = session.scalars(
            select(ProofArtifact)
            .where(ProofArtifact.user_id == self.user_id)
            .order_by(ProofArtifact.updated_at.desc())
        ).all()
        return [self._view(session, record) for record in records]

    def get(self, session: Session, artifact_id: uuid.UUID) -> ProofArtifactView:
        return self._view(session, self._get_artifact(session, artifact_id))

    def regenerate(
        self,
        session: Session,
        artifact_id: uuid.UUID,
        request: ProofArtifactRegenerateRequest,
    ) -> ProofArtifactView:
        artifact = self._get_artifact(session, artifact_id, lock=True)
        memory = self._get_memory(session, artifact.source_memory_id)
        target_role = request.target_role or artifact.target_role
        target_audience = request.target_audience or ProofTargetAudience(
            artifact.target_audience
        )
        artifact_type = request.artifact_type or ProofArtifactType(
            artifact.artifact_type
        )
        diagnosis = self._get_diagnosis(
            session, artifact.source_diagnosis_result_id, memory.id
        )
        if target_role != artifact.target_role:
            diagnosis = None
            artifact.source_diagnosis_result_id = None
        generated = self._generate(
            session,
            memory,
            target_role,
            target_audience,
            artifact_type,
            diagnosis,
        )
        next_version = (
            int(
                session.scalar(
                    select(func.max(ProofArtifactVersion.version_number)).where(
                        ProofArtifactVersion.artifact_id == artifact.id
                    )
                )
                or 0
            )
            + 1
        )
        artifact.title = generated.title
        artifact.target_role = target_role
        artifact.target_audience = target_audience.value
        artifact.artifact_type = artifact_type.value
        artifact.status = ProofArtifactStatus.DRAFT.value
        artifact.updated_at = datetime.now(UTC)
        session.add(self._version_record(artifact.id, next_version, generated))
        session.commit()
        return self.get(session, artifact.id)

    def update(
        self,
        session: Session,
        artifact_id: uuid.UUID,
        request: ProofArtifactUpdateRequest,
    ) -> ProofArtifactView:
        artifact = self._get_artifact(session, artifact_id)
        if (
            request.target_role is not None
            and request.target_role != artifact.target_role
        ):
            raise ProofArtifactValidationError(
                "Regenerate the artifact to change its target role so the saved "
                "claim and role framing stay consistent."
            )
        if (
            request.target_audience is not None
            and request.target_audience.value != artifact.target_audience
        ):
            raise ProofArtifactValidationError(
                "Regenerate the artifact to change its target audience so the saved "
                "usage guidance stays consistent."
            )
        if request.title is not None:
            latest = self._latest_version(session, artifact.id)
            self.update_version(
                session,
                artifact.id,
                latest.id,
                ProofArtifactVersionUpdateRequest(title=request.title),
            )
            artifact = self._get_artifact(session, artifact_id)
        if request.status is not None:
            artifact.status = request.status.value
        session.commit()
        return self.get(session, artifact.id)

    def update_version(
        self,
        session: Session,
        artifact_id: uuid.UUID,
        version_id: uuid.UUID,
        request: ProofArtifactVersionUpdateRequest,
    ) -> ProofArtifactView:
        artifact = self._get_artifact(session, artifact_id)
        latest = self._latest_version(session, artifact.id)
        if latest.id != version_id:
            raise ProofArtifactValidationError(
                "Only the latest proof artifact version can be edited."
            )
        version = session.scalar(
            select(ProofArtifactVersion).where(
                ProofArtifactVersion.id == version_id,
                ProofArtifactVersion.artifact_id == artifact.id,
                ProofArtifactVersion.user_id == self.user_id,
            )
        )
        if version is None:
            raise ProofArtifactNotFoundError("Proof artifact version not found.")
        requested_section_title = self._text_section(
            request.structured_sections or {}, "title"
        )
        requested_section_claim = self._text_section(
            request.structured_sections or {}, "target_claim"
        )
        if request.content is not None:
            version.content = request.content
        if request.structured_sections is not None:
            protected_sections = {
                key: version.structured_sections.get(key)
                for key in (
                    "compiled_profile",
                    "enrichment_ids_used",
                    "evidence_used",
                    "generator_version",
                    "outcome_signal_ids_used",
                    "outcome_signals",
                )
            }
            version.structured_sections = {
                **version.structured_sections,
                **request.structured_sections,
                **protected_sections,
            }
        if request.supporting_variants is not None:
            version.supporting_variants = {
                **version.supporting_variants,
                **request.supporting_variants,
            }

        content_title = self._markdown_title(version.content)
        content_claim = self._markdown_section(version.content, "Target claim")
        section_title = self._text_section(version.structured_sections, "title")
        section_claim = self._text_section(version.structured_sections, "target_claim")
        next_title = (
            request.title
            or requested_section_title
            or (content_title if request.content is not None else None)
            or section_title
            or version.title
        )
        next_claim = (
            request.claim
            or requested_section_claim
            or (content_claim if request.content is not None else None)
            or section_claim
            or version.claim
        )
        self._set_version_title(artifact, version, next_title)
        self._set_version_claim(version, next_claim)

        if request.structured_sections is not None and request.content is None:
            version.content = self._primary_content(
                ProofArtifactType(artifact.artifact_type),
                self._render_case_study(version.structured_sections),
                version.supporting_variants,
            )
        elif request.content is None:
            version.content = self._replace_markdown_section(
                version.content, "Target claim", version.claim
            )
            version.content = self._replace_markdown_title(
                version.content, version.title
            )
        else:
            if request.title is not None or requested_section_title is not None:
                version.content = self._replace_markdown_title(
                    version.content, version.title
                )
            if request.claim is not None or requested_section_claim is not None:
                version.content = self._replace_markdown_section(
                    version.content, "Target claim", version.claim
                )

        memory = self._get_source_memory(session, artifact.source_memory_id)
        compiled_profile: CompiledCareerMemoryProfile | None = None
        try:
            compiled_profile = self.compiler.compile(
                session,
                memory.id,
                artifact.target_role,
            )
            approved_text = self._compiled_factual_text(compiled_profile)
            evidence_references = self._compiled_evidence_references(compiled_profile)
        except CareerMemoryCompilationError:
            stored_profile = version.structured_sections.get("compiled_profile")
            approved_text = (
                json.dumps(stored_profile, ensure_ascii=False)
                if isinstance(stored_profile, dict)
                else self._approved_text(session, memory)
            )
            stored_references = version.structured_sections.get("evidence_used")
            evidence_references = (
                stored_references if isinstance(stored_references, list) else []
            )
        editable_sections = {
            key: value
            for key, value in version.structured_sections.items()
            if key
            not in {
                "compiled_profile",
                "enrichment_ids_used",
                "evidence_used",
                "generator_version",
                "outcome_signal_ids_used",
                "outcome_signals",
            }
        }
        edited_text = " ".join(
            (
                version.title,
                version.claim,
                version.content,
                json.dumps(editable_sections, ensure_ascii=False),
                json.dumps(version.supporting_variants, ensure_ascii=False),
            )
        )
        unsupported_numbers = self._unsupported_numbers(
            edited_text,
            " ".join(
                (
                    approved_text,
                    artifact.target_role,
                    json.dumps(evidence_references, ensure_ascii=False),
                    " ".join(version.evidence_ids),
                    "30",
                )
            ),
        )
        warnings = [
            warning
            for warning in version.warnings
            if not warning.startswith("Edited text contains numeric claims")
        ]
        if unsupported_numbers:
            warnings.append(
                "Edited text contains numeric claims not found in approved memory; "
                f"verify or remove them: {', '.join(unsupported_numbers)}."
            )
            version.readiness_score = Decimal(
                str(min(float(version.readiness_score), 0.59))
            )
            version.readiness_label = ProofReadinessLabel.DRAFTABLE.value
        else:
            capabilities = self._capabilities(approved_text)
            method = self._text_section(version.structured_sections, "method") or ""
            documented_outcome = (
                self._compiled_outcome(compiled_profile)
                if compiled_profile is not None
                else self._documented_outcome(memory.structured_fields)
            )
            score, label = self._readiness(
                len(evidence_references),
                version.claim,
                method,
                capabilities,
                documented_outcome,
                artifact.target_role,
            )
            version.readiness_score = Decimal(str(score))
            version.readiness_label = label.value
        version.warnings = warnings
        artifact.updated_at = datetime.now(UTC)
        session.commit()
        return self.get(session, artifact.id)

    def _generate(
        self,
        session: Session,
        memory: CanonicalMemoryRecord,
        target_role: str,
        target_audience: ProofTargetAudience,
        artifact_type: ProofArtifactType,
        diagnosis: DiagnosisResult | None,
    ) -> GeneratedProof:
        profile = self.compiler.compile(session, memory.id, target_role)
        evidence_references = self._compiled_evidence_references(profile)
        approved_text = self._compiled_factual_text(profile)
        capabilities = (
            self._capabilities(approved_text)
            if profile.methods or profile.skills_demonstrated
            else []
        )
        documented_outcome = self._compiled_outcome(profile)
        outcome_signals = self._outcome_signals(session, memory, diagnosis)
        title = self._compiled_title(profile, target_role, approved_text)
        claim = self._target_claim(memory, target_role, capabilities)
        method = self._compiled_method(profile)
        problem = self._compiled_problem(profile)
        data_or_inputs = self._compiled_data_or_inputs(profile)
        outcome_or_insight = self._compiled_outcome_or_insight(
            profile,
            capabilities,
            approved_text,
        )
        role_relevance = profile.role_relevance or self._role_relevance(
            target_role, capabilities
        )
        limitations = self._compiled_limitations(profile)
        what_this_proves = self._compiled_what_this_proves(
            profile,
            memory,
            target_role,
            capabilities,
            approved_text,
        )
        context = self._compiled_context(
            profile,
            self._context(memory, capabilities, approved_text),
        )
        sections: dict[str, Any] = {
            "title": title,
            "target_claim": claim,
            "role_relevance": role_relevance,
            "context": context,
            "problem": problem,
            "data_or_inputs": data_or_inputs,
            "method": method,
            "evidence_used": evidence_references,
            "skills_demonstrated": capabilities,
            "outcome_or_insight": outcome_or_insight,
            "limitations": limitations,
            "what_this_proves": what_this_proves,
            "how_to_use": self._how_to_use(target_audience),
            "reviewer_question": self._reviewer_question(
                target_role,
                artifact_type,
                self._reviewer_project_kind(profile, capabilities),
            ),
            "outcome_signals": outcome_signals,
            "compiled_profile": profile.model_dump(mode="json"),
            "enrichment_ids_used": [str(item) for item in profile.enrichment_ids_used],
            "outcome_signal_ids_used": [
                str(item) for item in profile.outcome_signal_ids_used
            ],
            "generator_version": self.generator_version,
        }
        warnings = self._warnings(
            len(evidence_references),
            self._has_documented_metric({}, approved_text),
            documented_outcome,
            outcome_signals,
        )
        profile_warnings = [
            (
                "Do not claim methods or findings from another project."
                if profile.project_kind == "UNICORN"
                and "gas kinematics" in warning.casefold()
                else warning
            )
            for warning in profile.warnings_not_to_claim
        ]
        warnings = list(dict.fromkeys([*warnings, *profile_warnings]))
        readiness_score, readiness_label = self._readiness(
            len(evidence_references),
            claim,
            method,
            capabilities,
            documented_outcome,
            target_role,
        )
        variants = self._supporting_variants(
            memory,
            target_role,
            claim,
            method,
            outcome_or_insight,
            capabilities,
            problem,
            data_or_inputs,
            sections["what_this_proves"],
            limitations,
        )
        case_study_content = self._render_case_study(sections)
        content = self._primary_content(artifact_type, case_study_content, variants)
        return GeneratedProof(
            title=title,
            claim=claim,
            content=content,
            sections=sections,
            evidence_ids=profile.evidence_ids_used,
            outcome_signal_ids=[item["feedback_event_id"] for item in outcome_signals],
            warnings=warnings,
            readiness_score=readiness_score,
            readiness_label=readiness_label,
            supporting_variants=variants,
        )

    def _outcome_signals(
        self,
        session: Session,
        memory: CanonicalMemoryRecord,
        diagnosis: DiagnosisResult | None,
    ) -> list[dict[str, str]]:
        diagnosis_snapshots = {
            str(item.get("feedback_event_id")): item
            for item in (diagnosis.outcome_signals if diagnosis else [])
            if item.get("feedback_event_id")
        }
        diagnosis_ids = set(diagnosis_snapshots)
        events = session.scalars(
            select(CareerFeedbackEvent)
            .where(
                CareerFeedbackEvent.user_id == self.user_id,
                CareerFeedbackEvent.status == FeedbackEventStatus.APPROVED.value,
                CareerFeedbackEvent.event_type
                == FeedbackEventType.ARTIFACT_SUCCESS.value,
            )
            .order_by(CareerFeedbackEvent.updated_at.desc())
        ).all()
        signals: list[dict[str, str]] = []
        for event in events:
            event_id = str(event.id)
            directly_related = str(memory.id) in event.related_memory_ids
            if event_id not in diagnosis_ids and not directly_related:
                continue
            snapshot = diagnosis_snapshots.get(event_id, {})
            parsed = CareerFeedbackService.parse_note(event.raw_note)
            label = event.artifact_label or parsed.artifact_label or "artifact"
            summary = event.structured_summary or parsed.structured_summary
            guidance = str(event.suggested_future_use or parsed.suggested_future_use)
            signals.append(
                {
                    "feedback_event_id": event_id,
                    "summary": summary,
                    "guidance": guidance,
                    "caveat": str(
                        snapshot.get("caveat")
                        or (
                            "An approved outcome note suggests similar framing worked "
                            "once. This is a strategy signal, not proof of causality."
                        )
                    ),
                    "artifact_label": label,
                }
            )
        return signals

    def _evidence_references(
        self,
        session: Session,
        evidence_ids: list[str],
        source_ids: list[str],
    ) -> list[dict[str, str | None]]:
        references: list[dict[str, str | None]] = []
        for index, evidence_id in enumerate(evidence_ids):
            evidence = None
            try:
                evidence = session.get(ListeningEvidence, uuid.UUID(evidence_id))
            except (TypeError, ValueError):
                pass
            if evidence is None or evidence.user_id != self.user_id:
                continue
            source = None
            source = session.get(ListeningSource, evidence.source_id)
            if source is not None and source.user_id != self.user_id:
                source = None
            fallback_source = (
                source_ids[min(index, len(source_ids) - 1)] if source_ids else None
            )
            references.append(
                {
                    "evidence_id": evidence_id,
                    "source_label": (
                        source.label
                        if source is not None
                        else f"Approved source {fallback_source or index + 1}"
                    ),
                    "excerpt": evidence.raw_excerpt,
                }
            )
        return references

    def _approved_text(
        self,
        session: Session,
        memory: CanonicalMemoryRecord,
        evidence_references: list[dict[str, str | None]] | None = None,
    ) -> str:
        references = evidence_references or self._evidence_references(
            session, memory.evidence_ids, memory.source_ids
        )
        excerpts = " ".join(str(item.get("excerpt") or "") for item in references)
        return " ".join(
            [
                memory.title,
                json.dumps(memory.structured_fields, ensure_ascii=False),
                excerpts,
            ]
        )

    @staticmethod
    def _compiled_evidence_references(
        profile: CompiledCareerMemoryProfile,
    ) -> list[dict[str, str | None]]:
        """Render compiler provenance without counting the memory row as a source."""

        references: list[dict[str, str | None]] = []
        seen: set[str] = set()
        for item in profile.evidence_used:
            if item.kind is CompiledEvidenceKind.CANONICAL_MEMORY:
                continue
            if item.evidence_id in seen:
                continue
            seen.add(item.evidence_id)
            references.append(
                {
                    "evidence_id": item.evidence_id,
                    "source_label": item.source_label,
                    "excerpt": item.excerpt,
                }
            )
        return references

    @staticmethod
    def _compiled_factual_text(profile: CompiledCareerMemoryProfile) -> str:
        """Build keyword input from factual compiler buckets, never target context."""

        factual = {
            "research_question_or_problem": profile.research_question_or_problem,
            "data_or_inputs": profile.data_or_inputs,
            "methods": profile.methods,
            "tools": profile.tools,
            "workflow_steps": profile.workflow_steps,
            "findings_or_results": profile.findings_or_results,
            "limitations": profile.limitations,
            "outputs": profile.outputs,
            "collaborators_or_context": profile.collaborators_or_context,
            "skills_demonstrated": profile.skills_demonstrated,
            "proof_claims": profile.proof_claims,
            "resume_bullet_claims": profile.resume_bullet_claims,
        }
        return json.dumps(factual, ensure_ascii=False)

    @classmethod
    def _compiled_title(
        cls,
        profile: CompiledCareerMemoryProfile,
        target_role: str,
        approved_text: str,
    ) -> str:
        target = target_role.casefold()
        if (
            profile.project_kind == "GAS_KINEMATICS"
            and re.search(r"\bdata scientist\b", target)
            and cls._is_rich_gas_profile(profile)
        ):
            return (
                "Data Science Case Study: Testing Galaxy Morphology with JWST "
                "Spectroscopy and Imaging"
            )
        if (
            profile.project_kind == "UNICORN"
            and cls._is_ai_target(target_role)
            and cls._is_rich_unicorn_profile(profile)
        ):
            return (
                "AI/Data Workflow Case Study: Image Inspection and Categorization "
                "in the UNICORN Project"
            )
        approved = approved_text.casefold()
        if cls._is_analytics_target(target_role):
            if (
                "spectral" in approved
                and "imaging" in approved
                and "morpholog" in approved
                and re.search(r"\bgalax(?:y|ies)\b", approved)
            ):
                return (
                    "Data Analytics Case Study: Modeling Galaxy Morphology from "
                    "Spectral and Imaging Data"
                )
            return f"Data Analytics Case Study: {profile.canonical_title}"
        if cls._is_ai_target(target_role):
            return f"AI / Automation Proof Case Study: {profile.canonical_title}"
        return f"Role-Specific Case Study: {profile.canonical_title}"

    @staticmethod
    def _is_rich_gas_profile(profile: CompiledCareerMemoryProfile) -> bool:
        text = " ".join(
            [*profile.data_or_inputs, *profile.methods, *profile.tools]
        ).casefold()
        return (
            "nirspec" in text
            and "nircam" in text
            and ("h-alpha" in text or "galfit" in text)
        )

    @staticmethod
    def _is_rich_unicorn_profile(profile: CompiledCareerMemoryProfile) -> bool:
        methods = set(profile.methods)
        inputs = " ".join(profile.data_or_inputs).casefold()
        return bool(
            re.search(r"image|imag|fits|inspection plot|detection", inputs)
            and "categorization and labeling" in methods
            and methods.intersection(
                {
                    "manual inspection of plots and images",
                    "detection review",
                }
            )
            and methods.intersection(
                {
                    "t-SNE exploratory organization",
                    "visual-feature grouping and sorting",
                }
            )
        )

    @classmethod
    def _compiled_method(
        cls,
        profile: CompiledCareerMemoryProfile,
    ) -> str:
        if profile.project_kind == "GAS_KINEMATICS" and cls._is_rich_gas_profile(
            profile
        ):
            steps = profile.workflow_steps or profile.methods
            if steps:
                return " ".join(steps)
        if profile.project_kind == "UNICORN" and cls._is_rich_unicorn_profile(
            profile
        ):
            return (
                "The workflow combined "
                f"{cls._join(profile.methods)} to organize and review the supported "
                "image data."
            )
        if profile.methods:
            return f"The documented workflow used {cls._join(profile.methods)}."
        if profile.workflow_steps:
            return (
                "The documented workflow included "
                f"{cls._join(profile.workflow_steps)}"
            )
        return (
            "The approved evidence does not yet describe a method clearly enough "
            "for this work sample."
        )

    @classmethod
    def _compiled_problem(
        cls,
        profile: CompiledCareerMemoryProfile,
    ) -> str:
        problem = profile.research_question_or_problem
        if problem and profile.project_kind == "GAS_KINEMATICS":
            compiled = " ".join(
                [problem, *profile.data_or_inputs, *profile.methods]
            ).casefold()
            has_spectral_and_imaging = (
                "spectral" in compiled and "imaging" in compiled
            )
            if has_spectral_and_imaging and "morpholog" in compiled:
                if "rotational" in compiled and "velocity dispersion" in compiled:
                    return (
                        "The project tested whether spectral and imaging data could "
                        "be used to study relationships between galaxy morphology "
                        "and rotational velocity dispersion."
                    )
                if "kinematic" in compiled:
                    return (
                        "The project tested how spectral and imaging observations "
                        "could be used to study relationships between galaxy "
                        "morphology and kinematics."
                    )
        if problem:
            return problem
        return (
            "The approved evidence does not yet state the project question or "
            "problem clearly enough for this work sample."
        )

    @classmethod
    def _compiled_data_or_inputs(
        cls,
        profile: CompiledCareerMemoryProfile,
    ) -> str:
        if profile.data_or_inputs:
            return f"The project used {cls._join(profile.data_or_inputs)}."
        return (
            "The approved evidence does not yet describe the project inputs in "
            "enough detail for this work sample."
        )

    @classmethod
    def _compiled_outcome_or_insight(
        cls,
        profile: CompiledCareerMemoryProfile,
        capabilities: list[str],
        approved_text: str,
    ) -> str:
        finding = cls._compiled_outcome(profile)
        if profile.project_kind == "GAS_KINEMATICS" and finding:
            return (
                f"{finding} The artifact presents this as careful hypothesis testing "
                "rather than failure and does not force the evidence into a "
                "conclusive claim."
            )
        if profile.project_kind == "UNICORN" and cls._is_rich_unicorn_profile(
            profile
        ):
            if finding:
                return finding
            return (
                "The supported evidence documents an image-review and data-quality "
                "workflow; it does not yet support a quantified outcome."
            )
        if finding:
            return finding
        if capabilities:
            return cls._outcome_or_insight(capabilities, approved_text)
        return (
            "The approved evidence does not yet document a supported finding or "
            "outcome."
        )

    @classmethod
    def _compiled_outcome(
        cls,
        profile: CompiledCareerMemoryProfile,
    ) -> str | None:
        if not profile.findings_or_results:
            return None
        return " ".join(item.rstrip(". ") + "." for item in profile.findings_or_results)

    @classmethod
    def _compiled_limitations(
        cls,
        profile: CompiledCareerMemoryProfile,
    ) -> str:
        if profile.limitations:
            return " ".join(item.rstrip(". ") + "." for item in profile.limitations)
        findings = " ".join(profile.findings_or_results).casefold()
        if profile.project_kind == "GAS_KINEMATICS" and (
            "no clear" in findings or "inconclusive" in findings
        ):
            return (
                "The approved evidence does not support a conclusive trend; the "
                "result should be presented as bounded, inconclusive analysis."
            )
        return (
            "The approved evidence does not yet document project limitations in "
            "enough detail for a final work sample."
        )

    @classmethod
    def _compiled_context(
        cls,
        profile: CompiledCareerMemoryProfile,
        fallback: str,
    ) -> str:
        if profile.project_kind not in {"GAS_KINEMATICS", "UNICORN"}:
            return fallback
        # The compiler retains an explicit negative boundary for provenance and
        # safeguards. Case-study prose should describe the selected project itself,
        # without introducing the other project's name as if it were project detail.
        boundary = re.sub(
            r"\s*Separate from (?:Gas Kinematics|UNICORN)\.?",
            "",
            profile.project_boundary,
            flags=re.IGNORECASE,
        ).strip()
        normalized_boundary = boundary.casefold()
        context_items: list[str] = []
        for item in profile.collaborators_or_context:
            normalized = item.casefold()
            if "gas kinematics" in normalized or "unicorn" in normalized:
                continue
            if (
                "honors capstone" in normalized_boundary
                and "honors capstone" in normalized
            ):
                continue
            if "gevip" in normalized_boundary and "gevip" in normalized:
                continue
            context_items.append(item.rstrip(". ") + ".")
        return " ".join(item for item in (boundary, *context_items) if item)

    @classmethod
    def _compiled_what_this_proves(
        cls,
        profile: CompiledCareerMemoryProfile,
        memory: CanonicalMemoryRecord,
        target_role: str,
        capabilities: list[str],
        approved_text: str,
    ) -> str:
        if profile.project_kind == "GAS_KINEMATICS" and cls._is_rich_gas_profile(
            profile
        ):
            return (
                "This case study shows the ability to debug messy data, test "
                "hypotheses, validate assumptions, reason about uncertainty, and "
                "communicate a nuanced result without overclaiming."
            )
        if profile.project_kind == "UNICORN" and cls._is_rich_unicorn_profile(
            profile
        ):
            return (
                "This case study shows image-data quality judgment, labeling and "
                "categorization workflow thinking, exploratory ML reasoning, and "
                "human-in-the-loop review without claiming a deployed model."
            )
        if not capabilities and not profile.skills_demonstrated:
            return (
                "Approved evidence is not yet detailed enough to support a "
                f"role-specific capability claim for {target_role}."
            )
        return cls._what_this_proves(
            memory,
            target_role,
            capabilities,
            approved_text,
        )

    @staticmethod
    def _capabilities(approved_text: str) -> list[str]:
        text = approved_text.casefold()
        rules = [
            ("data analysis", ("data analysis", "analyz", "analys", "dataset")),
            ("Python", ("python",)),
            ("Gaussian fitting", ("gaussian fit", "gaussian fitting")),
            (
                "statistical modeling",
                (
                    "statistical model",
                    "statistical modeling",
                    "statistical modelling",
                    "regression analysis",
                ),
            ),
            ("modeling", ("modeling", "modelling")),
            (
                "uncertainty and error propagation",
                ("uncertainty", "error propagation", "propagated error"),
            ),
            ("data visualization", ("visualization", "visualisation", "plotting")),
            (
                "technical communication",
                ("presented", "presentation", "conference", "communicat", "poster"),
            ),
            ("research reasoning", ("research", "hypothesis", "investigat")),
            (
                "image inspection",
                ("image inspection", "inspection of plots and images"),
            ),
            ("detection review", ("detection review", "reviewed detections")),
            (
                "labeling and categorization",
                ("categorization and labeling", "labeling workflow"),
            ),
            ("t-SNE exploration", ("t-sne", "t-distributed stochastic")),
            (
                "data-quality judgment",
                ("data quality", "data-quality", "hot pixels", "spurious detections"),
            ),
            ("human-in-the-loop review", ("human-in-the-loop",)),
            ("technical documentation", ("technical documentation",)),
        ]
        capabilities = [
            label for label, terms in rules if any(term in text for term in terms)
        ]
        if "statistical modeling" in capabilities and "modeling" in capabilities:
            capabilities.remove("modeling")
        return capabilities

    @classmethod
    def _target_claim(
        cls,
        memory: CanonicalMemoryRecord,
        target_role: str,
        capabilities: list[str],
    ) -> str:
        phrases = {
            "data analysis": "analyze complex data",
            "Python": "use Python",
            "Gaussian fitting": "apply Gaussian fitting",
            "statistical modeling": "apply statistical modeling",
            "modeling": "apply modeling",
            "uncertainty and error propagation": "reason about uncertainty",
            "data visualization": "make findings visually inspectable",
            "technical communication": "communicate technical findings clearly",
            "research reasoning": "structure evidence-based research questions",
            "image inspection": "inspect image data carefully",
            "detection review": "review detection candidates",
            "labeling and categorization": (
                "design labeling and categorization workflows"
            ),
            "t-SNE exploration": "use t-SNE for exploratory organization",
            "data-quality judgment": "reason about data quality",
            "human-in-the-loop review": "support human-in-the-loop review",
            "technical documentation": "document technical workflows",
        }
        supported = [phrases[item] for item in capabilities if item in phrases][:4]
        if not supported:
            return (
                f"This artifact makes the documented work in {memory.title} "
                f"inspectable for {target_role}."
            )
        return (
            f"This project demonstrates my ability to {cls._join(supported)} for "
            f"{target_role}."
        )

    @classmethod
    def _method(
        cls,
        memory: CanonicalMemoryRecord,
        capabilities: list[str],
        approved_text: str,
    ) -> str:
        direct = cls._field_text(
            memory.structured_fields,
            "enriched_method",
            "method",
            "methods",
            "methodology",
            "approach",
            "process",
        )
        if cls._is_galaxy_analytics_case(approved_text):
            text = approved_text.casefold()
            phrases: list[str] = []
            if "data analysis" in capabilities:
                phrases.append(
                    "statistical analysis"
                    if "statistical analys" in text
                    else "data analysis"
                )
            if "statistical modeling" in capabilities:
                phrases.append("statistical modeling")
            elif "modeling" in capabilities:
                phrases.append("modeling")
            phrases.extend(
                phrase
                for capability, phrase in (
                    ("Gaussian fitting", "Gaussian fitting"),
                    (
                        "uncertainty and error propagation",
                        "uncertainty and error propagation",
                    ),
                    ("data visualization", "data visualization"),
                    ("technical communication", "technical communication"),
                )
                if capability in capabilities
            )
            if phrases:
                return (
                    f"I used {cls._join(phrases)} to interpret complex spectral "
                    "and imaging data."
                )
        if direct:
            return direct
        if capabilities:
            return (
                f"I applied {cls._join(capabilities[:5])} to complete the documented "
                "project work and communicate the result."
            )
        return (
            "The method needs one more source-backed description before this work "
            "sample is ready to share."
        )

    @classmethod
    def _problem(
        cls,
        memory: CanonicalMemoryRecord,
        evidence_references: list[dict[str, str | None]],
        approved_text: str,
    ) -> str:
        direct = cls._field_text(
            memory.structured_fields,
            "enriched_problem",
            "problem",
            "objective",
            "research_question",
            "research question",
            "goal",
            "summary",
            "description",
        )
        if cls._is_galaxy_analytics_case(approved_text):
            text = approved_text.casefold()
            if "rotational" in text and "velocity dispersion" in text:
                return (
                    "The project tested whether spectral and imaging data could be "
                    "used to study relationships between galaxy morphology and "
                    "rotational velocity dispersion."
                )
            return (
                "The project tested how spectral and imaging observations could be "
                "used to study relationships between galaxy morphology and kinematics."
            )
        if direct:
            return direct
        for reference in evidence_references:
            excerpt = str(reference.get("excerpt") or "").strip()
            if excerpt and any(
                term in excerpt.casefold()
                for term in ("research", "investigat", "analy", "study", "model")
            ):
                return excerpt
        return (
            f"{memory.title} is documented, but the project question needs one clearer "
            "source-backed sentence before this work sample is ready to share."
        )

    @classmethod
    def _data_or_inputs(cls, memory: CanonicalMemoryRecord, approved_text: str) -> str:
        direct = cls._field_text(
            memory.structured_fields,
            "enriched_data_or_inputs",
            "data",
            "dataset",
            "datasets",
            "inputs",
            "data_or_inputs",
            "materials",
        )
        if direct:
            return direct
        text = approved_text.casefold()
        descriptors = [
            label
            for label, term in (
                ("spectral data", "spectral"),
                ("imaging data", "imaging"),
                ("survey data", "survey data"),
                ("observational data", "observational"),
            )
            if term in text
        ]
        if descriptors:
            return (
                f"The analysis used {cls._join(descriptors)} documented in the "
                "project evidence."
            )
        return (
            "The available sources do not yet describe the inputs in enough detail "
            "for a final work sample."
        )

    @classmethod
    def _context(
        cls,
        memory: CanonicalMemoryRecord,
        capabilities: list[str],
        approved_text: str,
    ) -> str:
        enriched = cls._field_text(memory.structured_fields, "enriched_context")
        if enriched:
            return enriched
        if cls._is_galaxy_analytics_case(approved_text):
            project_kind = (
                "This honors capstone"
                if any(
                    term in approved_text.casefold() for term in ("honors", "capstone")
                )
                else "This research project"
            )
            focus = [
                label
                for capability, label in (
                    ("statistical modeling", "modeling"),
                    ("modeling", "modeling"),
                    (
                        "uncertainty and error propagation",
                        "uncertainty analysis",
                    ),
                    ("data visualization", "visualization"),
                    ("technical communication", "clear technical communication"),
                )
                if capability in capabilities
            ]
            suffix = f", with an emphasis on {cls._join(focus)}" if focus else ""
            return (
                f"{project_kind} applied data analysis to an astronomy research "
                f"question{suffix}."
            )
        return (
            f"{memory.title} is a documented "
            f"{cls._memory_type_label(memory.memory_type)} "
            "presented here as a concise, role-specific work sample."
        )

    @classmethod
    def _outcome_or_insight(cls, capabilities: list[str], approved_text: str) -> str:
        if cls._is_galaxy_analytics_case(approved_text):
            return (
                "The project demonstrates a repeatable analytical workflow: define "
                "the question, analyze technical data, account for uncertainty, and "
                "communicate findings clearly."
            )
        if capabilities:
            return (
                "The project demonstrates a repeatable workflow for applying "
                f"{cls._join(capabilities[:4])} and communicating the work clearly."
            )
        return "The project creates an inspectable record of the documented work."

    @staticmethod
    def _limitations(
        memory: CanonicalMemoryRecord,
        resolved_evidence_count: int,
        documented_outcome: str | None,
    ) -> str:
        enriched = ProofArtifactService._field_text(
            memory.structured_fields, "enriched_limitations"
        )
        if enriched:
            return enriched
        if not resolved_evidence_count:
            return (
                "The current draft needs a source that documents the method or result "
                "before it is ready to share."
            )
        if not documented_outcome:
            return (
                "The available evidence documents the process and communication of "
                "findings, but not a quantified outcome."
            )
        return (
            "The scope is limited to the methods and results documented by the cited "
            "sources."
        )

    @staticmethod
    def _role_relevance(target_role: str, capabilities: list[str]) -> str:
        if not capabilities:
            return (
                f"For {target_role}, the current value is an inspectable work sample; "
                "the role-relevant method still needs more approved detail."
            )
        return (
            f"For {target_role}, this project is most relevant as evidence of "
            f"{ProofArtifactService._join(capabilities[:5])}."
        )

    @staticmethod
    def _what_this_proves(
        memory: CanonicalMemoryRecord,
        target_role: str,
        capabilities: list[str],
        approved_text: str,
    ) -> str:
        if ProofArtifactService._is_galaxy_analytics_case(approved_text):
            return (
                "This case study shows that I can work with complex data, reason "
                "through uncertainty, and explain technical results in a way that "
                "supports decision-making."
            )
        if capabilities:
            return (
                f"This work sample shows how I applied "
                f"{ProofArtifactService._join(capabilities[:5])} in {memory.title}, "
                f"skills that transfer directly to {target_role}."
            )
        return (
            f"This makes {memory.title} reviewable for {target_role}, while making "
            "the missing method evidence explicit."
        )

    @staticmethod
    def _how_to_use(target_audience: ProofTargetAudience) -> list[str]:
        prioritized = {
            ProofTargetAudience.APPLICATION_UPLOAD: (
                "Attach it as an optional application work sample.",
                "Reference its target claim in the cover letter.",
            ),
            ProofTargetAudience.PORTFOLIO: (
                "Publish the reviewed version as a concise portfolio project page.",
                "Link directly to it from targeted applications.",
            ),
            ProofTargetAudience.GITHUB: (
                "Use the README outline to make the repository understandable quickly.",
                "Link the reviewed case study near the top of the repository.",
            ),
            ProofTargetAudience.OUTREACH: (
                "Use the outreach blurb in one personalized message.",
                "Link the full case study for optional context.",
            ),
            ProofTargetAudience.INTERVIEW_PREP: (
                "Practice the interview version without adding unsupported results.",
                "Use the evidence list to prepare follow-up details.",
            ),
            ProofTargetAudience.GENERAL: (
                "Link it in a targeted application or portfolio.",
                "Use the short variants in outreach and interview preparation.",
            ),
        }[target_audience]
        return [
            *prioritized,
            "Ask a target-aware reviewer whether the value is clear in 30 seconds.",
        ]

    @staticmethod
    def _reviewer_question(
        target_role: str,
        artifact_type: ProofArtifactType,
        project_kind: str,
    ) -> str:
        if artifact_type is ProofArtifactType.RESUME_BULLETS:
            return (
                "Does each resume bullet make the supported method and role-relevant "
                "skill clear without adding an unsupported outcome?"
            )
        if artifact_type is ProofArtifactType.GITHUB_README:
            return (
                "Can a reviewer understand the problem, inputs, workflow, and "
                "limitations from the README in the first 30 seconds?"
            )
        if project_kind == "GAS_KINEMATICS" and (
            ProofArtifactService._is_analytics_target(target_role)
        ):
            return (
                "Is it clear in the first 30 seconds that this project demonstrates "
                "data cleaning, modeling, validation, and uncertainty reasoning?"
            )
        if project_kind == "UNICORN" and ProofArtifactService._is_ai_target(
            target_role
        ):
            return (
                "Is it clear in the first 30 seconds that this project demonstrates "
                "data-quality and labeling workflow thinking for AI systems?"
            )
        if project_kind == "SPARSE":
            return (
                "Which approved problem, method, or result detail should be added "
                "before this artifact makes a role-specific capability claim?"
            )
        if project_kind == "GENERIC":
            return "Is the supported role-relevant value clear in the first 30 seconds?"
        if ProofArtifactService._is_ai_target(target_role):
            return (
                "Is the supported AI workflow, data-quality judgment, and human "
                "review value clear in the first 30 seconds?"
            )
        if ProofArtifactService._is_analytics_target(target_role):
            return (
                "Is the supported data preparation, analysis, validation, and "
                "communication value clear in the first 30 seconds?"
            )
        return "Is the role-relevant value clear in the first 30 seconds?"

    @classmethod
    def _reviewer_project_kind(
        cls,
        profile: CompiledCareerMemoryProfile,
        capabilities: list[str],
    ) -> str:
        if not capabilities and not profile.methods:
            return "SPARSE"
        if profile.project_kind == "GAS_KINEMATICS" and cls._is_rich_gas_profile(
            profile
        ):
            return "GAS_KINEMATICS"
        if profile.project_kind == "UNICORN" and cls._is_rich_unicorn_profile(
            profile
        ):
            return "UNICORN"
        return "GENERIC"

    @classmethod
    def _case_study_title(
        cls,
        memory: CanonicalMemoryRecord,
        target_role: str,
        approved_text: str,
    ) -> str:
        target = target_role.casefold()
        approved = approved_text.casefold()
        if cls._is_analytics_target(target):
            if (
                "spectral" in approved
                and "imaging" in approved
                and "morpholog" in approved
                and re.search(r"\bgalax(?:y|ies)\b", approved)
            ):
                return (
                    "Data Analytics Case Study: Modeling Galaxy Morphology from "
                    "Spectral and Imaging Data"
                )
            return f"Data Analytics Case Study: {memory.title}"
        if cls._is_ai_target(target):
            return f"AI / Automation Proof Case Study: {memory.title}"
        return f"Role-Specific Case Study: {memory.title}"

    @staticmethod
    def _is_analytics_target(target_role: str) -> bool:
        return bool(
            re.search(
                r"\b(?:data|analytics?|analyst|business intelligence)\b",
                target_role.casefold(),
            )
        )

    @staticmethod
    def _is_ai_target(target_role: str) -> bool:
        return bool(
            re.search(
                r"\b(?:ai|artificial intelligence|machine learning|automation)\b",
                target_role.casefold(),
            )
        )

    @staticmethod
    def _is_galaxy_analytics_case(approved_text: str) -> bool:
        text = approved_text.casefold()
        return (
            "spectral" in text
            and "imaging" in text
            and "morpholog" in text
            and bool(re.search(r"\bgalax(?:y|ies)\b", text))
        )

    @classmethod
    def _supporting_variants(
        cls,
        memory: CanonicalMemoryRecord,
        target_role: str,
        claim: str,
        method: str,
        outcome: str,
        capabilities: list[str],
        problem: str,
        data_or_inputs: str,
        what_this_proves: str,
        limitations: str,
    ) -> dict[str, Any]:
        if not capabilities:
            return {
                "resume_bullets": [
                    (
                        "Add an approved method before converting this project into "
                        "a resume bullet."
                    ),
                    (
                        "Add an approved result before making an outcome or impact "
                        "claim."
                    ),
                ],
                "cover_letter_paragraph": (
                    f"{memory.title} is documented, but the approved evidence does "
                    "not yet support using it as a role-specific capability example."
                ),
                "outreach_blurb": (
                    f"I am refining the evidence for {memory.title} before sharing "
                    "it as a role-specific work sample."
                ),
                "interview_answer": (
                    f"I would not use {memory.title} as an interview example until "
                    "the approved problem, method, and result are documented."
                ),
                "github_readme_outline": (
                    f"# {memory.title}\n\n"
                    f"## Problem\n{problem}\n\n"
                    f"## Data or inputs\n{data_or_inputs}\n\n"
                    f"## Approach\n{method}\n\n"
                    f"## Key takeaway\n{outcome}\n\n"
                    f"## Limitations\n{limitations}\n\n"
                    f"## Role-specific claim\n{what_this_proves}"
                ),
            }
        skills = (
            cls._join(capabilities[:4]) if capabilities else "documented project work"
        )
        if cls._is_galaxy_analytics_case(
            " ".join((memory.title, problem, data_or_inputs, method))
        ):
            resume_bullets = [
                (
                    "Analyzed spectral and imaging data to study relationships "
                    "between galaxy morphology and kinematics."
                ),
                (
                    f"Applied {skills} to build a repeatable analytical workflow and "
                    "communicate technical findings clearly."
                ),
            ]
        else:
            resume_bullets = [
                (
                    f"Applied {skills} in {memory.title} to address the documented "
                    "project question."
                ),
                (
                    "Produced a reviewable case study that explains the method, "
                    f"evidence, and result for {target_role}."
                ),
            ]
        cover_letter = (
            f"In {memory.title}, {problem[0].lower() + problem[1:]} {method} "
            f"{what_this_proves} I would bring the same disciplined, evidence-based "
            "approach to this opportunity."
        )
        outreach = (
            f"I’m targeting {target_role} roles and created a one-page case study "
            f"from {memory.title}. {claim} I’d value one quick reaction: is the "
            "role-relevant value clear in the first 30 seconds?"
        )
        interview = (
            f"One example is {memory.title}. {problem} {method} {outcome} "
            f"For {target_role}, the most relevant takeaway is my experience with "
            f"{skills}."
        )
        github_outline = (
            f"# {memory.title}\n\n"
            f"## Overview\n{problem}\n\n"
            f"## Data or inputs\n{data_or_inputs}\n\n"
            f"## Approach\n{method}\n\n"
            f"## Key takeaway\n{outcome}\n\n"
            f"## Limitations\n{limitations}\n\n"
            f"## Relevance to {target_role}\n{what_this_proves}"
        )
        return {
            "resume_bullets": resume_bullets,
            "cover_letter_paragraph": cover_letter,
            "outreach_blurb": outreach,
            "interview_answer": interview,
            "github_readme_outline": github_outline,
        }

    @classmethod
    def _render_case_study(cls, sections: dict[str, Any]) -> str:
        ordered = [
            ("Target claim", "target_claim"),
            ("Role relevance", "role_relevance"),
            ("Context", "context"),
            ("Problem", "problem"),
            ("Data or inputs", "data_or_inputs"),
            ("Method", "method"),
            ("Evidence used", "evidence_used"),
            ("Skills demonstrated", "skills_demonstrated"),
            ("Outcome or insight", "outcome_or_insight"),
            ("Limitations", "limitations"),
            ("What this proves", "what_this_proves"),
            ("How to use", "how_to_use"),
            ("Reviewer question", "reviewer_question"),
        ]
        parts = [f"# {sections['title']}"]
        for label, key in ordered:
            value = sections[key]
            if key == "evidence_used" and isinstance(value, list):
                rendered = "\n".join(
                    f"- {item}" for item in cls._evidence_summary_lines(value)
                )
                rendered = rendered or "- No resolved evidence reference is available."
            else:
                rendered = (
                    "\n".join(f"- {item}" for item in value)
                    if isinstance(value, list)
                    else str(value)
                )
            parts.append(f"## {label}\n{rendered}")
        return "\n\n".join(parts)

    @classmethod
    def _evidence_summary_lines(cls, references: list[Any]) -> list[str]:
        valid = [item for item in references if isinstance(item, dict)]
        combined = " ".join(str(item.get("excerpt") or "") for item in valid)
        if cls._is_galaxy_analytics_case(combined):
            source = str(valid[0].get("source_label") or "Project evidence")
            lines = [
                (
                    f"{source}: Project scope — spectral and imaging data used to "
                    "investigate galaxy morphology and kinematics."
                )
            ]
            capabilities = cls._capabilities(combined)
            methods: list[str] = []
            if "data analysis" in capabilities:
                methods.append(
                    "statistical analysis"
                    if "statistical analys" in combined.casefold()
                    else "data analysis"
                )
            if "statistical modeling" in capabilities:
                methods.append("statistical modeling")
            elif "modeling" in capabilities:
                methods.append("modeling")
            methods.extend(
                label
                for capability, label in (
                    (
                        "uncertainty and error propagation",
                        "uncertainty and error propagation",
                    ),
                    ("data visualization", "data visualization"),
                )
                if capability in capabilities
            )
            if methods:
                lines.append(f"{source}: Analytical method — {cls._join(methods)}.")
            if "technical communication" in capabilities:
                lines.append(
                    f"{source}: Communication — technical findings presented clearly."
                )
            return lines

        lines: list[str] = []
        seen: set[tuple[str, str]] = set()
        for item in valid:
            source = str(item.get("source_label") or "Approved source").strip()
            excerpt = " ".join(str(item.get("excerpt") or "").split())
            if not excerpt:
                line = (source, "Source linked to the project record.")
            else:
                summary = (
                    excerpt if len(excerpt) <= 180 else f"{excerpt[:177].rstrip()}…"
                )
                line = (source, summary)
            key = (line[0].casefold(), line[1].casefold())
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"{line[0]}: {line[1]}")
        return lines[:4]

    @staticmethod
    def _primary_content(
        artifact_type: ProofArtifactType,
        case_study_content: str,
        variants: dict[str, Any],
    ) -> str:
        if artifact_type in {
            ProofArtifactType.CASE_STUDY,
            ProofArtifactType.PORTFOLIO_PAGE,
            ProofArtifactType.APPLICATION_UPLOAD,
        }:
            return case_study_content
        mapping = {
            ProofArtifactType.GITHUB_README: "github_readme_outline",
            ProofArtifactType.OUTREACH_SUMMARY: "outreach_blurb",
            ProofArtifactType.INTERVIEW_STORY: "interview_answer",
            ProofArtifactType.RESUME_BULLETS: "resume_bullets",
        }
        value = variants[mapping[artifact_type]]
        return (
            "\n".join(f"- {item}" for item in value)
            if isinstance(value, list)
            else value
        )

    @staticmethod
    def _warnings(
        resolved_evidence_count: int,
        has_documented_metric: bool,
        documented_outcome: str | None,
        outcome_signals: list[dict[str, str]],
    ) -> list[str]:
        warnings = [
            "Do not add tools, datasets, metrics, or outcomes that are not present "
            "in approved Career Memory or its evidence trail."
        ]
        if not resolved_evidence_count:
            warnings.append(
                "This memory has no resolvable, user-owned linked evidence. Treat the "
                "artifact as a partial draft and add approved evidence before sharing."
            )
        if not documented_outcome:
            warnings.append(
                "No documented outcome is approved. Do not claim quantified business "
                "impact or imply that the project caused an external result."
            )
        if not has_documented_metric:
            warnings.append(
                "No approved performance metric is available; keep the case study "
                "focused on process, evidence, and communication."
            )
        if outcome_signals:
            warnings.append(
                "An approved outcome note suggests similar framing worked once. This "
                "is a strategy signal, not proof of causality."
            )
        return warnings

    @staticmethod
    def _readiness(
        resolved_evidence_count: int,
        claim: str,
        method: str,
        capabilities: list[str],
        documented_outcome: str | None,
        target_role: str,
    ) -> tuple[float, ProofReadinessLabel]:
        score = 0.25
        score += min(0.25, resolved_evidence_count * 0.07)
        score += 0.12 if claim else 0
        score += 0.1 if "does not document" not in method else 0
        role_capabilities = ProofArtifactService._role_capabilities(
            target_role, capabilities
        )
        score += (
            0.08 if len(role_capabilities) >= 3 else 0.04 if role_capabilities else 0
        )
        score += 0.1 if documented_outcome else 0
        if not resolved_evidence_count:
            score = min(score, 0.39)
        elif not documented_outcome:
            score = min(score, 0.79)
        score = round(min(score, 1.0), 3)
        if score < 0.4:
            label = ProofReadinessLabel.NEEDS_EVIDENCE
        elif score < 0.6:
            label = ProofReadinessLabel.DRAFTABLE
        elif score < 0.8:
            label = ProofReadinessLabel.STRONG_DRAFT
        else:
            label = ProofReadinessLabel.READY_TO_SHARE
        return score, label

    @staticmethod
    def _role_capabilities(target_role: str, capabilities: list[str]) -> list[str]:
        if ProofArtifactService._is_analytics_target(target_role):
            relevant = {
                "data analysis",
                "Gaussian fitting",
                "statistical modeling",
                "modeling",
                "uncertainty and error propagation",
                "data visualization",
                "technical communication",
                "technical documentation",
                "research reasoning",
                "image inspection",
                "detection review",
                "labeling and categorization",
                "t-SNE exploration",
                "data-quality judgment",
                "human-in-the-loop review",
            }
        elif ProofArtifactService._is_ai_target(target_role):
            relevant = {
                "data analysis",
                "Python",
                "Gaussian fitting",
                "statistical modeling",
                "modeling",
                "technical communication",
                "technical documentation",
                "research reasoning",
                "image inspection",
                "detection review",
                "labeling and categorization",
                "t-SNE exploration",
                "data-quality judgment",
                "human-in-the-loop review",
            }
        else:
            return capabilities
        return [capability for capability in capabilities if capability in relevant]

    @classmethod
    def _documented_outcome(cls, fields: dict[str, Any]) -> str | None:
        return cls._field_text(
            fields,
            "enriched_findings",
            "outcome",
            "outcomes",
            "result",
            "results",
            "finding",
            "findings",
            "impact",
        )

    @classmethod
    def _has_documented_metric(cls, fields: dict[str, Any], approved_text: str) -> bool:
        metric_keys = {
            "metric",
            "metrics",
            "measurement",
            "measurements",
            "quantified impact",
            "performance metric",
            "performance metrics",
        }
        for key, value in fields.items():
            normalized = key.casefold().replace("_", " ")
            rendered = cls._render_value(value) or ""
            if normalized in metric_keys and re.search(r"\d", rendered):
                return True
            if isinstance(value, dict) and cls._has_documented_metric(
                value, json.dumps(value, ensure_ascii=False)
            ):
                return True
        return bool(
            re.search(
                r"(?<!\w)\d+(?:\.\d+)?\s*(?:%|percent\b|x\b|users?\b|"
                r"records?\b|samples?\b|applications?\b|interviews?\b|"
                r"callbacks?\b|milliseconds?\b|ms\b)",
                approved_text.casefold(),
            )
        )

    @classmethod
    def _field_text(cls, fields: dict[str, Any], *keys: str) -> str | None:
        wanted = {key.casefold().replace("_", " ") for key in keys}
        for key, value in fields.items():
            normalized = key.casefold().replace("_", " ")
            if normalized in wanted:
                rendered = cls._render_value(value)
                if rendered:
                    return rendered
        for value in fields.values():
            if isinstance(value, dict):
                found = cls._field_text(value, *keys)
                if found:
                    return found
        return None

    @classmethod
    def _field_values(cls, fields: dict[str, Any], *keys: str) -> list[str]:
        wanted = {key.casefold().replace("_", " ") for key in keys}
        for key, value in fields.items():
            normalized = key.casefold().replace("_", " ")
            if normalized not in wanted:
                continue
            values = value if isinstance(value, list) else [value]
            return [str(item).strip() for item in values if str(item).strip()]
        for value in fields.values():
            if isinstance(value, dict):
                found = cls._field_values(value, *keys)
                if found:
                    return found
        return []

    @staticmethod
    def _render_value(value: Any) -> str | None:
        if value is None or value == "" or value == [] or value == {}:
            return None
        if isinstance(value, list):
            return "; ".join(str(item) for item in value if item not in (None, ""))
        if isinstance(value, dict):
            return "; ".join(
                f"{key.replace('_', ' ')}: {item}"
                for key, item in value.items()
                if item not in (None, "", [], {})
            )
        return str(value)

    @staticmethod
    def _memory_type_label(value: str) -> str:
        return value.replace("_", " ").casefold()

    @staticmethod
    def _join(values: list[str]) -> str:
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return f"{', '.join(values[:-1])}, and {values[-1]}"

    @staticmethod
    def _unsupported_numbers(edited: str, approved: str) -> list[str]:
        number_pattern = r"(?<![\w.])\d+(?:\.\d+)?%?(?!\w)"
        approved_numbers = set(re.findall(number_pattern, approved))
        edited_numbers = list(dict.fromkeys(re.findall(number_pattern, edited)))
        return [number for number in edited_numbers if number not in approved_numbers]

    @staticmethod
    def _text_section(sections: dict[str, Any], key: str) -> str | None:
        value = sections.get(key)
        if not isinstance(value, str):
            return None
        value = value.strip()
        return value or None

    @staticmethod
    def _markdown_title(content: str) -> str | None:
        match = re.search(r"^#\s+(.+?)\s*$", content, flags=re.MULTILINE)
        return match.group(1).strip() if match else None

    @staticmethod
    def _markdown_section(content: str, heading: str) -> str | None:
        match = re.search(
            rf"^##\s+{re.escape(heading)}\s*\n(.+?)(?=\n##\s|\Z)",
            content,
            flags=re.MULTILINE | re.DOTALL,
        )
        return match.group(1).strip() if match else None

    @staticmethod
    def _replace_markdown_title(content: str, title: str) -> str:
        return re.sub(
            r"^#\s+.+?$",
            f"# {title}",
            content,
            count=1,
            flags=re.MULTILINE,
        )

    @staticmethod
    def _replace_markdown_section(content: str, heading: str, value: str) -> str:
        return re.sub(
            rf"(^##\s+{re.escape(heading)}\s*\n).+?(?=\n##\s|\Z)",
            lambda match: f"{match.group(1)}{value}",
            content,
            count=1,
            flags=re.MULTILINE | re.DOTALL,
        )

    @staticmethod
    def _set_version_title(
        artifact: ProofArtifact, version: ProofArtifactVersion, title: str
    ) -> None:
        artifact.title = title
        version.title = title
        version.structured_sections = {
            **version.structured_sections,
            "title": title,
        }

    @staticmethod
    def _set_version_claim(version: ProofArtifactVersion, claim: str) -> None:
        version.claim = claim
        version.structured_sections = {
            **version.structured_sections,
            "target_claim": claim,
        }

    def _get_memory(
        self, session: Session, memory_id: uuid.UUID
    ) -> CanonicalMemoryRecord:
        memory = session.scalar(
            select(CanonicalMemoryRecord)
            .join(
                ReviewProposal,
                ReviewProposal.id == CanonicalMemoryRecord.review_proposal_id,
            )
            .where(
                CanonicalMemoryRecord.id == memory_id,
                CanonicalMemoryRecord.user_id == self.user_id,
                ReviewProposal.user_id == self.user_id,
                ReviewProposal.decision.in_(
                    (
                        DurableReviewStatus.APPROVED.value,
                        DurableReviewStatus.EDITED_APPROVED.value,
                    )
                ),
            )
        )
        if memory is not None:
            return memory
        has_memory = session.scalar(
            select(func.count(CanonicalMemoryRecord.id))
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
            )
        )
        if not has_memory:
            raise ProofArtifactValidationError(
                "Approve career memories before building a proof artifact."
            )
        raise ProofArtifactNotFoundError("Approved source memory not found.")

    def _get_source_memory(
        self, session: Session, memory_id: uuid.UUID
    ) -> CanonicalMemoryRecord:
        memory = session.scalar(
            select(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.id == memory_id,
                CanonicalMemoryRecord.user_id == self.user_id,
            )
        )
        if memory is None:
            raise ProofArtifactNotFoundError("Source memory not found.")
        return memory

    def _get_diagnosis(
        self,
        session: Session,
        diagnosis_result_id: uuid.UUID | None,
        memory_id: uuid.UUID,
    ) -> DiagnosisResult | None:
        if diagnosis_result_id is None:
            return None
        result = session.scalar(
            select(DiagnosisResult).where(
                DiagnosisResult.id == diagnosis_result_id,
                DiagnosisResult.user_id == self.user_id,
            )
        )
        if result is None:
            raise ProofArtifactNotFoundError("Source diagnosis result not found.")
        referenced_memory_ids = {
            str(item.get("memory_id"))
            for item in result.evidence_map
            if item.get("memory_id")
        }
        referenced_memory_ids.update(
            str(item) for item in result.proof_sprint.get("evidence_to_strengthen", [])
        )
        if str(memory_id) not in referenced_memory_ids:
            raise ProofArtifactValidationError(
                "The selected memory is not referenced by this diagnosis result."
            )
        return result

    def _get_artifact(
        self, session: Session, artifact_id: uuid.UUID, *, lock: bool = False
    ) -> ProofArtifact:
        query = select(ProofArtifact).where(
            ProofArtifact.id == artifact_id,
            ProofArtifact.user_id == self.user_id,
        )
        if lock:
            query = query.with_for_update()
        artifact = session.scalar(query)
        if artifact is None:
            raise ProofArtifactNotFoundError("Proof artifact not found.")
        return artifact

    def _latest_version(
        self, session: Session, artifact_id: uuid.UUID
    ) -> ProofArtifactVersion:
        version = session.scalar(
            select(ProofArtifactVersion)
            .where(
                ProofArtifactVersion.artifact_id == artifact_id,
                ProofArtifactVersion.user_id == self.user_id,
            )
            .order_by(ProofArtifactVersion.version_number.desc())
            .limit(1)
        )
        if version is None:
            raise ProofArtifactNotFoundError("Proof artifact has no saved versions.")
        return version

    def _version_record(
        self,
        artifact_id: uuid.UUID,
        version_number: int,
        generated: GeneratedProof,
    ) -> ProofArtifactVersion:
        return ProofArtifactVersion(
            user_id=self.user_id,
            artifact_id=artifact_id,
            version_number=version_number,
            title=generated.title,
            claim=generated.claim,
            content=generated.content,
            structured_sections=generated.sections,
            evidence_ids=generated.evidence_ids,
            outcome_signal_ids=generated.outcome_signal_ids,
            warnings=generated.warnings,
            readiness_score=Decimal(str(generated.readiness_score)),
            readiness_label=generated.readiness_label.value,
            supporting_variants=generated.supporting_variants,
        )

    def _view(self, session: Session, artifact: ProofArtifact) -> ProofArtifactView:
        versions = session.scalars(
            select(ProofArtifactVersion)
            .where(
                ProofArtifactVersion.artifact_id == artifact.id,
                ProofArtifactVersion.user_id == self.user_id,
            )
            .order_by(ProofArtifactVersion.version_number.desc())
        ).all()
        if not versions:
            raise ProofArtifactNotFoundError("Proof artifact has no saved versions.")
        memory = self._get_source_memory(session, artifact.source_memory_id)
        return ProofArtifactView(
            id=artifact.id,
            title=self._clean_user_facing_text(artifact.title),
            artifact_type=ProofArtifactType(artifact.artifact_type),
            target_role=artifact.target_role,
            target_audience=ProofTargetAudience(artifact.target_audience),
            source_memory_id=artifact.source_memory_id,
            source_memory_title=memory.title,
            source_diagnosis_result_id=artifact.source_diagnosis_result_id,
            status=ProofArtifactStatus(artifact.status),
            latest_version=self._version_view(session, versions[0], memory),
            version_count=len(versions),
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )

    def _version_view(
        self,
        session: Session,
        version: ProofArtifactVersion,
        memory: CanonicalMemoryRecord,
    ) -> ProofArtifactVersionView:
        stored_references = version.structured_sections.get("evidence_used", [])
        references = (
            stored_references
            if isinstance(stored_references, list) and stored_references
            else self._evidence_references(
                session, version.evidence_ids, memory.source_ids
            )
        )
        stored_signals = version.structured_sections.get("outcome_signals", [])
        signals = [
            ProofOutcomeSignal(
                feedback_event_id=item["feedback_event_id"],
                summary=item["summary"],
                guidance=item["guidance"],
                caveat=item["caveat"],
            )
            for item in stored_signals
            if isinstance(item, dict)
            and item.get("feedback_event_id")
            and item.get("summary")
        ]
        content = self._clean_user_facing_text(
            version.content, version.structured_sections
        )
        content = self._replace_evidence_section(content, references)
        return ProofArtifactVersionView(
            id=version.id,
            artifact_id=version.artifact_id,
            version_number=version.version_number,
            title=self._clean_user_facing_text(version.title),
            claim=version.claim,
            content=content,
            structured_sections=version.structured_sections,
            evidence_ids=version.evidence_ids,
            evidence_references=[ProofEvidenceReference(**item) for item in references],
            outcome_signal_ids=version.outcome_signal_ids,
            outcome_signals=signals,
            warnings=version.warnings,
            readiness_score=float(version.readiness_score),
            readiness_label=ProofReadinessLabel(version.readiness_label),
            supporting_variants=self._clean_user_facing_value(
                version.supporting_variants, version.structured_sections
            ),
            created_at=version.created_at,
            updated_at=version.updated_at,
        )

    @classmethod
    def _clean_user_facing_value(
        cls, value: Any, sections: dict[str, Any] | None = None
    ) -> Any:
        if isinstance(value, str):
            return cls._clean_user_facing_text(value, sections)
        if isinstance(value, list):
            return [cls._clean_user_facing_value(item, sections) for item in value]
        if isinstance(value, dict):
            return {
                key: cls._clean_user_facing_value(item, sections)
                for key, item in value.items()
            }
        return value

    @staticmethod
    def _clean_user_facing_text(
        text: str, sections: dict[str, Any] | None = None
    ) -> str:
        cleaned = re.sub(r"\bCaseStudy\b", "Case Study", text)
        cleaned = re.sub(
            r"\s*\(evidence\s+[0-9a-f]{8}-[0-9a-f-]{27,}\)",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"(?im)^\s*(?:[-*]\s*)?Evidence ID:\s*"
            r"[0-9a-f]{8}-[0-9a-f-]{27,}\s*$\n?",
            "",
            cleaned,
        )
        if sections:
            replacements = {
                "State the approved problem in one paragraph.": sections.get(
                    "problem", "Describe the documented project question."
                ),
                "Name only source-backed inputs.": sections.get(
                    "data_or_inputs", "Describe the documented inputs."
                ),
                "Explain the approved analytical process.": sections.get(
                    "method", "Describe the documented approach."
                ),
                "Separate documented findings from gaps.": (
                    f"{sections.get('outcome_or_insight', '')}\n\n"
                    f"### Limitations\n{sections.get('limitations', '')}"
                ).strip(),
                "Use the target claim without inventing impact.": sections.get(
                    "what_this_proves", sections.get("target_claim", "")
                ),
            }
            for placeholder, replacement in replacements.items():
                cleaned = cleaned.replace(placeholder, str(replacement))
        return cleaned.strip()

    @classmethod
    def _replace_evidence_section(
        cls, content: str, references: list[dict[str, Any]]
    ) -> str:
        if "## Evidence used" not in content:
            return content
        rendered = "\n".join(
            f"- {item}" for item in cls._evidence_summary_lines(references)
        )
        rendered = rendered or "- No resolved evidence reference is available."
        pattern = re.compile(r"(?ms)(^## Evidence used\s*\n).*?(?=\n## |\Z)")
        return pattern.sub(
            lambda match: f"{match.group(1)}{rendered}\n", content, count=1
        ).strip()

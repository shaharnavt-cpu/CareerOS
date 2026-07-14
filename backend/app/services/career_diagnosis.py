"""Deterministic Career Diagnosis and Teach CareerOS services."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    ApplicationDraft,
    ApplicationOpportunity,
    CanonicalMemoryRecord,
    CareerFeedbackEvent,
    DiagnosisResult,
    DiagnosisSession,
    ReviewProposal,
    User,
)
from app.schemas.career_memory import CompiledCareerMemoryProfile
from app.schemas.diagnosis import (
    DiagnosisFocus,
    DiagnosisResultView,
    DiagnosisSessionCreateRequest,
    DiagnosisSessionStatus,
    DiagnosisSessionView,
    EvidenceMapItem,
    FeedbackArtifactType,
    FeedbackEventCreateRequest,
    FeedbackEventStatus,
    FeedbackEventType,
    FeedbackEventUpdateRequest,
    FeedbackEventView,
    FeedbackOutcomeType,
    OutcomeSignal,
    ProofSprint,
)
from app.schemas.knowledge import (
    DEMO_USER_ID,
    DurableReviewStatus,
    ReviewProposalType,
)
from app.services.career_memory_compiler import (
    CareerMemoryCompiler,
    compiled_profile_factual_text,
)


class DiagnosisNotFoundError(LookupError):
    """Raised when a user-scoped diagnosis object is unavailable."""


class DuplicateFeedbackEventError(ValueError):
    """Raised when a feedback note is too similar to an existing event."""

    def __init__(self, existing_event_id: uuid.UUID) -> None:
        super().__init__("This looks similar to an existing feedback event.")
        self.existing_event_id = existing_event_id


@dataclass(frozen=True)
class DiagnosisInputs:
    target_role: str | None
    target_context: str | None
    frustration_context: str | None
    selected_focus: DiagnosisFocus | None


@dataclass(frozen=True)
class ParsedFeedback:
    event_type: FeedbackEventType
    structured_summary: str
    artifact_type: FeedbackArtifactType | None
    artifact_label: str | None
    outcome: FeedbackOutcomeType | None
    suggested_future_use: str
    metadata: dict[str, Any]


class CareerDiagnosisService:
    """Persist and run evidence-linked local deterministic diagnoses."""

    version = "local-deterministic-v0"
    theme_keywords = {
        "Analytics": (
            "analytics",
            "analysis",
            "data",
            "python",
            "sql",
            "excel",
            "visualization",
            "statistics",
            "modeling",
            "reporting",
        ),
        "AI / Automation": (
            "artificial intelligence",
            "machine learning",
            " ai ",
            "automation",
            "llm",
            "agent",
            "decision-support",
            "decision support",
        ),
        "Research": (
            "research",
            "capstone",
            "thesis",
            "kinematics",
            "experiment",
            "hypothesis",
            "uncertainty",
        ),
        "Communication": (
            "communicat",
            "present",
            "wrote",
            "writing",
            "taught",
            "teaching",
            "non-technical",
            "stakeholder",
        ),
        "Leadership": (
            "leadership",
            "led ",
            "leader",
            "mentor",
            "managed",
            "coordinated",
            "facilitated",
        ),
        "Operations": (
            "operations",
            "process",
            "workflow",
            "service",
            "organized",
            "coordination",
        ),
        "Quant / Finance": (
            "quant",
            "finance",
            "financial",
            "risk",
            "econometrics",
            "forecast",
            "valuation",
        ),
    }
    focus_themes = {
        DiagnosisFocus.ANALYTICS: {"Analytics", "Communication"},
        DiagnosisFocus.AI_AUTOMATION: {"AI / Automation", "Analytics"},
        DiagnosisFocus.RESEARCH: {"Research", "Analytics"},
        DiagnosisFocus.QUANT_FINANCE: {"Quant / Finance", "Analytics"},
        DiagnosisFocus.CAMPUS_JOB: {"Operations", "Communication", "Leadership"},
        DiagnosisFocus.SCHOLARSHIP_LEADERSHIP: {
            "Leadership",
            "Communication",
            "Operations",
        },
        DiagnosisFocus.GENERAL: set(),
    }
    memory_weights = {
        ReviewProposalType.PROJECT: 0.36,
        ReviewProposalType.EXPERIENCE: 0.31,
        ReviewProposalType.ACHIEVEMENT: 0.22,
        ReviewProposalType.SKILL_SET: 0.18,
        ReviewProposalType.EDUCATION: 0.12,
        ReviewProposalType.PROGRAM: 0.13,
        ReviewProposalType.ORGANIZATION: 0.08,
        ReviewProposalType.CONTACT: 0.01,
        ReviewProposalType.NEEDS_CLASSIFICATION: 0.04,
    }

    def __init__(
        self,
        user_id: uuid.UUID = DEMO_USER_ID,
        compiler: CareerMemoryCompiler | None = None,
    ) -> None:
        self.user_id = user_id
        self.compiler = compiler or CareerMemoryCompiler(user_id=user_id)
        self._compiled_profiles: dict[uuid.UUID, CompiledCareerMemoryProfile] = {}

    def create_and_run(
        self, session: Session, request: DiagnosisSessionCreateRequest
    ) -> DiagnosisSessionView:
        self._ensure_user(session)
        record = DiagnosisSession(
            user_id=self.user_id,
            target_role=request.target_role,
            target_context=request.target_context,
            frustration_context=request.frustration_context,
            selected_focus=(
                request.selected_focus.value if request.selected_focus else None
            ),
            status=DiagnosisSessionStatus.RUNNING.value,
        )
        session.add(record)
        session.flush()
        self._run_into(session, record)
        session.commit()
        return self.get_session(session, record.id)

    def list_sessions(self, session: Session) -> list[DiagnosisSessionView]:
        records = session.scalars(
            select(DiagnosisSession)
            .where(DiagnosisSession.user_id == self.user_id)
            .order_by(DiagnosisSession.created_at.desc())
        ).all()
        return [self._session_view(session, record) for record in records]

    def get_session(
        self, session: Session, diagnosis_session_id: uuid.UUID
    ) -> DiagnosisSessionView:
        return self._session_view(
            session, self._get_session(session, diagnosis_session_id)
        )

    def rerun(
        self, session: Session, diagnosis_session_id: uuid.UUID
    ) -> DiagnosisSessionView:
        record = self._get_session(session, diagnosis_session_id)
        record.status = DiagnosisSessionStatus.RUNNING.value
        session.execute(
            delete(DiagnosisResult).where(DiagnosisResult.session_id == record.id)
        )
        session.flush()
        self._run_into(session, record)
        session.commit()
        return self.get_session(session, record.id)

    def _run_into(self, session: Session, record: DiagnosisSession) -> None:
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
        ).all()
        self._compiled_profiles = {
            memory.id: self.compiler.compile(
                session,
                memory.id,
                record.target_role,
            )
            for memory in memories
            if memory.memory_type == "PROJECT"
        }
        approved_feedback = session.scalars(
            select(CareerFeedbackEvent)
            .where(
                CareerFeedbackEvent.user_id == self.user_id,
                CareerFeedbackEvent.status == FeedbackEventStatus.APPROVED.value,
            )
            .order_by(CareerFeedbackEvent.updated_at.desc())
            .limit(20)
        ).all()
        inputs = DiagnosisInputs(
            target_role=record.target_role,
            target_context=record.target_context,
            frustration_context=record.frustration_context,
            selected_focus=(
                DiagnosisFocus(record.selected_focus) if record.selected_focus else None
            ),
        )
        payload = (
            self._diagnose(memories, approved_feedback, inputs)
            if memories
            else self._empty_diagnosis()
        )
        record.status = (
            DiagnosisSessionStatus.COMPLETE.value
            if memories
            else DiagnosisSessionStatus.NEEDS_MEMORY.value
        )
        session.add(
            DiagnosisResult(
                user_id=self.user_id,
                session_id=record.id,
                career_identity=payload["career_identity"],
                identity_rationale=payload["identity_rationale"],
                evidence_map=payload["evidence_map"],
                recognition_gap=payload["recognition_gap"],
                missing_proof=payload["missing_proof"],
                proof_sprint=payload["proof_sprint"],
                do_not_waste_time=payload["do_not_waste_time"],
                exact_next_actions=payload["exact_next_actions"],
                exact_messages=payload["exact_messages"],
                confidence=Decimal(str(payload["confidence"])),
                evidence_ids=payload["evidence_ids"],
                feedback_event_ids=payload["feedback_event_ids"],
                outcome_signals=payload["outcome_signals"],
                diagnosis_version=self.version,
            )
        )

    def _diagnose(
        self,
        memories: list[CanonicalMemoryRecord],
        approved_feedback: list[CareerFeedbackEvent],
        inputs: DiagnosisInputs,
    ) -> dict[str, Any]:
        evidence_map = self._build_evidence_map(memories, inputs)
        theme_scores = self._theme_scores(memories)
        identity = self._career_identity(memories, theme_scores)
        rationale = self._identity_rationale(
            memories, evidence_map, approved_feedback, inputs
        )
        outcome_signals = self._outcome_signals(approved_feedback)
        recognition_gap = self._recognition_gap(
            memories,
            theme_scores,
            approved_feedback,
            outcome_signals,
            inputs,
        )
        missing_proof = self._missing_proof(memories, theme_scores, inputs)
        proof_source = next(
            (
                item
                for item in evidence_map
                if item["memory_type"] == ReviewProposalType.PROJECT.value
            ),
            next(
                (
                    item
                    for item in evidence_map
                    if item["memory_type"] == ReviewProposalType.EXPERIENCE.value
                ),
                evidence_map[0],
            ),
        )
        proof_sprint = self._proof_sprint(
            proof_source, theme_scores, outcome_signals, inputs
        )
        do_not_waste_time = self._do_not_waste_time(
            memories, theme_scores, proof_source, inputs
        )
        exact_actions = [
            proof_sprint["actions"][0],
            proof_sprint["actions"][2],
            (
                "Send the finished artifact to three people who evaluate "
                f"{self._target_label(inputs)} work and ask one specific question."
            ),
        ]
        if outcome_signals:
            artifact_label = outcome_signals[0].get("artifact_label") or "the artifact"
            exact_actions.insert(
                1,
                f"Review {artifact_label} and preserve the role-specific framing "
                "that received one positive outcome signal.",
            )
        exact_messages = self._exact_messages(proof_source, outcome_signals, inputs)
        evidence_ids = list(
            dict.fromkeys(
                evidence_id
                for item in evidence_map
                for evidence_id in item["evidence_ids"]
            )
        )
        memories_with_evidence = sum(bool(memory.evidence_ids) for memory in memories)
        confidence = min(
            0.91,
            0.48
            + min(len(memories), 5) * 0.055
            + min(memories_with_evidence, 4) * 0.035,
        )
        return {
            "career_identity": identity,
            "identity_rationale": rationale,
            "evidence_map": evidence_map,
            "recognition_gap": recognition_gap,
            "missing_proof": missing_proof,
            "proof_sprint": proof_sprint,
            "do_not_waste_time": do_not_waste_time,
            "exact_next_actions": exact_actions,
            "exact_messages": exact_messages,
            "confidence": round(confidence, 3),
            "evidence_ids": evidence_ids,
            "feedback_event_ids": [str(event.id) for event in approved_feedback],
            "outcome_signals": outcome_signals,
        }

    def _empty_diagnosis(self) -> dict[str, Any]:
        return {
            "career_identity": (
                "Approve career memories before running a full diagnosis."
            ),
            "identity_rationale": (
                "CareerOS only treats approved canonical Career Memory as proof. "
                "No approved memory is available yet, so it will not infer a career "
                "identity from unreviewed proposals or context alone."
            ),
            "evidence_map": [],
            "recognition_gap": (
                "The current gap is evidence readiness: CareerOS cannot compare your "
                "target with trusted proof until at least one career memory is "
                "approved."
            ),
            "missing_proof": [
                "At least one approved project, experience, education, or skill memory "
                "with its evidence trail."
            ],
            "proof_sprint": {
                "objective": "Approve the strongest existing career memory.",
                "actions": [
                    "Open Review and choose the proposal with the clearest source "
                    "evidence.",
                    "Correct its title and structured details before approving it.",
                    "Return to Diagnosis and rerun this session.",
                ],
                "expected_artifact": "One approved canonical Career Memory record.",
                "why_it_matters": (
                    "A diagnosis needs trusted evidence before it can make a specific "
                    "career judgment."
                ),
                "evidence_to_strengthen": [],
                "application_use": (
                    "After approval, CareerOS can map that proof to a target without "
                    "inventing claims."
                ),
            },
            "do_not_waste_time": (
                "Do not treat unapproved proposals or your frustration note as proof; "
                "approve the strongest sourced memory first."
            ),
            "exact_next_actions": [
                "Open Review and approve one evidence-backed memory.",
                "Rerun this diagnosis after approval.",
            ],
            "exact_messages": {},
            "confidence": 0.0,
            "evidence_ids": [],
            "feedback_event_ids": [],
            "outcome_signals": [],
        }

    def _build_evidence_map(
        self,
        memories: list[CanonicalMemoryRecord],
        inputs: DiagnosisInputs,
    ) -> list[dict[str, Any]]:
        target_themes = self._target_themes(inputs)
        ranked: list[tuple[float, dict[str, Any]]] = []
        for memory in memories:
            memory_type = ReviewProposalType(memory.memory_type)
            if memory_type is ReviewProposalType.CONTACT:
                continue
            text = self._memory_text(memory)
            themes = self._themes(text)
            if not themes:
                themes = [self._fallback_theme(memory_type)]
            confidence = float(memory.confidence)
            strength = (
                "STRONG"
                if memory.evidence_ids and confidence >= 0.8
                else "MODERATE"
                if memory.evidence_ids or confidence >= 0.65
                else "LIMITED"
            )
            reason_code = (
                "STRONG_DIRECT_PROOF"
                if strength == "STRONG"
                else "CORROBORATED_PROOF"
                if memory.evidence_ids
                else "APPROVED_WITH_LIMITED_PROVENANCE"
            )
            item = {
                "memory_id": str(memory.id),
                "memory_title": memory.title,
                "memory_type": memory.memory_type,
                "relevant_themes": themes,
                "claim_supported": self._claim_supported(
                    memory.title, memory_type, themes
                ),
                "evidence_ids": memory.evidence_ids,
                "strength": strength,
                "confidence": round(confidence, 3),
                "reason_code": reason_code,
            }
            overlap = len(set(themes) & target_themes)
            score = self.memory_weights.get(memory_type, 0.04)
            score += overlap * 0.14 + min(len(themes), 3) * 0.025
            score += confidence * 0.08
            score += min(len(memory.evidence_ids), 8) * 0.006
            ranked.append((score, item))
        return [
            item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)
        ]

    def _career_identity(
        self,
        memories: list[CanonicalMemoryRecord],
        scores: dict[str, int],
    ) -> str:
        ai_builder = any(
            memory.memory_type in {"PROJECT", "EXPERIENCE"}
            and "AI / Automation" in self._themes(self._memory_text(memory))
            for memory in memories
        )
        has_project = any(memory.memory_type == "PROJECT" for memory in memories)
        if ai_builder and scores["Analytics"]:
            return (
                "AI and analytics builder focused on practical decision-support "
                "systems."
            )
        if scores["Analytics"] >= 2 and has_project:
            ending = (
                " and technical communication proof."
                if scores["Communication"]
                else "."
            )
            return (
                "Analytical problem-solver with research depth, data analysis "
                f"experience{ending}"
            )
        if scores["Leadership"] and (scores["Analytics"] or scores["Communication"]):
            return "Analytical communicator with leadership and operations proof."
        strongest_type = ReviewProposalType(memories[0].memory_type)
        if strongest_type is ReviewProposalType.EXPERIENCE:
            return "Experience-led contributor with approved, role-relevant proof."
        if strongest_type is ReviewProposalType.EDUCATION:
            return "Emerging professional with a strong approved education foundation."
        return "Evidence-led early-career professional with an emerging through-line."

    def _identity_rationale(
        self,
        memories: list[CanonicalMemoryRecord],
        evidence_map: list[dict[str, Any]],
        approved_feedback: list[CareerFeedbackEvent],
        inputs: DiagnosisInputs,
    ) -> str:
        top_titles = ", ".join(item["memory_title"] for item in evidence_map[:3])
        rationale = (
            f"This is an inference across {len(memories)} approved memories, led by "
            f"{top_titles}. The evidence map separates those approved records from "
            "CareerOS's interpretation."
        )
        if inputs.target_role or inputs.target_context or inputs.frustration_context:
            rationale += (
                " Your target and context changed relevance ordering, but were not "
                "treated as proof."
            )
        if self._context_denies_leadership(inputs.frustration_context) and any(
            "Leadership" in item["relevant_themes"] for item in evidence_map
        ):
            rationale += (
                " Although your context questions your leadership, approved memory "
                "contains leadership evidence; the likely issue is recognition or "
                "framing, not a total absence of proof."
            )
        if approved_feedback:
            rationale += (
                f" {len(approved_feedback)} approved Teach CareerOS event(s) informed "
                "framing as user guidance, not as canonical factual evidence."
            )
        return rationale

    @staticmethod
    def _outcome_signals(
        approved_feedback: list[CareerFeedbackEvent],
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        for event in approved_feedback:
            if event.event_type != FeedbackEventType.ARTIFACT_SUCCESS.value:
                continue
            parsed = CareerFeedbackService.parse_note(event.raw_note)
            artifact_type = (
                FeedbackArtifactType(event.artifact_type)
                if event.artifact_type
                else parsed.artifact_type
            )
            artifact_label = event.artifact_label or parsed.artifact_label
            outcome = (
                FeedbackOutcomeType(event.outcome) if event.outcome else parsed.outcome
            )
            if outcome is None:
                continue
            label = artifact_label or "artifact"
            outcome_phrase = {
                FeedbackOutcomeType.INTERVIEW_INVITE: "led to an interview invite",
                FeedbackOutcomeType.CALLBACK: "received a callback",
                FeedbackOutcomeType.OFFER: "was associated with an offer",
            }[outcome]
            signals.append(
                {
                    "feedback_event_id": str(event.id),
                    "artifact_type": artifact_type.value if artifact_type else None,
                    "artifact_label": artifact_label,
                    "outcome": outcome.value,
                    "summary": (
                        f"An approved outcome note says the {label} {outcome_phrase}. "
                        "Treat this as a signal that this framing worked once, not "
                        "proof that it caused the result."
                    ),
                    "guidance": event.suggested_future_use
                    or parsed.suggested_future_use,
                    "caveat": (
                        "Outcome signals guide strategy but are not canonical proof "
                        "of skill or causality."
                    ),
                }
            )
        return signals

    def _recognition_gap(
        self,
        memories: list[CanonicalMemoryRecord],
        scores: dict[str, int],
        approved_feedback: list[CareerFeedbackEvent],
        outcome_signals: list[dict[str, Any]],
        inputs: DiagnosisInputs,
    ) -> str:
        combined = " ".join(self._memory_text(memory) for memory in memories)
        target_themes = self._target_themes(inputs)
        has_project = any(memory.memory_type == "PROJECT" for memory in memories)
        has_packaging = self._contains(
            combined, "case study", "portfolio", "github", "readme", "demo", "dashboard"
        )
        has_business_framing = self._contains(
            combined,
            "business",
            "stakeholder",
            "recommendation",
            "decision",
            "customer",
            "client",
        )
        has_ai_product = any(
            memory.memory_type in {"PROJECT", "EXPERIENCE"}
            and "AI / Automation" in self._themes(self._memory_text(memory))
            for memory in memories
        )
        if "AI / Automation" in target_themes and not has_ai_product:
            gap = (
                "Your approved memory supports analytical ability, but deployable AI "
                "or automation product proof is thin. The bottleneck is recognizable "
                "build evidence, not stated interest."
            )
        elif (
            "Analytics" in target_themes
            and has_project
            and scores["Research"]
            and not has_business_framing
        ):
            gap = (
                "Your strongest proof is analytical research depth, but it is not yet "
                "packaged in business-facing language. An evaluator may recognize the "
                "domain topic before recognizing analysis, uncertainty, and decision "
                "value."
            )
        elif has_project and not has_packaging:
            gap = (
                "Relevant project proof exists, but it is not yet easy to inspect. "
                "The recognition gap is packaging: a reviewer has to infer too much "
                "from titles and skill lists."
            )
        elif scores["Leadership"] and "Leadership" in target_themes:
            gap = (
                "Leadership proof exists, but its connection to the target is not "
                "explicit. The gap is role-specific framing and a concrete operating "
                "result."
            )
        else:
            gap = (
                "Approved experiences support a plausible direction, but external "
                "validation and role-specific proof are limited. The main bottleneck "
                "is "
                "recognizable evidence, not application volume."
            )
        enriched_project = next(
            (
                memory
                for memory in memories
                if memory.memory_type == "PROJECT"
                and (profile := self._compiled_profiles.get(memory.id)) is not None
                and profile.enrichment_ids_used
                and profile.methods
                and profile.data_or_inputs
            ),
            None,
        )
        if enriched_project is not None:
            gap += (
                f" Your {enriched_project.title} project now has stronger proof "
                "because its approved method, data, and limitations are documented."
            )
        if approved_feedback:
            gap += (
                " Approved Teach CareerOS notes shape this strategy, but remain "
                "user-reported learning inputs rather than canonical proof."
            )
        if outcome_signals:
            gap += f" {outcome_signals[0]['summary']}"
        return gap

    def _missing_proof(
        self,
        memories: list[CanonicalMemoryRecord],
        scores: dict[str, int],
        inputs: DiagnosisInputs,
    ) -> list[str]:
        combined = " ".join(self._memory_text(memory) for memory in memories)
        target_themes = self._target_themes(inputs)
        gaps: list[str] = []
        if not self._contains(
            combined, "case study", "portfolio", "readme", "demo", "dashboard"
        ):
            gaps.append(
                "A role-specific, inspectable case study of the strongest project."
            )
        if "Analytics" in target_themes and not self._contains(
            combined, "dashboard", "reporting", "business insight"
        ):
            gaps.append("A dashboard or reporting artifact framed around a decision.")
        if "AI / Automation" in target_themes and not any(
            memory.memory_type in {"PROJECT", "EXPERIENCE"}
            and "AI / Automation" in self._themes(self._memory_text(memory))
            for memory in memories
        ):
            gaps.append("A runnable AI/automation demo with a concise GitHub README.")
        if not self._contains(
            combined,
            "impact",
            "outcome",
            "result",
            "improved",
            "reduced",
            "increased",
            "recommendation",
        ):
            gaps.append(
                "A business-impact summary that states the decision or outcome."
            )
        if not any(memory.memory_type == "ACHIEVEMENT" for memory in memories):
            gaps.append(
                "External validation from a reviewer, mentor, user, or evaluator."
            )
        if scores["Leadership"] and "Leadership" in target_themes:
            gaps.append(
                "A leadership example tied to an operating result and target need."
            )
        return list(dict.fromkeys(gaps))[:3]

    def _proof_sprint(
        self,
        strongest: dict[str, Any],
        scores: dict[str, int],
        outcome_signals: list[dict[str, Any]],
        inputs: DiagnosisInputs,
    ) -> dict[str, Any]:
        title = strongest["memory_title"]
        target = self._target_label(inputs)
        target_themes = self._target_themes(inputs)
        if "AI / Automation" in target_themes:
            artifact = (
                f"A concise README and two-minute demo that frames {title} for "
                f"{target}."
            )
        elif "Analytics" in target_themes or scores["Analytics"]:
            artifact = (
                f"A one-page case study of {title} with problem, method, visual, "
                "finding, and decision implication."
            )
        else:
            artifact = f"A one-page target-facing proof brief for {title}."
        day_five = (
            "Day 5: ask one target-aware reviewer what they recognize in 30 seconds."
        )
        application_use = (
            "Link or attach it in targeted applications, use its opening sentence "
            "in outreach, and ask reviewers about the specific claim it demonstrates."
        )
        if outcome_signals:
            outcome_label = outcome_signals[0].get("artifact_label") or "the artifact"
            day_five = (
                f"Day 5: compare the framing with {outcome_label}, which has one "
                "user-reported positive outcome, then ask a target-aware reviewer "
                "what they recognize in 30 seconds."
            )
            application_use += (
                f" Reuse the role-specific clarity from {outcome_label} where it "
                "fits; treat its outcome as a one-time signal, not a guarantee."
            )
        return {
            "objective": f"Package {title} as recognizable proof for {target}.",
            "actions": [
                f"Day 1: choose one claim from {title} that the target must recognize.",
                "Day 2: collect only the approved facts and evidence references that "
                "support it.",
                "Days 3-4: build the one-page artifact with problem, action, "
                "evidence, and implication.",
                day_five,
                "Days 6-7: revise once, publish or attach it, and send three targeted "
                "messages.",
            ],
            "expected_artifact": artifact,
            "why_it_matters": (
                "It converts an existing approved memory into proof an evaluator can "
                "recognize without guessing."
            ),
            "evidence_to_strengthen": [
                str(strongest["memory_id"]),
                *strongest["evidence_ids"],
            ],
            "application_use": application_use,
        }

    def _do_not_waste_time(
        self,
        memories: list[CanonicalMemoryRecord],
        scores: dict[str, int],
        strongest: dict[str, Any],
        inputs: DiagnosisInputs,
    ) -> str:
        target_themes = self._target_themes(inputs)
        if (
            "Analytics" in target_themes
            and scores["Research"]
            and strongest["memory_type"] == ReviewProposalType.PROJECT.value
        ):
            return (
                f"Do not lead with the domain label of {strongest['memory_title']} for "
                "analytics roles; lead with analysis, modeling, uncertainty, and "
                "communication, then explain the domain."
            )
        if any(memory.memory_type == "PROJECT" for memory in memories):
            return (
                "Do not build a brand-new project this week before packaging "
                f"{strongest['memory_title']}, the strongest proof you already have."
            )
        return (
            "Do not send a high volume of identical applications while your strongest "
            "approved experience is still hard to recognize; package that proof first."
        )

    def _exact_messages(
        self,
        strongest: dict[str, Any],
        outcome_signals: list[dict[str, Any]],
        inputs: DiagnosisInputs,
    ) -> dict[str, str]:
        target = self._target_label(inputs)
        title = strongest["memory_title"]
        themes = ", ".join(strongest["relevant_themes"][:3]).lower()
        outcome_guidance = ""
        if outcome_signals:
            outcome_label = outcome_signals[0].get("artifact_label") or "the artifact"
            outcome_guidance = (
                f" Reuse the role-specific framing pattern from {outcome_label} "
                "where relevant; its positive result is one outcome signal, not "
                "proof of causality."
            )
        return {
            "linkedin_outreach": (
                f"Hi [Name] — I’m targeting {target} roles and am packaging {title} "
                f"as proof of {themes}. Would you be open to a 15-minute review of "
                "the one-page case study? I’d value one answer: what capability is "
                "clear in the first 30 seconds, and what is still hard to recognize?"
            ),
            "email_or_referral": (
                f"Subject: Quick proof review for {target}\n\nHi [Name],\n\nI’m "
                f"positioning {title} for {target} opportunities. My approved evidence "
                f"supports {themes}, and I’m turning it into a concise case study "
                "rather than starting another project. Could you review it and tell "
                "me whether "
                "the target-relevant value is obvious?\n\nThank you,\n[Your name]"
            ),
            "application_positioning": (
                f"For {target}, I would lead with {title}: it provides approved "
                "evidence "
                f"of {themes}. I would frame the work around the problem, method, and "
                "decision implication without claiming an outcome that is not "
                f"documented.{outcome_guidance}"
            ),
        }

    def _session_view(
        self, session: Session, record: DiagnosisSession
    ) -> DiagnosisSessionView:
        result = session.scalar(
            select(DiagnosisResult).where(DiagnosisResult.session_id == record.id)
        )
        if result is None:
            raise DiagnosisNotFoundError("Career diagnosis result not found.")
        return DiagnosisSessionView(
            id=record.id,
            target_role=record.target_role,
            target_context=record.target_context,
            frustration_context=record.frustration_context,
            selected_focus=(
                DiagnosisFocus(record.selected_focus) if record.selected_focus else None
            ),
            status=DiagnosisSessionStatus(record.status),
            result=self._result_view(result),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _result_view(result: DiagnosisResult) -> DiagnosisResultView:
        return DiagnosisResultView(
            id=result.id,
            session_id=result.session_id,
            career_identity=result.career_identity,
            identity_rationale=result.identity_rationale,
            evidence_map=[EvidenceMapItem(**item) for item in result.evidence_map],
            recognition_gap=result.recognition_gap,
            missing_proof=result.missing_proof,
            proof_sprint=ProofSprint(**result.proof_sprint),
            do_not_waste_time=result.do_not_waste_time,
            exact_next_actions=result.exact_next_actions,
            exact_messages=result.exact_messages,
            confidence=float(result.confidence),
            evidence_ids=result.evidence_ids,
            feedback_event_ids=result.feedback_event_ids,
            outcome_signals=[
                OutcomeSignal(**signal) for signal in result.outcome_signals
            ],
            diagnosis_version=result.diagnosis_version,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )

    def _get_session(
        self, session: Session, diagnosis_session_id: uuid.UUID
    ) -> DiagnosisSession:
        record = session.get(DiagnosisSession, diagnosis_session_id)
        if record is None or record.user_id != self.user_id:
            raise DiagnosisNotFoundError("Career diagnosis session not found.")
        return record

    def _theme_scores(self, memories: list[CanonicalMemoryRecord]) -> dict[str, int]:
        scores = dict.fromkeys(self.theme_keywords, 0)
        for memory in memories:
            for theme in self._themes(self._memory_text(memory)):
                scores[theme] += 1
        return scores

    def _target_themes(self, inputs: DiagnosisInputs) -> set[str]:
        themes = set(
            self.focus_themes.get(
                inputs.selected_focus or DiagnosisFocus.GENERAL, set()
            )
        )
        target_text = f" {inputs.target_role or ''} {inputs.target_context or ''} "
        themes.update(self._themes(target_text))
        return themes

    def _target_label(self, inputs: DiagnosisInputs) -> str:
        if inputs.target_role:
            return inputs.target_role
        if (
            inputs.selected_focus
            and inputs.selected_focus is not DiagnosisFocus.GENERAL
        ):
            return inputs.selected_focus.value.replace("_", " ").title()
        return "your next role"

    def _themes(self, text: str) -> list[str]:
        padded = f" {text.casefold()} "
        return [
            theme
            for theme, keywords in self.theme_keywords.items()
            if any(keyword in padded for keyword in keywords)
        ]

    @staticmethod
    def _fallback_theme(memory_type: ReviewProposalType) -> str:
        return {
            ReviewProposalType.PROJECT: "Project delivery",
            ReviewProposalType.EXPERIENCE: "Professional experience",
            ReviewProposalType.EDUCATION: "Education",
            ReviewProposalType.PROGRAM: "Program participation",
            ReviewProposalType.SKILL_SET: "Documented skills",
            ReviewProposalType.ACHIEVEMENT: "External validation",
            ReviewProposalType.ORGANIZATION: "Community involvement",
            ReviewProposalType.CONTACT: "Contact information",
            ReviewProposalType.NEEDS_CLASSIFICATION: "Approved memory",
        }[memory_type]

    @staticmethod
    def _claim_supported(
        title: str, memory_type: ReviewProposalType, themes: list[str]
    ) -> str:
        theme_text = ", ".join(themes[:3]).lower()
        descriptions = {
            ReviewProposalType.PROJECT: "project-based proof",
            ReviewProposalType.EXPERIENCE: "experience-based proof",
            ReviewProposalType.EDUCATION: "an education foundation",
            ReviewProposalType.PROGRAM: "program participation",
            ReviewProposalType.SKILL_SET: "approved skill claims",
            ReviewProposalType.ACHIEVEMENT: "external validation",
            ReviewProposalType.ORGANIZATION: "organization involvement",
            ReviewProposalType.CONTACT: "contact context",
            ReviewProposalType.NEEDS_CLASSIFICATION: "an approved claim",
        }
        return f"{title} supports {descriptions[memory_type]} in {theme_text}."

    def _memory_text(self, memory: CanonicalMemoryRecord) -> str:
        profile = self._compiled_profiles.get(memory.id)
        if profile is not None:
            return compiled_profile_factual_text(profile)
        return " ".join([memory.title, *self._flatten(memory.structured_fields)])

    @classmethod
    def _flatten(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, dict):
            return [part for nested in value.values() for part in cls._flatten(nested)]
        if isinstance(value, (list, tuple, set)):
            return [part for nested in value for part in cls._flatten(nested)]
        return [str(value)]

    @staticmethod
    def _contains(text: str, *needles: str) -> bool:
        lowered = text.casefold()
        return any(needle in lowered for needle in needles)

    @staticmethod
    def _context_denies_leadership(context: str | None) -> bool:
        if not context:
            return False
        return bool(
            re.search(r"\b(no|lack|lacking|without)\s+leadership\b", context, re.I)
        )

    def _ensure_user(self, session: Session) -> None:
        if session.get(User, self.user_id) is None:
            session.add(
                User(
                    id=self.user_id,
                    clerk_user_id=f"diagnosis-demo-{self.user_id}",
                    email=f"diagnosis-demo-{self.user_id}@example.invalid",
                    display_name="Diagnosis Demo User",
                )
            )
            session.flush()


class CareerFeedbackService:
    """Parse, persist, and review user-authored CareerOS learning events."""

    def __init__(self, user_id: uuid.UUID = DEMO_USER_ID) -> None:
        self.user_id = user_id

    def create(
        self, session: Session, request: FeedbackEventCreateRequest
    ) -> FeedbackEventView:
        self._ensure_user(session)
        parsed = self.parse_note(request.raw_note)
        duplicate = self._find_duplicate(session, request.raw_note, parsed)
        if duplicate is not None:
            raise DuplicateFeedbackEventError(duplicate.id)
        related_ids = self._validated_memory_ids(session, request.related_memory_ids)
        obvious_ids = self._obvious_memory_ids(session, request.raw_note)
        self._validate_application_links(
            session, request.related_opportunity_id, request.related_draft_id
        )
        record = CareerFeedbackEvent(
            user_id=self.user_id,
            raw_note=request.raw_note,
            event_type=parsed.event_type.value,
            structured_summary=parsed.structured_summary,
            artifact_type=(
                parsed.artifact_type.value if parsed.artifact_type else None
            ),
            artifact_label=parsed.artifact_label,
            outcome=parsed.outcome.value if parsed.outcome else None,
            event_metadata=parsed.metadata,
            related_memory_ids=list(dict.fromkeys([*related_ids, *obvious_ids])),
            related_opportunity_id=request.related_opportunity_id,
            related_draft_id=request.related_draft_id,
            suggested_future_use=parsed.suggested_future_use,
            status=request.status.value,
        )
        session.add(record)
        session.commit()
        return self._view(record)

    def list(self, session: Session) -> list[FeedbackEventView]:
        records = session.scalars(
            select(CareerFeedbackEvent)
            .where(CareerFeedbackEvent.user_id == self.user_id)
            .order_by(CareerFeedbackEvent.created_at.desc())
        ).all()
        return [self._view(record) for record in records]

    def update(
        self,
        session: Session,
        feedback_event_id: uuid.UUID,
        request: FeedbackEventUpdateRequest,
    ) -> FeedbackEventView:
        record = self._get(session, feedback_event_id)
        if request.raw_note is not None:
            record.raw_note = request.raw_note
            parsed = self.parse_note(request.raw_note)
            record.event_type = parsed.event_type.value
            record.structured_summary = parsed.structured_summary
            record.artifact_type = (
                parsed.artifact_type.value if parsed.artifact_type else None
            )
            record.artifact_label = parsed.artifact_label
            record.outcome = parsed.outcome.value if parsed.outcome else None
            record.event_metadata = parsed.metadata
            record.suggested_future_use = parsed.suggested_future_use
            record.related_memory_ids = list(
                dict.fromkeys(
                    [
                        *record.related_memory_ids,
                        *self._obvious_memory_ids(session, request.raw_note),
                    ]
                )
            )
        if request.event_type is not None:
            record.event_type = request.event_type.value
        if request.structured_summary is not None:
            record.structured_summary = request.structured_summary
        if "artifact_type" in request.model_fields_set:
            record.artifact_type = (
                request.artifact_type.value if request.artifact_type else None
            )
        if "artifact_label" in request.model_fields_set:
            record.artifact_label = request.artifact_label
        if "outcome" in request.model_fields_set:
            record.outcome = request.outcome.value if request.outcome else None
        if request.related_memory_ids is not None:
            record.related_memory_ids = self._validated_memory_ids(
                session, request.related_memory_ids
            )
        opportunity_id = (
            request.related_opportunity_id
            if "related_opportunity_id" in request.model_fields_set
            else record.related_opportunity_id
        )
        draft_id = (
            request.related_draft_id
            if "related_draft_id" in request.model_fields_set
            else record.related_draft_id
        )
        self._validate_application_links(session, opportunity_id, draft_id)
        record.related_opportunity_id = opportunity_id
        record.related_draft_id = draft_id
        if request.suggested_future_use is not None:
            record.suggested_future_use = request.suggested_future_use
        if request.status is not None:
            record.status = request.status.value
        session.commit()
        return self._view(record)

    @classmethod
    def parse_note(cls, note: str) -> ParsedFeedback:
        clean_note = " ".join(note.split())
        lowered = clean_note.casefold()
        artifact_type = cls._artifact_type(clean_note)
        outcome = cls._outcome(clean_note)
        if any(
            phrase in lowered
            for phrase in ("do not use", "don't use", "never use", "avoid using")
        ):
            event_type = FeedbackEventType.MEMORY_USAGE_RULE
        elif any(
            phrase in lowered
            for phrase in (
                "use ",
                "position ",
                "positioning",
                "frame ",
                "framing",
                "strongest for",
                "not as",
            )
        ) and any(phrase in lowered for phrase in (" as ", " for ", "role", "story")):
            event_type = FeedbackEventType.POSITIONING_RULE
        elif outcome is not None and artifact_type is not None:
            event_type = FeedbackEventType.ARTIFACT_SUCCESS
        elif any(
            phrase in lowered
            for phrase in ("rejected", "rejection", "application outcome", "interview")
        ):
            event_type = FeedbackEventType.APPLICATION_OUTCOME
        elif "draft" in lowered or "generic" in lowered or "too long" in lowered:
            event_type = FeedbackEventType.DRAFT_FEEDBACK
        elif len(clean_note.split()) >= 3:
            event_type = FeedbackEventType.GENERAL_LEARNING
        else:
            event_type = FeedbackEventType.UNKNOWN

        artifact_label = cls._artifact_label(clean_note, artifact_type)
        structured_summary = cls._summary(
            clean_note, event_type, artifact_label, outcome
        )
        suggested_future_use = cls._future_use(
            event_type, artifact_type, artifact_label, outcome
        )
        return ParsedFeedback(
            event_type=event_type,
            structured_summary=structured_summary,
            artifact_type=artifact_type,
            artifact_label=artifact_label,
            outcome=outcome,
            suggested_future_use=suggested_future_use,
            metadata={
                "parser_version": "feedback-deterministic-v1",
                "normalized_raw_note": cls._normalize(clean_note),
                "artifact_keywords": cls._artifact_keywords(artifact_label),
                "outcome_language": outcome.value if outcome else None,
            },
        )

    @staticmethod
    def _artifact_type(note: str) -> FeedbackArtifactType | None:
        lowered = note.casefold()
        if "cover letter" in lowered:
            return FeedbackArtifactType.COVER_LETTER
        if "resume" in lowered or "résumé" in lowered:
            return FeedbackArtifactType.RESUME
        if "application" in lowered:
            return FeedbackArtifactType.APPLICATION
        if "draft" in lowered:
            return FeedbackArtifactType.DRAFT
        if "project" in lowered or "case study" in lowered:
            return FeedbackArtifactType.PROJECT
        return None

    @staticmethod
    def _outcome(note: str) -> FeedbackOutcomeType | None:
        lowered = note.casefold()
        if "callback" in lowered or "called me back" in lowered:
            return FeedbackOutcomeType.CALLBACK
        if any(phrase in lowered for phrase in ("offer", "accepted", "hired")):
            return FeedbackOutcomeType.OFFER
        if any(
            phrase in lowered
            for phrase in (
                "interview invite",
                "interview invitation",
                "invited to interview",
                "got me an interview",
                "led to an interview",
                "resulted in an interview",
            )
        ):
            return FeedbackOutcomeType.INTERVIEW_INVITE
        return None

    @staticmethod
    def _artifact_label(
        note: str, artifact_type: FeedbackArtifactType | None
    ) -> str | None:
        if artifact_type is None:
            return None
        suffix = {
            FeedbackArtifactType.COVER_LETTER: r"cover letter",
            FeedbackArtifactType.RESUME: r"resume(?: version)?|résumé(?: version)?",
            FeedbackArtifactType.APPLICATION: r"application",
            FeedbackArtifactType.DRAFT: r"draft",
            FeedbackArtifactType.PROJECT: r"project|case study",
            FeedbackArtifactType.OTHER: r"artifact",
        }[artifact_type]
        match = re.search(
            rf"^(?:(?:the|this|my|a|an)\s+)?(.+?\b(?:{suffix}))\b",
            note,
            flags=re.IGNORECASE,
        )
        if match is None:
            return {
                FeedbackArtifactType.COVER_LETTER: "cover letter",
                FeedbackArtifactType.RESUME: "resume",
                FeedbackArtifactType.APPLICATION: "application",
                FeedbackArtifactType.DRAFT: "draft",
                FeedbackArtifactType.PROJECT: "project",
                FeedbackArtifactType.OTHER: "artifact",
            }[artifact_type]
        return match.group(1).strip(" ,.;:-")

    @staticmethod
    def _summary(
        note: str,
        event_type: FeedbackEventType,
        artifact_label: str | None,
        outcome: FeedbackOutcomeType | None,
    ) -> str:
        if event_type == FeedbackEventType.ARTIFACT_SUCCESS and outcome is not None:
            label = artifact_label or "artifact"
            outcome_phrase = {
                FeedbackOutcomeType.INTERVIEW_INVITE: "led to an interview invite",
                FeedbackOutcomeType.CALLBACK: "received a callback",
                FeedbackOutcomeType.OFFER: "was associated with an offer",
            }[outcome]
            return (
                f"User reports that {label} {outcome_phrase}. "
                "This is an association, not a proven cause."
            )
        prefixes = {
            FeedbackEventType.ARTIFACT_SUCCESS: (
                "User reports a positive artifact outcome: "
            ),
            FeedbackEventType.APPLICATION_OUTCOME: (
                "User-reported application outcome: "
            ),
            FeedbackEventType.DRAFT_FEEDBACK: "User feedback about draft quality: ",
            FeedbackEventType.POSITIONING_RULE: "User-defined positioning rule: ",
            FeedbackEventType.MEMORY_USAGE_RULE: "User-defined memory usage rule: ",
            FeedbackEventType.GENERAL_LEARNING: "User-authored career learning: ",
            FeedbackEventType.UNKNOWN: "Unclassified user note: ",
        }
        return f"{prefixes[event_type]}{note.strip()}"

    @classmethod
    def _future_use(
        cls,
        event_type: FeedbackEventType,
        artifact_type: FeedbackArtifactType | None,
        artifact_label: str | None,
        outcome: FeedbackOutcomeType | None,
    ) -> str:
        if (
            event_type == FeedbackEventType.ARTIFACT_SUCCESS
            and artifact_type == FeedbackArtifactType.COVER_LETTER
            and outcome == FeedbackOutcomeType.INTERVIEW_INVITE
        ):
            label_words = set(cls._artifact_keywords(artifact_label))
            if label_words & {"jsom", "elearning", "recording", "studio", "assistant"}:
                return (
                    "Use this artifact and framing for similar campus, student-worker, "
                    "technical communication, or department-specific roles; treat "
                    "the result as a one-time signal."
                )
            return (
                "Use this cover-letter framing for similar roles; treat the interview "
                "invite as a one-time outcome signal, not proof of causality."
            )
        if event_type == FeedbackEventType.ARTIFACT_SUCCESS and artifact_type:
            label = artifact_label or artifact_type.value.replace("_", " ").lower()
            return (
                f"Consider the framing from {label} for similar roles; treat the "
                "result as a one-time outcome signal, not proof of causality."
            )
        return {
            FeedbackEventType.ARTIFACT_SUCCESS: (
                "Consider this artifact and framing in future drafts; do not infer "
                "causality from one outcome."
            ),
            FeedbackEventType.APPLICATION_OUTCOME: (
                "Keep this outcome linked to its opportunity or draft for future "
                "pattern review."
            ),
            FeedbackEventType.DRAFT_FEEDBACK: (
                "Use this preference when judging future draft specificity and tone."
            ),
            FeedbackEventType.POSITIONING_RULE: (
                "Apply this framing when the target matches, while keeping factual "
                "claims grounded in approved memory."
            ),
            FeedbackEventType.MEMORY_USAGE_RULE: (
                "Respect this boundary when selecting or framing memory in future work."
            ),
            FeedbackEventType.GENERAL_LEARNING: (
                "Retain as user guidance and revisit when future evidence makes it "
                "relevant."
            ),
            FeedbackEventType.UNKNOWN: (
                "Review and classify this note before using it in a diagnosis."
            ),
        }[event_type]

    def _find_duplicate(
        self, session: Session, raw_note: str, parsed: ParsedFeedback
    ) -> CareerFeedbackEvent | None:
        normalized_note = self._normalize(raw_note)
        parsed_label = self._normalize(parsed.artifact_label or "")
        parsed_keywords = set(self._artifact_keywords(parsed.artifact_label))
        records = session.scalars(
            select(CareerFeedbackEvent).where(
                CareerFeedbackEvent.user_id == self.user_id
            )
        ).all()
        for record in records:
            existing = self.parse_note(record.raw_note)
            if existing.event_type != parsed.event_type:
                continue
            existing_note = self._normalize(record.raw_note)
            if existing_note == normalized_note:
                return record
            if self._normalize(record.structured_summary) == self._normalize(
                parsed.structured_summary
            ):
                return record
            existing_artifact_type = record.artifact_type or (
                existing.artifact_type.value if existing.artifact_type else None
            )
            existing_outcome = record.outcome or (
                existing.outcome.value if existing.outcome else None
            )
            same_artifact_outcome = (
                existing_artifact_type
                == (parsed.artifact_type.value if parsed.artifact_type else None)
                and existing_outcome
                == (parsed.outcome.value if parsed.outcome else None)
                and parsed.outcome is not None
            )
            if same_artifact_outcome:
                existing_label = self._normalize(
                    record.artifact_label or existing.artifact_label or ""
                )
                if existing_label and existing_label == parsed_label:
                    return record
                existing_keywords = set(
                    self._artifact_keywords(
                        record.artifact_label or existing.artifact_label
                    )
                )
                shared = existing_keywords & parsed_keywords
                combined = existing_keywords | parsed_keywords
                if combined and len(shared) / len(combined) >= 0.6:
                    return record
            if SequenceMatcher(None, existing_note, normalized_note).ratio() >= 0.9:
                return record
        return None

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))

    @staticmethod
    def _artifact_keywords(value: str | None) -> list[str]:
        ignored = {
            "a",
            "an",
            "application",
            "cover",
            "letter",
            "my",
            "resume",
            "the",
            "this",
            "version",
        }
        return [
            word
            for word in re.findall(r"[a-z0-9]+", (value or "").casefold())
            if len(word) > 1 and word not in ignored
        ]

    def _obvious_memory_ids(self, session: Session, note: str) -> list[str]:
        note_words = set(self._significant_words(note))
        note_lower = note.casefold()
        related: list[str] = []
        memories = session.scalars(
            select(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.user_id == self.user_id
            )
        ).all()
        for memory in memories:
            title_lower = memory.title.casefold()
            title_words = set(self._significant_words(memory.title))
            if title_lower in note_lower or (
                len(title_words) >= 2 and len(title_words & note_words) >= 2
            ):
                related.append(str(memory.id))
        return related

    def _validated_memory_ids(
        self, session: Session, memory_ids: list[uuid.UUID]
    ) -> list[str]:
        validated: list[str] = []
        for memory_id in memory_ids:
            memory = session.get(CanonicalMemoryRecord, memory_id)
            if memory is None or memory.user_id != self.user_id:
                raise DiagnosisNotFoundError("Related Career Memory was not found.")
            validated.append(str(memory_id))
        return validated

    def _validate_application_links(
        self,
        session: Session,
        opportunity_id: uuid.UUID | None,
        draft_id: uuid.UUID | None,
    ) -> None:
        opportunity = None
        if opportunity_id is not None:
            opportunity = session.get(ApplicationOpportunity, opportunity_id)
            if opportunity is None or opportunity.user_id != self.user_id:
                raise DiagnosisNotFoundError(
                    "Related application opportunity not found."
                )
        if draft_id is not None:
            draft = session.get(ApplicationDraft, draft_id)
            if draft is None or draft.user_id != self.user_id:
                raise DiagnosisNotFoundError("Related application draft not found.")
            if opportunity is not None and draft.opportunity_id != opportunity.id:
                raise DiagnosisNotFoundError(
                    "Related draft does not belong to the selected opportunity."
                )

    def _get(
        self, session: Session, feedback_event_id: uuid.UUID
    ) -> CareerFeedbackEvent:
        record = session.get(CareerFeedbackEvent, feedback_event_id)
        if record is None or record.user_id != self.user_id:
            raise DiagnosisNotFoundError("Career feedback event not found.")
        return record

    @staticmethod
    def _view(record: CareerFeedbackEvent) -> FeedbackEventView:
        return FeedbackEventView(
            id=record.id,
            raw_note=record.raw_note,
            event_type=FeedbackEventType(record.event_type),
            structured_summary=record.structured_summary,
            artifact_type=(
                FeedbackArtifactType(record.artifact_type)
                if record.artifact_type
                else None
            ),
            artifact_label=record.artifact_label,
            outcome=(FeedbackOutcomeType(record.outcome) if record.outcome else None),
            event_metadata=record.event_metadata,
            related_memory_ids=record.related_memory_ids,
            related_opportunity_id=record.related_opportunity_id,
            related_draft_id=record.related_draft_id,
            suggested_future_use=record.suggested_future_use,
            status=FeedbackEventStatus(record.status),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _significant_words(value: str) -> list[str]:
        ignored = {"with", "from", "this", "that", "honors", "project", "the"}
        return [
            word
            for word in re.findall(r"[a-z0-9]+", value.casefold())
            if len(word) > 2 and word not in ignored
        ]

    def _ensure_user(self, session: Session) -> None:
        if session.get(User, self.user_id) is None:
            session.add(
                User(
                    id=self.user_id,
                    clerk_user_id=f"feedback-demo-{self.user_id}",
                    email=f"feedback-demo-{self.user_id}@example.invalid",
                    display_name="Feedback Demo User",
                )
            )
            session.flush()

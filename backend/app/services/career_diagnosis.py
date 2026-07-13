"""Deterministic Career Diagnosis and Teach CareerOS services."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
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
    User,
)
from app.schemas.diagnosis import (
    DiagnosisFocus,
    DiagnosisResultView,
    DiagnosisSessionCreateRequest,
    DiagnosisSessionStatus,
    DiagnosisSessionView,
    EvidenceMapItem,
    FeedbackEventCreateRequest,
    FeedbackEventStatus,
    FeedbackEventType,
    FeedbackEventUpdateRequest,
    FeedbackEventView,
    ProofSprint,
)
from app.schemas.knowledge import DEMO_USER_ID, ReviewProposalType


class DiagnosisNotFoundError(LookupError):
    """Raised when a user-scoped diagnosis object is unavailable."""


@dataclass(frozen=True)
class DiagnosisInputs:
    target_role: str | None
    target_context: str | None
    frustration_context: str | None
    selected_focus: DiagnosisFocus | None


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

    def __init__(self, user_id: uuid.UUID = DEMO_USER_ID) -> None:
        self.user_id = user_id

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
            select(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.user_id == self.user_id
            )
        ).all()
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
        recognition_gap = self._recognition_gap(
            memories, theme_scores, approved_feedback, inputs
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
        proof_sprint = self._proof_sprint(proof_source, theme_scores, inputs)
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
        exact_messages = self._exact_messages(proof_source, inputs)
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

    def _recognition_gap(
        self,
        memories: list[CanonicalMemoryRecord],
        scores: dict[str, int],
        approved_feedback: list[CareerFeedbackEvent],
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
        if approved_feedback:
            gap += (
                " Approved Teach CareerOS notes shape this strategy, but remain "
                "user-reported learning inputs rather than canonical proof."
            )
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
        return {
            "objective": f"Package {title} as recognizable proof for {target}.",
            "actions": [
                f"Day 1: choose one claim from {title} that the target must recognize.",
                "Day 2: collect only the approved facts and evidence references that "
                "support it.",
                "Days 3-4: build the one-page artifact with problem, action, "
                "evidence, and implication.",
                "Day 5: ask one target-aware reviewer what they recognize in 30 "
                "seconds.",
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
            "application_use": (
                "Link or attach it in targeted applications, use its opening sentence "
                "in outreach, and ask reviewers about the specific claim it "
                "demonstrates."
            ),
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
        self, strongest: dict[str, Any], inputs: DiagnosisInputs
    ) -> dict[str, str]:
        target = self._target_label(inputs)
        title = strongest["memory_title"]
        themes = ", ".join(strongest["relevant_themes"][:3]).lower()
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
                "documented."
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

    @classmethod
    def _memory_text(cls, memory: CanonicalMemoryRecord) -> str:
        return " ".join([memory.title, *cls._flatten(memory.structured_fields)])

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
        related_ids = self._validated_memory_ids(session, request.related_memory_ids)
        obvious_ids = self._obvious_memory_ids(session, request.raw_note)
        self._validate_application_links(
            session, request.related_opportunity_id, request.related_draft_id
        )
        event_type = self._event_type(request.raw_note)
        record = CareerFeedbackEvent(
            user_id=self.user_id,
            raw_note=request.raw_note,
            event_type=event_type.value,
            structured_summary=self._summary(request.raw_note, event_type),
            related_memory_ids=list(dict.fromkeys([*related_ids, *obvious_ids])),
            related_opportunity_id=request.related_opportunity_id,
            related_draft_id=request.related_draft_id,
            suggested_future_use=self._future_use(event_type),
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
            parsed_type = self._event_type(request.raw_note)
            record.event_type = parsed_type.value
            record.structured_summary = self._summary(request.raw_note, parsed_type)
            record.suggested_future_use = self._future_use(parsed_type)
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

    @staticmethod
    def _event_type(note: str) -> FeedbackEventType:
        lowered = note.casefold()
        if any(
            phrase in lowered
            for phrase in ("do not use", "don't use", "never use", "avoid using")
        ):
            return FeedbackEventType.MEMORY_USAGE_RULE
        if any(
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
            return FeedbackEventType.POSITIONING_RULE
        positive = any(
            phrase in lowered
            for phrase in (
                "interview invite",
                "got me an interview",
                "led to an interview",
                "offer",
                "accepted",
                "successful",
            )
        )
        artifact = any(
            phrase in lowered
            for phrase in ("cover letter", "draft", "resume", "project", "case study")
        )
        if positive and artifact:
            return FeedbackEventType.ARTIFACT_SUCCESS
        if any(
            phrase in lowered
            for phrase in ("rejected", "rejection", "application outcome", "interview")
        ):
            return FeedbackEventType.APPLICATION_OUTCOME
        if "draft" in lowered or "generic" in lowered or "too long" in lowered:
            return FeedbackEventType.DRAFT_FEEDBACK
        if len(note.split()) >= 3:
            return FeedbackEventType.GENERAL_LEARNING
        return FeedbackEventType.UNKNOWN

    @staticmethod
    def _summary(note: str, event_type: FeedbackEventType) -> str:
        prefixes = {
            FeedbackEventType.ARTIFACT_SUCCESS: (
                "User reports a positive artifact outcome; this is an association, "
                "not a proven cause: "
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

    @staticmethod
    def _future_use(event_type: FeedbackEventType) -> str:
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

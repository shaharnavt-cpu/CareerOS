"""Deterministic Application Intelligence over approved Career Memory."""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    ApplicationDraft,
    ApplicationMemoryMatch,
    ApplicationOpportunity,
    ApplicationQuestion,
    CanonicalMemoryRecord,
    Story,
    StoryEvidence,
    User,
)
from app.schemas.applications import (
    MEMORY_TYPE_WEIGHT,
    ApplicationDraftLength,
    ApplicationDraftRequest,
    ApplicationDraftResponse,
    ApplicationDraftStatus,
    ApplicationDraftType,
    ApplicationDraftUpdateRequest,
    ApplicationDraftView,
    ApplicationMatchResponse,
    ApplicationMemoryMatchView,
    ApplicationOpportunityCreateRequest,
    ApplicationOpportunityListItem,
    ApplicationOpportunityStatus,
    ApplicationOpportunityView,
    ApplicationQuestionCreateRequest,
    ApplicationQuestionStatus,
    ApplicationQuestionType,
    ApplicationQuestionView,
    ApplicationStoryContext,
)
from app.schemas.knowledge import (
    DEMO_USER_ID,
    CanonicalReviewMemory,
    ReviewProposalType,
)
from app.schemas.stories import StoryStatus


@dataclass(frozen=True)
class OpportunityAnalysis:
    title: str
    organization: str | None
    role_type: str | None
    skills: list[str]
    keywords: list[str]
    responsibilities: list[str]
    questions: list[str]


@dataclass(frozen=True)
class MatchCandidate:
    memory: CanonicalMemoryRecord
    score: float
    reason: str
    themes: list[str]


class ApplicationNotFoundError(LookupError):
    """Raised when an application resource is not owned by the current user."""


class ApplicationIntelligenceService:
    """Analyze opportunities and draft answers from approved Career Memory only."""

    skill_vocab = {
        "python": "Python",
        "sql": "SQL",
        "mysql": "MySQL",
        "excel": "Excel",
        "r": "R",
        "tableau": "Tableau",
        "power bi": "Power BI",
        "dashboard": "Dashboarding",
        "dashboarding": "Dashboarding",
        "analytics": "Analytics",
        "data analysis": "Data Analysis",
        "machine learning": "Machine Learning",
        "statistics": "Statistics",
        "reporting": "Reporting",
        "visual": "Data Visualization",
        "visualization": "Data Visualization",
    }
    role_keywords = {
        "internship": ("intern", "internship"),
        "analytics": ("analytics", "analyst", "analysis"),
        "data": ("data", "dataset", "datasets"),
        "research": ("research", "experiment", "scientific"),
        "ai": ("ai", "machine learning", "ml"),
        "finance": ("finance", "financial", "investment"),
        "student worker": ("student worker",),
        "full-time": ("full-time", "full time"),
        "part-time": ("part-time", "part time"),
    }
    theme_keywords = {
        "communication": ("communicat", "stakeholder", "non-technical", "present"),
        "business insights": ("business insight", "recommendation", "insight"),
        "leadership": ("leadership", "lead", "mentor", "operations"),
        "data cleaning": ("cleaning data", "clean data", "data cleaning"),
        "reporting": ("reporting", "summary", "summaries", "visual"),
        "technical rigor": ("model", "statistics", "uncertainty", "analysis"),
    }

    def __init__(self, user_id: uuid.UUID = DEMO_USER_ID) -> None:
        self.user_id = user_id

    def create_opportunity(
        self, session: Session, request: ApplicationOpportunityCreateRequest
    ) -> ApplicationOpportunityView:
        analysis = self.analyze_text(
            request.raw_text,
            title_override=request.title,
            organization_override=request.organization,
        )
        self._ensure_user(session)
        opportunity = ApplicationOpportunity(
            user_id=self.user_id,
            title=analysis.title,
            organization=analysis.organization,
            raw_text=request.raw_text,
            detected_role_type=analysis.role_type,
            detected_skills=analysis.skills,
            detected_keywords=analysis.keywords,
            detected_responsibilities=analysis.responsibilities,
            detected_questions=analysis.questions,
            status=ApplicationOpportunityStatus.ANALYZED.value,
        )
        session.add(opportunity)
        session.flush()
        for question_text in analysis.questions:
            session.add(self._question_record(opportunity.id, question_text))
        session.commit()
        self.recompute_matches(session, opportunity.id)
        return self.get_opportunity(session, opportunity.id)

    def list_opportunities(
        self, session: Session
    ) -> list[ApplicationOpportunityListItem]:
        opportunities = session.scalars(
            select(ApplicationOpportunity)
            .where(ApplicationOpportunity.user_id == self.user_id)
            .order_by(ApplicationOpportunity.updated_at.desc())
        ).all()
        match_counts = dict(
            session.execute(
                select(
                    ApplicationMemoryMatch.opportunity_id,
                    func.count(ApplicationMemoryMatch.id),
                )
                .where(ApplicationMemoryMatch.user_id == self.user_id)
                .group_by(ApplicationMemoryMatch.opportunity_id)
            ).all()
        )
        draft_counts = dict(
            session.execute(
                select(ApplicationDraft.opportunity_id, func.count(ApplicationDraft.id))
                .where(ApplicationDraft.user_id == self.user_id)
                .group_by(ApplicationDraft.opportunity_id)
            ).all()
        )
        return [
            ApplicationOpportunityListItem(
                id=opportunity.id,
                title=opportunity.title,
                organization=opportunity.organization,
                detected_role_type=opportunity.detected_role_type,
                detected_skills=opportunity.detected_skills,
                status=ApplicationOpportunityStatus(opportunity.status),
                match_count=match_counts.get(opportunity.id, 0),
                draft_count=draft_counts.get(opportunity.id, 0),
                created_at=opportunity.created_at,
                updated_at=opportunity.updated_at,
            )
            for opportunity in opportunities
        ]

    def get_opportunity(
        self, session: Session, opportunity_id: uuid.UUID
    ) -> ApplicationOpportunityView:
        opportunity = self._get_opportunity(session, opportunity_id)
        return self._opportunity_view(session, opportunity)

    def create_question(
        self, session: Session, request: ApplicationQuestionCreateRequest
    ) -> ApplicationQuestionView:
        opportunity = self._get_opportunity(session, request.opportunity_id)
        question = self._question_record(opportunity.id, request.question_text)
        session.add(question)
        session.commit()
        self.recompute_matches(session, opportunity.id, question.id)
        return self._question_view(question)

    def recompute_matches(
        self,
        session: Session,
        opportunity_id: uuid.UUID,
        question_id: uuid.UUID | None = None,
    ) -> ApplicationMatchResponse:
        opportunity = self._get_opportunity(session, opportunity_id)
        question = (
            self._get_question(session, question_id, opportunity.id)
            if question_id is not None
            else None
        )
        candidates = self._rank_candidates(session, opportunity, question)
        statement = delete(ApplicationMemoryMatch).where(
            ApplicationMemoryMatch.user_id == self.user_id,
            ApplicationMemoryMatch.opportunity_id == opportunity.id,
        )
        if question_id is None:
            statement = statement.where(ApplicationMemoryMatch.question_id.is_(None))
        else:
            statement = statement.where(
                ApplicationMemoryMatch.question_id == question_id
            )
        session.execute(statement)
        for candidate in candidates:
            session.add(
                ApplicationMemoryMatch(
                    user_id=self.user_id,
                    opportunity_id=opportunity.id,
                    question_id=question.id if question else None,
                    canonical_memory_id=candidate.memory.id,
                    match_score=Decimal(str(round(candidate.score, 3))),
                    match_reason=candidate.reason,
                    evidence_ids=candidate.memory.evidence_ids,
                    themes_matched=candidate.themes,
                )
            )
        session.commit()
        view = self.get_opportunity(session, opportunity.id)
        scoped = [
            match
            for match in view.matches
            if (
                match.question_id is None
                if question_id is None
                else match.question_id == question_id
            )
        ]
        return ApplicationMatchResponse(
            opportunity=view,
            matches=scoped,
            gaps=self._gaps(opportunity, view.matches),
        )

    def generate_draft(
        self,
        session: Session,
        opportunity_id: uuid.UUID,
        request: ApplicationDraftRequest,
    ) -> ApplicationDraftResponse:
        opportunity = self._get_opportunity(session, opportunity_id)
        question = (
            self._get_question(session, request.question_id, opportunity.id)
            if request.question_id is not None
            else None
        )
        matches = self._matches_for_scope(session, opportunity.id, request.question_id)
        if not matches:
            self.recompute_matches(session, opportunity.id, request.question_id)
            matches = self._matches_for_scope(
                session, opportunity.id, request.question_id
            )
        top_matches = matches[:5]
        draft_text = self._draft_text(
            opportunity,
            question,
            top_matches,
            request.draft_type,
            request.length,
        )
        evidence_ids = list(
            dict.fromkeys(
                evidence_id
                for match in top_matches
                for evidence_id in match.evidence_ids
            )
        )
        prompt = (
            question.question_text
            if question is not None
            else f"General application response for {opportunity.title}"
        )
        draft = ApplicationDraft(
            user_id=self.user_id,
            opportunity_id=opportunity.id,
            question_id=question.id if question else None,
            draft_type=request.draft_type.value,
            prompt=prompt,
            draft_text=draft_text,
            evidence_ids=evidence_ids,
            status=ApplicationDraftStatus.DRAFT.value,
            draft_metadata={
                "length": request.length.value,
                "uses_approved_memory_only": True,
                "matched_memory_ids": [
                    str(match.canonical_memory_id) for match in top_matches
                ],
                "gaps": self._gaps(opportunity, top_matches),
            },
        )
        session.add(draft)
        session.commit()
        draft_view = self._draft_view(draft)
        return ApplicationDraftResponse(
            draft=draft_view,
            matches_used=top_matches,
            evidence_used=evidence_ids,
        )

    def generate_question_draft(
        self,
        session: Session,
        question_id: uuid.UUID,
        request: ApplicationDraftRequest,
    ) -> ApplicationDraftResponse:
        question = self._get_question_any_opportunity(session, question_id)
        payload = request.model_copy(update={"question_id": question.id})
        return self.generate_draft(session, question.opportunity_id, payload)

    def update_draft(
        self,
        session: Session,
        draft_id: uuid.UUID,
        request: ApplicationDraftUpdateRequest,
    ) -> ApplicationDraftView:
        draft = self._get_draft(session, draft_id)
        if request.draft_text is not None:
            draft.draft_text = request.draft_text
            draft.status = ApplicationDraftStatus.EDITED.value
        if request.status is not None:
            draft.status = request.status.value
        session.commit()
        return self._draft_view(draft)

    def analyze_text(
        self,
        raw_text: str,
        *,
        title_override: str | None = None,
        organization_override: str | None = None,
    ) -> OpportunityAnalysis:
        normalized = raw_text.replace("\r\n", "\n").strip()
        lines = [
            line.strip(" -*\t") for line in normalized.splitlines() if line.strip()
        ]
        text_lower = normalized.casefold()
        title = title_override or self._detect_title(lines)
        organization = organization_override or self._detect_organization(lines)
        role_type = self._detect_role_type(text_lower)
        skills = self._detected_skills(text_lower)
        keywords = self._detected_keywords(text_lower, skills)
        responsibilities = self._responsibilities(lines)
        questions = self._questions(lines)
        return OpportunityAnalysis(
            title=title,
            organization=organization,
            role_type=role_type,
            skills=skills,
            keywords=keywords,
            responsibilities=responsibilities,
            questions=questions,
        )

    def _rank_candidates(
        self,
        session: Session,
        opportunity: ApplicationOpportunity,
        question: ApplicationQuestion | None,
    ) -> list[MatchCandidate]:
        memories = session.scalars(
            select(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.user_id == self.user_id
            )
        ).all()
        requirement_labels = self._requirement_labels(opportunity, question)
        requirement_terms = self._term_set(" ".join(requirement_labels))
        candidates: list[MatchCandidate] = []
        for memory in memories:
            memory_type = ReviewProposalType(memory.memory_type)
            memory_text = self._memory_text(memory)
            memory_terms = self._term_set(memory_text)
            themes = self._themes_matched(
                requirement_labels, requirement_terms, memory_terms, memory_text
            )
            if not themes:
                continue
            score = MEMORY_TYPE_WEIGHT.get(memory_type, 0.02)
            score += min(0.36, 0.07 * len(themes))
            score += float(memory.confidence) * 0.12
            score += 0.06 if memory.evidence_ids else 0
            score += self._question_type_boost(memory_type, question)
            score = min(score, 0.99)
            reason = self._match_reason(memory, themes, question)
            candidates.append(
                MatchCandidate(
                    memory=memory,
                    score=score,
                    reason=reason,
                    themes=themes,
                )
            )
        return sorted(candidates, key=lambda item: item.score, reverse=True)[:10]

    def _matches_for_scope(
        self,
        session: Session,
        opportunity_id: uuid.UUID,
        question_id: uuid.UUID | None,
    ) -> list[ApplicationMemoryMatchView]:
        statement = (
            select(ApplicationMemoryMatch)
            .where(
                ApplicationMemoryMatch.user_id == self.user_id,
                ApplicationMemoryMatch.opportunity_id == opportunity_id,
            )
            .order_by(ApplicationMemoryMatch.match_score.desc())
        )
        if question_id is None:
            statement = statement.where(ApplicationMemoryMatch.question_id.is_(None))
        else:
            statement = statement.where(
                ApplicationMemoryMatch.question_id == question_id
            )
        return [
            self._match_view(session, match)
            for match in session.scalars(statement).all()
        ]

    def _opportunity_view(
        self, session: Session, opportunity: ApplicationOpportunity
    ) -> ApplicationOpportunityView:
        questions = session.scalars(
            select(ApplicationQuestion)
            .where(ApplicationQuestion.opportunity_id == opportunity.id)
            .order_by(ApplicationQuestion.created_at)
        ).all()
        matches = session.scalars(
            select(ApplicationMemoryMatch)
            .where(ApplicationMemoryMatch.opportunity_id == opportunity.id)
            .order_by(ApplicationMemoryMatch.match_score.desc())
        ).all()
        drafts = session.scalars(
            select(ApplicationDraft)
            .where(ApplicationDraft.opportunity_id == opportunity.id)
            .order_by(ApplicationDraft.updated_at.desc())
        ).all()
        match_views = [self._match_view(session, match) for match in matches]
        return ApplicationOpportunityView(
            id=opportunity.id,
            title=opportunity.title,
            organization=opportunity.organization,
            raw_text=opportunity.raw_text,
            detected_role_type=opportunity.detected_role_type,
            detected_skills=opportunity.detected_skills,
            detected_keywords=opportunity.detected_keywords,
            detected_responsibilities=opportunity.detected_responsibilities,
            detected_questions=opportunity.detected_questions,
            status=ApplicationOpportunityStatus(opportunity.status),
            gaps=self._gaps(opportunity, match_views),
            questions=[self._question_view(question) for question in questions],
            matches=match_views,
            drafts=[self._draft_view(draft) for draft in drafts],
            approved_stories=self._approved_story_context(session),
            created_at=opportunity.created_at,
            updated_at=opportunity.updated_at,
        )

    def _question_record(
        self, opportunity_id: uuid.UUID, question_text: str
    ) -> ApplicationQuestion:
        question_type = self._question_type(question_text)
        themes = self._question_themes(question_text)
        return ApplicationQuestion(
            user_id=self.user_id,
            opportunity_id=opportunity_id,
            question_text=question_text,
            question_type=question_type.value,
            detected_intent=self._intent_for_question(question_type),
            required_themes=themes,
            status=ApplicationQuestionStatus.OPEN.value,
        )

    @staticmethod
    def _question_view(question: ApplicationQuestion) -> ApplicationQuestionView:
        return ApplicationQuestionView(
            id=question.id,
            opportunity_id=question.opportunity_id,
            question_text=question.question_text,
            question_type=ApplicationQuestionType(question.question_type),
            detected_intent=question.detected_intent,
            required_themes=question.required_themes,
            status=ApplicationQuestionStatus(question.status),
            created_at=question.created_at,
            updated_at=question.updated_at,
        )

    def _match_view(
        self, session: Session, match: ApplicationMemoryMatch
    ) -> ApplicationMemoryMatchView:
        memory = session.get(CanonicalMemoryRecord, match.canonical_memory_id)
        if memory is None or memory.user_id != self.user_id:
            raise ApplicationNotFoundError("Matched memory is unavailable.")
        return ApplicationMemoryMatchView(
            id=match.id,
            opportunity_id=match.opportunity_id,
            question_id=match.question_id,
            canonical_memory_id=match.canonical_memory_id,
            match_score=float(match.match_score),
            match_reason=match.match_reason,
            evidence_ids=match.evidence_ids,
            themes_matched=match.themes_matched,
            memory=self._memory_view(memory),
        )

    @staticmethod
    def _memory_view(memory: CanonicalMemoryRecord) -> CanonicalReviewMemory:
        return CanonicalReviewMemory(
            id=memory.id,
            memory_type=ReviewProposalType(memory.memory_type),
            title=memory.title,
            structured_fields=memory.structured_fields,
            evidence_ids=memory.evidence_ids,
            source_ids=memory.source_ids,
            confidence=float(memory.confidence),
            review_proposal_id=memory.review_proposal_id,
            updated_at=memory.updated_at,
        )

    @staticmethod
    def _draft_view(draft: ApplicationDraft) -> ApplicationDraftView:
        return ApplicationDraftView(
            id=draft.id,
            opportunity_id=draft.opportunity_id,
            question_id=draft.question_id,
            draft_type=ApplicationDraftType(draft.draft_type),
            prompt=draft.prompt,
            draft_text=draft.draft_text,
            evidence_ids=draft.evidence_ids,
            status=ApplicationDraftStatus(draft.status),
            draft_metadata=draft.draft_metadata,
            created_at=draft.created_at,
            updated_at=draft.updated_at,
        )

    def _approved_story_context(
        self, session: Session
    ) -> list[ApplicationStoryContext]:
        stories = session.scalars(
            select(Story)
            .where(
                Story.user_id == self.user_id,
                Story.status == StoryStatus.APPROVED.value,
                Story.deleted_at.is_(None),
            )
            .order_by(Story.updated_at.desc())
        ).all()
        if not stories:
            return []
        evidence_by_story: dict[uuid.UUID, list[str]] = {}
        rows = session.execute(
            select(StoryEvidence.story_id, StoryEvidence.evidence_item_id).where(
                StoryEvidence.user_id == self.user_id,
                StoryEvidence.story_id.in_([story.id for story in stories]),
            )
        ).all()
        for story_id, evidence_id in rows:
            evidence_by_story.setdefault(story_id, []).append(str(evidence_id))
        return [
            ApplicationStoryContext(
                id=story.id,
                title=story.title,
                summary=story.summary,
                evidence_ids=evidence_by_story.get(story.id, []),
                confidence=float(story.confidence),
            )
            for story in stories[:3]
        ]

    def _get_opportunity(
        self, session: Session, opportunity_id: uuid.UUID
    ) -> ApplicationOpportunity:
        opportunity = session.get(ApplicationOpportunity, opportunity_id)
        if opportunity is None or opportunity.user_id != self.user_id:
            raise ApplicationNotFoundError("Application opportunity not found.")
        return opportunity

    def _get_question(
        self, session: Session, question_id: uuid.UUID, opportunity_id: uuid.UUID
    ) -> ApplicationQuestion:
        question = session.get(ApplicationQuestion, question_id)
        if (
            question is None
            or question.user_id != self.user_id
            or question.opportunity_id != opportunity_id
        ):
            raise ApplicationNotFoundError("Application question not found.")
        return question

    def _get_question_any_opportunity(
        self, session: Session, question_id: uuid.UUID
    ) -> ApplicationQuestion:
        question = session.get(ApplicationQuestion, question_id)
        if question is None or question.user_id != self.user_id:
            raise ApplicationNotFoundError("Application question not found.")
        return question

    def _get_draft(self, session: Session, draft_id: uuid.UUID) -> ApplicationDraft:
        draft = session.get(ApplicationDraft, draft_id)
        if draft is None or draft.user_id != self.user_id:
            raise ApplicationNotFoundError("Application draft not found.")
        return draft

    def _ensure_user(self, session: Session) -> None:
        if session.get(User, self.user_id) is None:
            session.add(
                User(
                    id=self.user_id,
                    clerk_user_id=f"application-demo-{self.user_id}",
                    email=f"application-demo-{self.user_id}@example.invalid",
                    display_name="Application Demo User",
                )
            )
            session.flush()

    def _draft_text(
        self,
        opportunity: ApplicationOpportunity,
        question: ApplicationQuestion | None,
        matches: list[ApplicationMemoryMatchView],
        draft_type: ApplicationDraftType,
        length: ApplicationDraftLength,
    ) -> str:
        del draft_type
        titles = [match.memory.title for match in matches[:4]]
        skill_match = next(
            (
                match
                for match in matches
                if match.memory.memory_type is ReviewProposalType.SKILL_SET
            ),
            None,
        )
        project_match = next(
            (
                match
                for match in matches
                if match.memory.memory_type is ReviewProposalType.PROJECT
            ),
            None,
        )
        experience_match = next(
            (
                match
                for match in matches
                if match.memory.memory_type is ReviewProposalType.EXPERIENCE
            ),
            None,
        )
        education_match = next(
            (
                match
                for match in matches
                if match.memory.memory_type is ReviewProposalType.EDUCATION
            ),
            None,
        )
        skills = self._skills_from_memory(skill_match.memory if skill_match else None)
        target = (
            question.question_text
            if question is not None
            else f"this {opportunity.title} opportunity"
        )
        opening = (
            f"For {target}, I would highlight approved experience in "
            f"{', '.join(titles[:3])}."
            if titles
            else "I would keep this answer focused on approved Career Memory."
        )
        project_sentence = (
            f"A strong project example is {project_match.memory.title}, which shows "
            "hands-on analytical work and the ability to turn technical findings "
            "into a clear explanation."
            if project_match
            else ""
        )
        skill_sentence = (
            f"The relevant approved skills include {', '.join(skills[:6])}, which "
            "connect directly to the tools and analysis themes in the posting."
            if skills
            else ""
        )
        experience_sentence = (
            f"{experience_match.memory.title} adds communication evidence, especially "
            "around explaining technical ideas to other people."
            if experience_match
            else ""
        )
        education_sentence = (
            f"{education_match.memory.title} supports the academic preparation behind "
            "the analytics work."
            if education_match
            else ""
        )
        closing = (
            "I would frame the response around technical rigor, clear communication, "
            "and using data to create useful recommendations."
        )
        sentences = [
            sentence
            for sentence in (
                opening,
                project_sentence,
                skill_sentence,
                experience_sentence,
                education_sentence,
                closing,
            )
            if sentence
        ]
        if length is ApplicationDraftLength.SHORT:
            return " ".join(sentences[:3])
        if length is ApplicationDraftLength.LONG:
            midpoint = min(3, len(sentences))
            return (
                " ".join(sentences[:midpoint]) + "\n\n" + " ".join(sentences[midpoint:])
            )
        return " ".join(sentences[:5])

    @staticmethod
    def _skills_from_memory(memory: CanonicalMemoryRecord | None) -> list[str]:
        if memory is None:
            return []
        value = memory.structured_fields.get("skills")
        if isinstance(value, list):
            return [str(skill) for skill in value]
        name = memory.structured_fields.get("name")
        return [str(name)] if name else []

    def _gaps(
        self,
        opportunity: ApplicationOpportunity,
        matches: list[ApplicationMemoryMatchView],
    ) -> list[str]:
        matched_text = " ".join(
            [match.memory.title for match in matches]
            + [self._flatten(match.memory.structured_fields) for match in matches]
        ).casefold()
        gaps = [
            skill
            for skill in opportunity.detected_skills
            if self._normalize_label(skill) not in matched_text
        ]
        if "Dashboarding" in opportunity.detected_skills and not any(
            "dashboard" in match.casefold() for match in matched_text.split()
        ):
            gaps.append("Power BI/Tableau/dashboarding evidence")
        return list(dict.fromkeys(gaps))[:6]

    def _requirement_labels(
        self,
        opportunity: ApplicationOpportunity,
        question: ApplicationQuestion | None,
    ) -> list[str]:
        labels = (
            opportunity.detected_skills
            + opportunity.detected_keywords
            + opportunity.detected_responsibilities
        )
        if question is not None:
            labels += [question.question_text, *question.required_themes]
        return list(dict.fromkeys(labels))

    def _themes_matched(
        self,
        labels: list[str],
        requirement_terms: set[str],
        memory_terms: set[str],
        memory_text: str,
    ) -> list[str]:
        lower_memory = memory_text.casefold()
        themes = []
        for label in labels:
            normalized = self._normalize_label(label)
            label_terms = self._term_set(label)
            if normalized and normalized in lower_memory:
                themes.append(label)
            elif label_terms and label_terms.intersection(memory_terms):
                themes.append(label)
        if not themes:
            intersection = requirement_terms.intersection(memory_terms)
            themes = sorted(intersection, key=str.lower)[:3]
        return list(dict.fromkeys(themes))[:6]

    @staticmethod
    def _question_type_boost(
        memory_type: ReviewProposalType, question: ApplicationQuestion | None
    ) -> float:
        if question is None:
            return 0
        question_type = ApplicationQuestionType(question.question_type)
        if (
            question_type is ApplicationQuestionType.PROJECT_EXPLANATION
            and memory_type is ReviewProposalType.PROJECT
        ):
            return 0.16
        if (
            question_type is ApplicationQuestionType.TECHNICAL_SKILLS
            and memory_type is ReviewProposalType.SKILL_SET
        ):
            return 0.16
        if question_type in {
            ApplicationQuestionType.EXPERIENCE_EXAMPLE,
            ApplicationQuestionType.LEADERSHIP,
        } and memory_type in {
            ReviewProposalType.EXPERIENCE,
            ReviewProposalType.ACHIEVEMENT,
            ReviewProposalType.PROGRAM,
        }:
            return 0.12
        return 0

    @staticmethod
    def _match_reason(
        memory: CanonicalMemoryRecord,
        themes: list[str],
        question: ApplicationQuestion | None,
    ) -> str:
        scope = "this question" if question else "this opportunity"
        return (
            f"{memory.title} matches {scope} through "
            f"{', '.join(themes[:4])}; it is approved Career Memory with "
            f"{len(memory.evidence_ids)} evidence reference"
            f"{'' if len(memory.evidence_ids) == 1 else 's'}."
        )

    def _memory_text(self, memory: CanonicalMemoryRecord) -> str:
        return " ".join(
            [
                memory.title,
                memory.memory_type,
                self._flatten(memory.structured_fields),
            ]
        )

    @classmethod
    def _detected_skills(cls, text_lower: str) -> list[str]:
        found = []
        for needle, label in cls.skill_vocab.items():
            pattern = (
                r"(?<![a-z])r(?![a-z])"
                if needle == "r"
                else rf"\b{re.escape(needle)}\b"
            )
            if re.search(pattern, text_lower):
                found.append(label)
        return list(dict.fromkeys(found))

    @classmethod
    def _detected_keywords(cls, text_lower: str, skills: list[str]) -> list[str]:
        keywords = list(skills)
        for label, needles in cls.role_keywords.items():
            if any(needle in text_lower for needle in needles):
                keywords.append(label.title())
        for label, needles in cls.theme_keywords.items():
            if any(needle in text_lower for needle in needles):
                keywords.append(label.title())
        return list(dict.fromkeys(keywords))

    @classmethod
    def _question_themes(cls, question_text: str) -> list[str]:
        text_lower = question_text.casefold()
        return list(
            dict.fromkeys(
                cls._detected_skills(text_lower)
                + cls._detected_keywords(text_lower, [])
                + [cls._question_type(question_text).value.replace("_", " ").title()]
            )
        )

    @staticmethod
    def _responsibilities(lines: list[str]) -> list[str]:
        result = []
        for line in lines:
            lower = line.casefold()
            if any(
                marker in lower
                for marker in (
                    "responsibil",
                    "include",
                    "support",
                    "using",
                    "clean",
                    "analy",
                    "communicat",
                    "creating",
                    "translate",
                )
            ):
                result.append(line.rstrip("."))
        return result[:8]

    @staticmethod
    def _questions(lines: list[str]) -> list[str]:
        questions = []
        for index, line in enumerate(lines):
            lower = line.casefold().rstrip(":")
            if lower in {"application question", "question", "questions"}:
                if index + 1 < len(lines):
                    questions.append(lines[index + 1])
            elif line.endswith("?") or lower.startswith(
                ("tell us", "tell me", "describe", "why ", "what ", "how ")
            ):
                questions.append(line)
        return list(dict.fromkeys(questions))[:8]

    @staticmethod
    def _detect_title(lines: list[str]) -> str:
        for line in lines[:5]:
            if len(line) <= 90 and re.search(
                r"\b(intern|analyst|engineer|research|assistant|associate|manager)\b",
                line,
                re.IGNORECASE,
            ):
                return line.rstrip(":")
        return lines[0][:90] if lines else "Application opportunity"

    @staticmethod
    def _detect_organization(lines: list[str]) -> str | None:
        for line in lines[:8]:
            match = re.search(
                r"\b(?:company|organization|employer)\s*:\s*(.+)$",
                line,
                re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()
            match = re.search(r"\bat\s+([A-Z][A-Za-z0-9&., ]{2,60})", line)
            if match:
                return match.group(1).strip(" .")
        return None

    @classmethod
    def _detect_role_type(cls, text_lower: str) -> str | None:
        scores = Counter(
            label
            for label, needles in cls.role_keywords.items()
            for needle in needles
            if needle in text_lower
        )
        if not scores:
            return None
        return scores.most_common(1)[0][0].title()

    @classmethod
    def _question_type(cls, question_text: str) -> ApplicationQuestionType:
        text = question_text.casefold()
        if "why" in text and ("role" in text or "position" in text):
            return ApplicationQuestionType.WHY_THIS_ROLE
        if "why" in text and ("company" in text or "organization" in text):
            return ApplicationQuestionType.WHY_THIS_COMPANY
        if "tell" in text and "yourself" in text:
            return ApplicationQuestionType.TELL_ME_ABOUT_YOURSELF
        if "lead" in text:
            return ApplicationQuestionType.LEADERSHIP
        if "skill" in text or "technical" in text:
            return ApplicationQuestionType.TECHNICAL_SKILLS
        if "project" in text:
            return ApplicationQuestionType.PROJECT_EXPLANATION
        if "strength" in text:
            return ApplicationQuestionType.STRENGTHS
        if "experience" in text or "prepared" in text or "example" in text:
            return ApplicationQuestionType.EXPERIENCE_EXAMPLE
        if "cover letter" in text:
            return ApplicationQuestionType.GENERAL_COVER_LETTER
        return ApplicationQuestionType.UNKNOWN

    @staticmethod
    def _intent_for_question(question_type: ApplicationQuestionType) -> str:
        intents = {
            ApplicationQuestionType.WHY_THIS_ROLE: "Show fit for the role.",
            ApplicationQuestionType.WHY_THIS_COMPANY: (
                "Connect motivation to the organization."
            ),
            ApplicationQuestionType.TELL_ME_ABOUT_YOURSELF: (
                "Summarize the user's relevant background."
            ),
            ApplicationQuestionType.EXPERIENCE_EXAMPLE: (
                "Choose a concrete approved experience."
            ),
            ApplicationQuestionType.LEADERSHIP: (
                "Highlight leadership and collaboration evidence."
            ),
            ApplicationQuestionType.TECHNICAL_SKILLS: (
                "Show tool and technical skill fit."
            ),
            ApplicationQuestionType.PROJECT_EXPLANATION: (
                "Explain an approved project clearly."
            ),
            ApplicationQuestionType.STRENGTHS: "Frame strengths using evidence.",
            ApplicationQuestionType.GENERAL_COVER_LETTER: (
                "Draft a broad application narrative."
            ),
            ApplicationQuestionType.UNKNOWN: (
                "Answer using the most relevant approved memories."
            ),
        }
        return intents[question_type]

    @staticmethod
    def _term_set(value: str) -> set[str]:
        stop = {
            "and",
            "the",
            "for",
            "with",
            "this",
            "that",
            "into",
            "using",
            "include",
            "includes",
            "experience",
            "opportunity",
        }
        return {
            token
            for token in re.findall(r"[a-z][a-z0-9+#-]{1,}", value.casefold())
            if token not in stop
        }

    @staticmethod
    def _normalize_label(value: str) -> str:
        return re.sub(r"[^a-z0-9+#]+", " ", value.casefold()).strip()

    @classmethod
    def _flatten(cls, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(cls._flatten(item) for item in value.values())
        if isinstance(value, list):
            return " ".join(cls._flatten(item) for item in value)
        return str(value or "")

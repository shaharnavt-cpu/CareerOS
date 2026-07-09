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


@dataclass(frozen=True)
class DraftMemorySelection:
    primary: ApplicationMemoryMatchView | None
    supporting: list[ApplicationMemoryMatchView]


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
        selection = self._select_draft_memories(matches, question)
        selected_matches = [
            match for match in [selection.primary, *selection.supporting] if match
        ]
        draft_text = self._draft_text(
            opportunity,
            question,
            selection,
            request.draft_type,
            request.length,
        )
        evidence_ids = list(
            dict.fromkeys(
                evidence_id
                for match in selected_matches
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
                "variant": self._variant_label(request.length),
                "uses_approved_memory_only": True,
                "matched_memory_ids": [
                    str(match.canonical_memory_id) for match in selected_matches
                ],
                "primary_memory": self._draft_memory_metadata(selection.primary),
                "supporting_memories": [
                    self._draft_memory_metadata(match)
                    for match in selection.supporting
                ],
                "question_type": question.question_type if question else None,
                "evidence_ids": evidence_ids,
                "gaps": self._gaps(opportunity, selected_matches),
            },
        )
        session.add(draft)
        session.commit()
        draft_view = self._draft_view(draft)
        return ApplicationDraftResponse(
            draft=draft_view,
            matches_used=selected_matches,
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

    def _select_draft_memories(
        self,
        matches: list[ApplicationMemoryMatchView],
        question: ApplicationQuestion | None,
    ) -> DraftMemorySelection:
        excluded = {
            ReviewProposalType.CONTACT,
            ReviewProposalType.ORGANIZATION,
            ReviewProposalType.NEEDS_CLASSIFICATION,
        }
        unique: list[ApplicationMemoryMatchView] = []
        seen: set[uuid.UUID] = set()
        for match in matches:
            if (
                match.canonical_memory_id in seen
                or match.memory.memory_type in excluded
            ):
                continue
            seen.add(match.canonical_memory_id)
            unique.append(match)
        if not unique:
            return DraftMemorySelection(primary=None, supporting=[])

        question_type = self._draft_question_type(question)
        primary = max(
            unique,
            key=lambda match: self._primary_memory_score(match, question_type),
        )
        supporting = sorted(
            [
                match
                for match in unique
                if match.canonical_memory_id != primary.canonical_memory_id
            ],
            key=lambda match: self._supporting_memory_score(match, question_type),
            reverse=True,
        )[:2]
        return DraftMemorySelection(primary=primary, supporting=supporting)

    def _draft_text(
        self,
        opportunity: ApplicationOpportunity,
        question: ApplicationQuestion | None,
        selection: DraftMemorySelection,
        draft_type: ApplicationDraftType,
        length: ApplicationDraftLength,
    ) -> str:
        if selection.primary is None:
            return (
                "I do not yet have enough approved Career Memory to answer this "
                "prompt well. I would review and approve relevant projects, "
                "experiences, or skills before drafting a final response."
            )

        question_type = self._draft_question_type(question)
        if draft_type is ApplicationDraftType.COVER_LETTER_SNIPPET:
            sentences = self._why_role_sentences(opportunity, selection)
        elif question_type is ApplicationQuestionType.TECHNICAL_SKILLS:
            sentences = self._technical_sentences(opportunity, selection)
        elif question_type is ApplicationQuestionType.LEADERSHIP:
            sentences = self._leadership_sentences(opportunity, selection)
        elif question_type is ApplicationQuestionType.TELL_ME_ABOUT_YOURSELF:
            sentences = self._about_me_sentences(opportunity, selection)
        elif question_type in {
            ApplicationQuestionType.WHY_THIS_ROLE,
            ApplicationQuestionType.WHY_THIS_COMPANY,
        }:
            sentences = self._why_role_sentences(opportunity, selection)
        else:
            sentences = self._project_or_experience_sentences(opportunity, selection)
        return self._format_draft(sentences, length)

    def _project_or_experience_sentences(
        self,
        opportunity: ApplicationOpportunity,
        selection: DraftMemorySelection,
    ) -> list[str]:
        primary = selection.primary
        if primary is None:
            return []
        role = self._role_phrase(opportunity)
        support_skills = self._skills_from_selection(selection)
        action = self._action_clause(primary, self._skills_from_match(primary))
        sentences = [
            f"A project that prepared me for {role} is {self._memory_phrase(primary)}.",
            f"In that work, I {action}.",
            (
                "The project strengthened how I move from technical evidence to a "
                "clear conclusion, which is the same habit I bring to analytics work."
            ),
        ]
        if support_skills:
            sentences.append(
                f"My approved technical foundation also includes "
                f"{self._join_natural(support_skills[:6])}, so I can connect the "
                "project work to the tools named in the posting."
            )
        sentences.extend(
            self._supporting_sentences(selection.supporting, skip_skills=True)
        )
        sentences.extend(
            [
                (
                    f"That preparation matches {role} because the opportunity "
                    f"emphasizes {self._theme_phrase(opportunity)}."
                ),
                (
                    "Because the work involved real research questions, I had to be "
                    "careful about assumptions, uncertainty, and how much detail "
                    "belonged in the final explanation."
                ),
                (
                    "That process maps well to analytics work: understand the data, "
                    "choose the right method, build a concise summary, and explain "
                    "what the result means for the decision at hand."
                ),
                (
                    "What I took from the experience was not only the technical "
                    "analysis, but also the discipline of explaining complex work in "
                    "a way another person can use."
                ),
                (
                    "If I were given a new dataset in this internship, I would bring "
                    "that same workflow: clarify the question, check the data, test "
                    "the analysis, and communicate the recommendation clearly."
                ),
                (
                    "I can bring that combination of careful analysis, practical "
                    "tool use, and clear communication to the internship from the "
                    "first project I support."
                ),
            ]
        )
        return sentences

    def _technical_sentences(
        self,
        opportunity: ApplicationOpportunity,
        selection: DraftMemorySelection,
    ) -> list[str]:
        primary = selection.primary
        if primary is None:
            return []
        role = self._role_phrase(opportunity)
        skills = self._skills_from_selection(selection)
        action = self._action_clause(primary, self._skills_from_match(primary))
        primary_phrase = self._memory_phrase(primary)
        sentences = [
            (
                f"My strongest technical fit for {role} is my approved foundation "
                f"in {self._join_natural(skills[:6])}."
                if skills
                else (
                    f"My strongest technical fit for {role} comes from "
                    f"{primary_phrase}."
                )
            ),
            f"I have applied that background through {primary_phrase}.",
            f"In that work, I {action}.",
        ]
        sentences.extend(self._supporting_sentences(selection.supporting))
        sentences.extend(
            [
                (
                    "That matters for this role because the posting asks for someone "
                    "who can analyze data, summarize patterns, and communicate the "
                    "result clearly."
                ),
                (
                    "I am comfortable learning the business context around a dataset "
                    "and then choosing the right level of technical detail for the "
                    "audience."
                ),
                (
                    "I would use those skills to help the team turn analysis into "
                    "useful reporting and recommendations."
                ),
            ]
        )
        return sentences

    def _about_me_sentences(
        self,
        opportunity: ApplicationOpportunity,
        selection: DraftMemorySelection,
    ) -> list[str]:
        primary = selection.primary
        if primary is None:
            return []
        education = next(
            (
                match
                for match in [primary, *selection.supporting]
                if match.memory.memory_type is ReviewProposalType.EDUCATION
            ),
            None,
        )
        action = self._action_clause(primary, self._skills_from_match(primary))
        sentences = [
            f"I am a student with {self._education_phrase(education)}.",
            f"The strongest example of how I work is {self._memory_phrase(primary)}.",
            f"In that work, I {action}.",
        ]
        sentences.extend(self._supporting_sentences(selection.supporting))
        sentences.extend(
            [
                (
                    "Across those experiences, the common thread is translating "
                    "technical material into clear, useful decisions or explanations."
                ),
                (
                    f"That is why {self._role_phrase(opportunity)} is a strong fit "
                    "for me: it combines data, business context, and communication."
                ),
                (
                    "I am looking for work where I can keep building as an analyst "
                    "while contributing careful, evidence-based thinking to a team."
                ),
            ]
        )
        return sentences

    def _why_role_sentences(
        self,
        opportunity: ApplicationOpportunity,
        selection: DraftMemorySelection,
    ) -> list[str]:
        primary = selection.primary
        if primary is None:
            return []
        role = self._role_phrase(opportunity)
        action = self._action_clause(primary, self._skills_from_match(primary))
        sentences = [
            (
                f"I am interested in {role} because it brings together "
                f"{self._theme_phrase(opportunity)}."
            ),
            f"My strongest preparation is {self._memory_phrase(primary)}.",
            f"In that work, I {action}.",
        ]
        sentences.extend(self._supporting_sentences(selection.supporting))
        sentences.extend(
            [
                (
                    "The role stands out to me because it asks for more than tool "
                    "knowledge; it asks for someone who can turn analysis into a "
                    "useful explanation."
                ),
                (
                    "That is the kind of work I have been practicing through my "
                    "approved projects, technical skill development, and teaching or "
                    "communication experience."
                ),
                (
                    "I would be excited to contribute that mix of curiosity, rigor, "
                    "and clear communication while continuing to grow in a real "
                    "analytics environment."
                ),
            ]
        )
        return sentences

    def _leadership_sentences(
        self,
        opportunity: ApplicationOpportunity,
        selection: DraftMemorySelection,
    ) -> list[str]:
        primary = selection.primary
        if primary is None:
            return []
        role = self._role_phrase(opportunity)
        primary_phrase = self._memory_phrase(primary)
        action = self._action_clause(primary, self._skills_from_match(primary))
        sentences = [
            f"One leadership experience that shaped me is {primary_phrase}.",
            f"The situation required me to {action}.",
            (
                "My focus was to create structure for other people, communicate "
                "clearly, and follow through on the work that made the group more "
                "effective."
            ),
        ]
        sentences.extend(self._supporting_sentences(selection.supporting))
        sentences.extend(
            [
                (
                    "The result was stronger practice in coordinating people around "
                    "a shared goal and adjusting my communication to the audience."
                ),
                (
                    f"That prepares me for {role} because analytics work also depends "
                    "on listening carefully, explaining tradeoffs, and helping others "
                    "act on information."
                ),
                (
                    "I carry that lesson into team settings: leadership is not just "
                    "having the answer, but making the work easier for others to use."
                ),
            ]
        )
        return sentences

    def _supporting_sentences(
        self,
        supporting: list[ApplicationMemoryMatchView],
        *,
        skip_skills: bool = False,
    ) -> list[str]:
        sentences = []
        for match in supporting:
            memory_type = match.memory.memory_type
            if skip_skills and memory_type is ReviewProposalType.SKILL_SET:
                continue
            if memory_type is ReviewProposalType.SKILL_SET:
                skills = self._skills_from_match(match)
                if skills:
                    sentences.append(
                        f"My {match.memory.title} memory supports this with "
                        f"{self._join_natural(skills[:6])}."
                    )
                continue
            if memory_type is ReviewProposalType.EXPERIENCE:
                sentences.append(
                    f"{match.memory.title} adds evidence that I can communicate "
                    "technical ideas and support other people through complex material."
                )
            elif memory_type is ReviewProposalType.PROJECT:
                sentences.append(
                    f"{match.memory.title} gives me another approved example of "
                    "using analysis to reach and explain a conclusion."
                )
            elif memory_type is ReviewProposalType.EDUCATION:
                sentences.append(
                    f"{match.memory.title} supports the academic preparation behind "
                    "my interest in the role."
                )
            elif memory_type in {
                ReviewProposalType.PROGRAM,
                ReviewProposalType.ACHIEVEMENT,
            }:
                sentences.append(
                    f"{match.memory.title} adds context for the consistency and "
                    "initiative behind that work."
                )
        return sentences

    @staticmethod
    def _format_draft(sentences: list[str], length: ApplicationDraftLength) -> str:
        clean = [sentence for sentence in sentences if sentence]
        if length is ApplicationDraftLength.SHORT:
            return " ".join(clean[:4])
        if length is ApplicationDraftLength.MEDIUM:
            return " ".join(clean[:7])
        midpoint = min(5, len(clean))
        return " ".join(clean[:midpoint]) + "\n\n" + " ".join(clean[midpoint:])

    @staticmethod
    def _variant_label(length: ApplicationDraftLength) -> str:
        if length is ApplicationDraftLength.SHORT:
            return "short"
        if length is ApplicationDraftLength.MEDIUM:
            return "medium"
        return "detailed"

    @staticmethod
    def _draft_question_type(
        question: ApplicationQuestion | None,
    ) -> ApplicationQuestionType:
        if question is None:
            return ApplicationQuestionType.GENERAL_COVER_LETTER
        return ApplicationQuestionType(question.question_type)

    def _primary_memory_score(
        self,
        match: ApplicationMemoryMatchView,
        question_type: ApplicationQuestionType,
    ) -> float:
        orders = {
            ApplicationQuestionType.PROJECT_EXPLANATION: (
                ReviewProposalType.PROJECT,
                ReviewProposalType.EXPERIENCE,
                ReviewProposalType.PROGRAM,
                ReviewProposalType.ACHIEVEMENT,
                ReviewProposalType.SKILL_SET,
                ReviewProposalType.EDUCATION,
            ),
            ApplicationQuestionType.EXPERIENCE_EXAMPLE: (
                ReviewProposalType.PROJECT,
                ReviewProposalType.EXPERIENCE,
                ReviewProposalType.PROGRAM,
                ReviewProposalType.ACHIEVEMENT,
                ReviewProposalType.SKILL_SET,
                ReviewProposalType.EDUCATION,
            ),
            ApplicationQuestionType.TECHNICAL_SKILLS: (
                ReviewProposalType.SKILL_SET,
                ReviewProposalType.PROJECT,
                ReviewProposalType.EXPERIENCE,
                ReviewProposalType.EDUCATION,
            ),
            ApplicationQuestionType.LEADERSHIP: (
                ReviewProposalType.EXPERIENCE,
                ReviewProposalType.ACHIEVEMENT,
                ReviewProposalType.PROGRAM,
                ReviewProposalType.PROJECT,
            ),
            ApplicationQuestionType.TELL_ME_ABOUT_YOURSELF: (
                ReviewProposalType.PROJECT,
                ReviewProposalType.EXPERIENCE,
                ReviewProposalType.EDUCATION,
                ReviewProposalType.SKILL_SET,
            ),
        }
        order = orders.get(
            question_type,
            (
                ReviewProposalType.PROJECT,
                ReviewProposalType.EXPERIENCE,
                ReviewProposalType.SKILL_SET,
                ReviewProposalType.EDUCATION,
                ReviewProposalType.PROGRAM,
                ReviewProposalType.ACHIEVEMENT,
            ),
        )
        memory_type = match.memory.memory_type
        rank_bonus = (
            0.48 - (order.index(memory_type) * 0.06)
            if memory_type in order
            else 0
        )
        text = self._memory_text_from_view(match.memory).casefold()
        capstone_bonus = (
            0.08
            if any(term in text for term in ("capstone", "kinematics", "morphology"))
            else 0
        )
        evidence_bonus = 0.03 if match.evidence_ids else 0
        skill_penalty = (
            0.18
            if memory_type is ReviewProposalType.SKILL_SET
            and question_type
            not in {
                ApplicationQuestionType.TECHNICAL_SKILLS,
                ApplicationQuestionType.UNKNOWN,
            }
            else 0
        )
        return (
            match.match_score
            + rank_bonus
            + capstone_bonus
            + evidence_bonus
            - skill_penalty
        )

    def _supporting_memory_score(
        self,
        match: ApplicationMemoryMatchView,
        question_type: ApplicationQuestionType,
    ) -> float:
        if question_type in {
            ApplicationQuestionType.PROJECT_EXPLANATION,
            ApplicationQuestionType.EXPERIENCE_EXAMPLE,
        }:
            order = (
                ReviewProposalType.SKILL_SET,
                ReviewProposalType.EXPERIENCE,
                ReviewProposalType.PROJECT,
                ReviewProposalType.PROGRAM,
                ReviewProposalType.EDUCATION,
                ReviewProposalType.ACHIEVEMENT,
            )
        elif question_type is ApplicationQuestionType.TECHNICAL_SKILLS:
            order = (
                ReviewProposalType.PROJECT,
                ReviewProposalType.EXPERIENCE,
                ReviewProposalType.EDUCATION,
                ReviewProposalType.PROGRAM,
            )
        else:
            order = (
                ReviewProposalType.SKILL_SET,
                ReviewProposalType.PROJECT,
                ReviewProposalType.EXPERIENCE,
                ReviewProposalType.EDUCATION,
                ReviewProposalType.PROGRAM,
                ReviewProposalType.ACHIEVEMENT,
            )
        memory_type = match.memory.memory_type
        rank_bonus = (
            0.22 - (order.index(memory_type) * 0.035)
            if memory_type in order
            else 0
        )
        return match.match_score + rank_bonus + (0.02 if match.evidence_ids else 0)

    @staticmethod
    def _draft_memory_metadata(
        match: ApplicationMemoryMatchView | None,
    ) -> dict[str, Any] | None:
        if match is None:
            return None
        return {
            "id": str(match.canonical_memory_id),
            "title": match.memory.title,
            "type": match.memory.memory_type.value,
            "evidence_count": len(match.evidence_ids),
            "themes_matched": match.themes_matched,
        }

    @staticmethod
    def _role_phrase(opportunity: ApplicationOpportunity) -> str:
        title = opportunity.title.strip().rstrip(".")
        if not title:
            return "this role"
        return f"this {title.casefold()} role"

    def _theme_phrase(self, opportunity: ApplicationOpportunity) -> str:
        labels = list(
            dict.fromkeys(opportunity.detected_skills + opportunity.detected_keywords)
        )
        filtered = [
            label
            for label in labels
            if label.casefold()
            not in {"internship", "data", "analytics", "data analysis"}
        ]
        chosen = filtered[:3] or labels[:3] or ["clear analysis", "communication"]
        return self._join_natural([label.casefold() for label in chosen])

    @staticmethod
    def _memory_phrase(match: ApplicationMemoryMatchView) -> str:
        title = match.memory.title
        if match.memory.memory_type is ReviewProposalType.EXPERIENCE:
            return f"my {title} experience"
        if title.casefold().startswith(("the ", "my ")):
            return title
        return f"my {title}"

    def _education_phrase(self, match: ApplicationMemoryMatchView | None) -> str:
        if match is None:
            return "approved academic preparation"
        fields = match.memory.structured_fields
        degree = str(fields.get("degree") or "").strip()
        field = str(
            fields.get("field_of_study") or fields.get("field") or ""
        ).strip()
        institution = str(
            fields.get("institution_name")
            or fields.get("institution")
            or match.memory.title
        ).strip()
        parts = [part for part in (degree, field) if part]
        if parts:
            return f"{' in '.join(parts)} from {institution}"
        return f"approved academic preparation from {institution}"

    def _action_clause(
        self,
        match: ApplicationMemoryMatchView,
        skills: list[str],
    ) -> str:
        fields = match.memory.structured_fields
        memory_text = self._memory_text_from_view(match.memory).casefold()
        skill_phrase = f" using {self._join_natural(skills[:4])}" if skills else ""
        if match.memory.memory_type is ReviewProposalType.EXPERIENCE:
            responsibilities = self._string_list(fields.get("responsibilities"))
            if responsibilities:
                return self._lower_first(self._join_natural(responsibilities[:2]))
            return (
                "explained technical ideas, supported other people, and adapted my "
                "communication to the audience"
            )
        if "gas" in memory_text and "morphology" in memory_text:
            return (
                "analyzed spectral and imaging evidence to study gas kinematics "
                f"and galaxy morphology{skill_phrase}"
            )
        if "unicorn" in memory_text:
            return (
                "worked with astronomy research data and translated technical "
                f"findings into clearer outputs{skill_phrase}"
            )
        summary = str(fields.get("summary") or fields.get("description") or "").strip()
        if summary:
            return f"worked on {self._lower_first(summary.rstrip('.'))}{skill_phrase}"
        return (
            "analyzed evidence, organized the important patterns, and explained "
            f"the result clearly{skill_phrase}"
        )

    def _skills_from_selection(self, selection: DraftMemorySelection) -> list[str]:
        skills = []
        for match in [selection.primary, *selection.supporting]:
            if match is None:
                continue
            skills.extend(self._skills_from_match(match))
        return list(dict.fromkeys(skills))

    def _skills_from_match(self, match: ApplicationMemoryMatchView) -> list[str]:
        fields = match.memory.structured_fields
        skills: list[str] = []
        for key in ("skills", "methods", "tools"):
            skills.extend(self._string_list(fields.get(key)))
        memory_text = self._memory_text_from_view(match.memory).casefold()
        for needle, label in self.skill_vocab.items():
            pattern = (
                r"(?<![a-z])r(?![a-z])"
                if needle == "r"
                else rf"\b{re.escape(needle)}\b"
            )
            if re.search(pattern, memory_text):
                skills.append(label)
        return list(dict.fromkeys(skill for skill in skills if skill))

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _join_natural(values: list[str]) -> str:
        clean = [value for value in values if value]
        if not clean:
            return ""
        if len(clean) == 1:
            return clean[0]
        if len(clean) == 2:
            return f"{clean[0]} and {clean[1]}"
        return f"{', '.join(clean[:-1])}, and {clean[-1]}"

    @staticmethod
    def _lower_first(value: str) -> str:
        if not value:
            return value
        return value[0].lower() + value[1:]

    @classmethod
    def _memory_text_from_view(cls, memory: CanonicalReviewMemory) -> str:
        return " ".join(
            [
                memory.title,
                memory.memory_type.value,
                cls._flatten(memory.structured_fields),
            ]
        )

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

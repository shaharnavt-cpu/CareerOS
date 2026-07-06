"""Tenant-safe persistence and Career Memory retrieval for stories."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Achievement,
    Education,
    EvidenceItem,
    EvidenceLink,
    Experience,
    Program,
    Project,
    Skill,
    SkillLink,
    Story,
    StoryChapter,
    StoryEvidence,
    StoryMembership,
    User,
)
from app.schemas.knowledge import EntityType
from app.schemas.stories import (
    StoryChapterView,
    StoryCreateRequest,
    StoryEvidenceView,
    StoryMembershipView,
    StoryStatus,
    StoryView,
)
from app.services.story_clustering import RelatedStoryEntity, StorySignal


class StoryNotFoundError(LookupError):
    """Raised when a story is unavailable to the current tenant."""


class StoryValidationError(ValueError):
    """Raised when a story would cross ownership or lifecycle boundaries."""


class StoryRepository:
    """Store stories while keeping polymorphic membership validation centralized."""

    entity_models = {
        EntityType.PROGRAM: Program,
        EntityType.EDUCATION: Education,
        EntityType.EXPERIENCE: Experience,
        EntityType.PROJECT: Project,
        EntityType.ACHIEVEMENT: Achievement,
        EntityType.SKILL: Skill,
    }
    verification_confidence = {
        "OFFICIAL": 1.0,
        "EXTERNALLY_VERIFIED": 0.9,
        "SELF_VERIFIED": 0.7,
        "UNVERIFIED": 0.5,
    }
    stop_words = {
        "and",
        "for",
        "from",
        "that",
        "the",
        "this",
        "with",
        "into",
        "using",
        "through",
        "work",
        "role",
        "team",
    }

    def list_records(
        self,
        session: Session,
        user_id: uuid.UUID,
        *,
        include_archived: bool = False,
    ) -> list[Story]:
        statement = self._story_query().where(
            Story.user_id == user_id, Story.deleted_at.is_(None)
        )
        if not include_archived:
            statement = statement.where(Story.status != StoryStatus.ARCHIVED.value)
        return list(
            session.scalars(statement.order_by(Story.updated_at.desc())).unique()
        )

    def get_record(
        self, session: Session, user_id: uuid.UUID, story_id: uuid.UUID
    ) -> Story:
        story = session.scalar(
            self._story_query().where(
                Story.id == story_id,
                Story.user_id == user_id,
                Story.deleted_at.is_(None),
            )
        )
        if story is None:
            raise StoryNotFoundError("Story not found for the current user.")
        return story

    def create_record(
        self,
        session: Session,
        user_id: uuid.UUID,
        request: StoryCreateRequest,
        *,
        status: StoryStatus = StoryStatus.PROPOSED,
    ) -> Story:
        self._ensure_user(session, user_id)
        story = Story(
            user_id=user_id,
            title=request.title,
            summary=request.summary,
            primary_goal=request.primary_goal,
            transformation=request.transformation,
            confidence=Decimal(str(request.confidence)),
            status=status.value,
        )
        session.add(story)
        session.flush()

        chapters: dict[int, StoryChapter] = {}
        for chapter_input in sorted(request.chapters, key=lambda item: item.position):
            if chapter_input.position in chapters:
                raise StoryValidationError("Chapter positions must be unique.")
            chapter = StoryChapter(
                user_id=user_id,
                story_id=story.id,
                **chapter_input.model_dump(),
            )
            session.add(chapter)
            session.flush()
            chapters[chapter.position] = chapter

        seen_memberships: set[tuple[EntityType, uuid.UUID]] = set()
        for membership_input in request.memberships:
            key = (membership_input.entity_type, membership_input.entity_id)
            if key in seen_memberships:
                continue
            seen_memberships.add(key)
            self._validate_entity_owner(
                session,
                user_id,
                membership_input.entity_type,
                membership_input.entity_id,
            )
            chapter = (
                chapters.get(membership_input.chapter_position)
                if membership_input.chapter_position is not None
                else None
            )
            if membership_input.chapter_position is not None and chapter is None:
                raise StoryValidationError("Membership references an unknown chapter.")
            session.add(
                StoryMembership(
                    user_id=user_id,
                    story_id=story.id,
                    chapter_id=chapter.id if chapter else None,
                    entity_type=membership_input.entity_type.value,
                    entity_id=membership_input.entity_id,
                    role=membership_input.role,
                    rationale=membership_input.rationale,
                    confidence=Decimal(str(membership_input.confidence)),
                )
            )

        for evidence_id in dict.fromkeys(request.evidence_ids):
            evidence = session.scalar(
                select(EvidenceItem).where(
                    EvidenceItem.id == evidence_id,
                    EvidenceItem.user_id == user_id,
                    EvidenceItem.deleted_at.is_(None),
                )
            )
            if evidence is None:
                raise StoryValidationError(
                    "Story evidence must exist and belong to the current user."
                )
            session.add(
                StoryEvidence(
                    user_id=user_id,
                    story_id=story.id,
                    evidence_item_id=evidence.id,
                    relationship_type="SUPPORTS",
                    excerpt=evidence.description,
                )
            )
        session.flush()
        return self.get_record(session, user_id, story.id)

    def to_view(self, session: Session, story: Story) -> StoryView:
        memberships = [
            self._membership_view(session, story.user_id, membership)
            for membership in story.memberships
        ]
        return StoryView(
            id=story.id,
            title=story.title,
            summary=story.summary,
            primary_goal=story.primary_goal,
            transformation=story.transformation,
            confidence=float(story.confidence),
            status=StoryStatus(story.status),
            chapters=[
                StoryChapterView(
                    id=chapter.id,
                    title=chapter.title,
                    summary=chapter.summary,
                    position=chapter.position,
                    start_date=chapter.start_date,
                    end_date=chapter.end_date,
                )
                for chapter in story.chapters
                if chapter.deleted_at is None
            ],
            memberships=memberships,
            evidence=[
                StoryEvidenceView(
                    id=link.id,
                    evidence_item_id=link.evidence_item_id,
                    title=link.evidence_item.title,
                    evidence_type=link.evidence_item.evidence_type,
                    verification_status=link.evidence_item.verification_status,
                    source_url=link.evidence_item.source_url,
                    excerpt=link.excerpt or link.evidence_item.description,
                    relationship_type=link.relationship_type,
                )
                for link in story.evidence_links
                if link.evidence_item.deleted_at is None
            ],
            created_at=story.created_at,
            updated_at=story.updated_at,
            approved_at=story.approved_at,
        )

    def load_discovery_signals(
        self, session: Session, user_id: uuid.UUID
    ) -> list[StorySignal]:
        experiences = list(
            session.scalars(
                select(Experience).where(
                    Experience.user_id == user_id,
                    Experience.deleted_at.is_(None),
                )
            )
        )
        if not experiences:
            return []

        experience_ids = [item.id for item in experiences]
        projects = list(
            session.scalars(
                select(Project).where(
                    Project.user_id == user_id,
                    Project.experience_id.in_(experience_ids),
                    Project.deleted_at.is_(None),
                )
            )
        )
        project_ids = [item.id for item in projects]
        achievements = list(
            session.scalars(
                select(Achievement).where(
                    Achievement.user_id == user_id,
                    Achievement.deleted_at.is_(None),
                    (
                        Achievement.experience_id.in_(experience_ids)
                        | Achievement.project_id.in_(project_ids)
                    ),
                )
            )
        )
        entity_ids = experience_ids + project_ids + [item.id for item in achievements]
        skill_links = list(
            session.scalars(
                select(SkillLink).where(
                    SkillLink.user_id == user_id,
                    SkillLink.entity_id.in_(entity_ids),
                )
            )
        )
        skill_ids = [link.skill_id for link in skill_links]
        skills = {
            item.id: item
            for item in session.scalars(
                select(Skill).where(
                    Skill.user_id == user_id,
                    Skill.id.in_(skill_ids),
                    Skill.deleted_at.is_(None),
                )
            )
        }
        evidence_links = list(
            session.scalars(
                select(EvidenceLink).where(
                    EvidenceLink.user_id == user_id,
                    EvidenceLink.entity_id.in_(entity_ids + skill_ids),
                )
            )
        )
        evidence_ids = [link.evidence_item_id for link in evidence_links]
        evidence_items = {
            item.id: item
            for item in session.scalars(
                select(EvidenceItem).where(
                    EvidenceItem.user_id == user_id,
                    EvidenceItem.id.in_(evidence_ids),
                    EvidenceItem.deleted_at.is_(None),
                )
            )
        }

        projects_by_experience: dict[uuid.UUID, list[Project]] = defaultdict(list)
        for project in projects:
            if project.experience_id:
                projects_by_experience[project.experience_id].append(project)
        achievements_by_experience: dict[uuid.UUID, list[Achievement]] = defaultdict(
            list
        )
        for achievement in achievements:
            if achievement.experience_id:
                achievements_by_experience[achievement.experience_id].append(
                    achievement
                )
            elif achievement.project_id:
                project = next(
                    (item for item in projects if item.id == achievement.project_id),
                    None,
                )
                if project and project.experience_id:
                    achievements_by_experience[project.experience_id].append(
                        achievement
                    )
        skills_by_entity: dict[uuid.UUID, list[Skill]] = defaultdict(list)
        for link in skill_links:
            if skill := skills.get(link.skill_id):
                skills_by_entity[link.entity_id].append(skill)
        evidence_by_entity: dict[uuid.UUID, list[EvidenceItem]] = defaultdict(list)
        for link in evidence_links:
            if evidence := evidence_items.get(link.evidence_item_id):
                evidence_by_entity[link.entity_id].append(evidence)

        signals: list[StorySignal] = []
        for experience in experiences:
            related_projects = projects_by_experience[experience.id]
            related_achievements = achievements_by_experience[experience.id]
            related_entity_ids = [
                experience.id,
                *(item.id for item in related_projects),
                *(item.id for item in related_achievements),
            ]
            related_skills = list(
                {
                    skill.id: skill
                    for entity_id in related_entity_ids
                    for skill in skills_by_entity[entity_id]
                }.values()
            )
            all_entity_ids = related_entity_ids + [item.id for item in related_skills]
            related_evidence = list(
                {
                    evidence.id: evidence
                    for entity_id in all_entity_ids
                    for evidence in evidence_by_entity[entity_id]
                }.values()
            )
            text = " ".join(
                filter(
                    None,
                    [
                        experience.title,
                        experience.summary,
                        self._flatten(experience.responsibilities),
                        *(item.summary or item.title for item in related_projects),
                        *(
                            item.description or item.title
                            for item in related_achievements
                        ),
                    ],
                )
            )
            confidences = [
                self.verification_confidence.get(item.verification_status, 0.5)
                for item in related_evidence
            ]
            signals.append(
                StorySignal(
                    experience_id=experience.id,
                    title=experience.title,
                    organization=experience.organization_name,
                    start_date=experience.start_date,
                    end_date=experience.end_date,
                    summary=experience.summary or "",
                    goals=frozenset(self._goal_terms(text)),
                    projects=frozenset(
                        self._normalize(item.title) for item in related_projects
                    ),
                    skills=frozenset(
                        self._normalize(item.normalized_name) for item in related_skills
                    ),
                    collaborators=frozenset(
                        self._collaborators(experience.responsibilities)
                    ),
                    themes=frozenset(self._keywords(text)),
                    evidence_ids=tuple(item.id for item in related_evidence),
                    evidence_confidence=(
                        sum(confidences) / len(confidences) if confidences else 0.4
                    ),
                    related_entities=tuple(
                        [
                            RelatedStoryEntity(EntityType.PROJECT, item.id, item.title)
                            for item in related_projects
                        ]
                        + [
                            RelatedStoryEntity(
                                EntityType.ACHIEVEMENT, item.id, item.title
                            )
                            for item in related_achievements
                        ]
                        + [
                            RelatedStoryEntity(EntityType.SKILL, item.id, item.name)
                            for item in related_skills
                        ]
                    ),
                )
            )
        return signals

    def evidence_ids_for_entities(
        self,
        session: Session,
        user_id: uuid.UUID,
        entity_ids: list[uuid.UUID],
    ) -> list[uuid.UUID]:
        return list(
            dict.fromkeys(
                session.scalars(
                    select(EvidenceLink.evidence_item_id).where(
                        EvidenceLink.user_id == user_id,
                        EvidenceLink.entity_id.in_(entity_ids),
                    )
                )
            )
        )

    @staticmethod
    def _story_query():
        return select(Story).options(
            selectinload(Story.chapters),
            selectinload(Story.memberships),
            selectinload(Story.evidence_links).selectinload(
                StoryEvidence.evidence_item
            ),
        )

    def _membership_view(
        self,
        session: Session,
        user_id: uuid.UUID,
        membership: StoryMembership,
    ) -> StoryMembershipView:
        entity_type = EntityType(membership.entity_type)
        model = self.entity_models[entity_type]
        entity = session.get(model, membership.entity_id)
        if entity is None or entity.user_id != user_id:
            label, organization = "Unavailable Career Memory item", None
        else:
            label = self._entity_label(entity_type, entity)
            organization = getattr(entity, "organization_name", None)
        return StoryMembershipView(
            id=membership.id,
            entity_type=entity_type,
            entity_id=membership.entity_id,
            chapter_id=membership.chapter_id,
            label=label,
            organization=organization,
            role=membership.role,
            rationale=membership.rationale,
            confidence=float(membership.confidence),
        )

    def _validate_entity_owner(
        self,
        session: Session,
        user_id: uuid.UUID,
        entity_type: EntityType,
        entity_id: uuid.UUID,
    ) -> None:
        entity = session.get(self.entity_models[entity_type], entity_id)
        if (
            entity is None
            or entity.user_id != user_id
            or getattr(entity, "deleted_at", None) is not None
        ):
            raise StoryValidationError(
                "Story members must exist and belong to the current user."
            )

    @staticmethod
    def _entity_label(entity_type: EntityType, entity: Any) -> str:
        if entity_type is EntityType.EDUCATION:
            return entity.institution_name
        return getattr(entity, "title", None) or getattr(entity, "name", "Untitled")

    @staticmethod
    def _ensure_user(session: Session, user_id: uuid.UUID) -> None:
        if session.get(User, user_id) is None:
            session.add(
                User(
                    id=user_id,
                    clerk_user_id=f"story-demo-{user_id}",
                    email=f"story-demo-{user_id}@example.invalid",
                    display_name="Career Story Demo User",
                )
            )
            session.flush()

    @classmethod
    def _keywords(cls, text: str) -> list[str]:
        words = [
            word
            for word in re.findall(r"[a-z][a-z0-9+#-]{2,}", text.casefold())
            if word not in cls.stop_words
        ]
        counts: dict[str, int] = defaultdict(int)
        for word in words:
            counts[word] += 1
        return [
            word for word, _ in sorted(counts.items(), key=lambda item: -item[1])[:8]
        ]

    @classmethod
    def _goal_terms(cls, text: str) -> list[str]:
        keywords = cls._keywords(text)
        return keywords[:4]

    @staticmethod
    def _collaborators(value: Any) -> list[str]:
        if isinstance(value, dict):
            collaborators = value.get("collaborators") or value.get("team") or []
            if isinstance(collaborators, str):
                return [collaborators.casefold().strip()]
            if isinstance(collaborators, list):
                return [str(item).casefold().strip() for item in collaborators]
        return []

    @staticmethod
    def _flatten(value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(
                f"{key} {StoryRepository._flatten(item)}" for key, item in value.items()
            )
        if isinstance(value, list):
            return " ".join(StoryRepository._flatten(item) for item in value)
        return str(value or "")

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def utc_now() -> datetime:
    """Return an aware timestamp for lifecycle services and tests."""

    return datetime.now(UTC)

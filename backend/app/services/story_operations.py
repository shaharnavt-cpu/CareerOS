"""User-directed editing, merging, and splitting of Career Stories."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.schemas.knowledge import EntityType
from app.schemas.stories import (
    StoryChapterInput,
    StoryCreateRequest,
    StoryMembershipInput,
    StoryMergeRequest,
    StoryRenameRequest,
    StorySplitRequest,
    StoryStatus,
    StoryUpdateRequest,
    StoryView,
)
from app.services.story_repository import StoryRepository, StoryValidationError


class StoryOperationsService:
    """Perform reversible narrative operations while preserving Career Memory."""

    def __init__(self, repository: StoryRepository | None = None) -> None:
        self.repository = repository or StoryRepository()

    def create(
        self, session: Session, user_id: uuid.UUID, request: StoryCreateRequest
    ) -> StoryView:
        story = self.repository.create_record(session, user_id, request)
        session.commit()
        return self.repository.to_view(session, story)

    def update(
        self,
        session: Session,
        user_id: uuid.UUID,
        story_id: uuid.UUID,
        request: StoryUpdateRequest,
    ) -> StoryView:
        story = self.repository.get_record(session, user_id, story_id)
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(story, field, value)
        session.commit()
        return self.repository.to_view(session, story)

    def rename(
        self,
        session: Session,
        user_id: uuid.UUID,
        story_id: uuid.UUID,
        request: StoryRenameRequest,
    ) -> StoryView:
        story = self.repository.get_record(session, user_id, story_id)
        story.title = request.title
        session.commit()
        return self.repository.to_view(session, story)

    def merge(
        self,
        session: Session,
        user_id: uuid.UUID,
        request: StoryMergeRequest,
    ) -> StoryView:
        sources = [
            self.repository.get_record(session, user_id, story_id)
            for story_id in request.story_ids
        ]
        if any(story.status == StoryStatus.ARCHIVED.value for story in sources):
            raise StoryValidationError("Archived stories cannot be merged.")

        title = request.title or " + ".join(story.title for story in sources)
        summary = request.summary or " ".join(story.summary for story in sources)
        confidence = sum(float(story.confidence) for story in sources) / len(sources)
        memberships = [
            StoryMembershipInput(
                entity_type=EntityType(membership.entity_type),
                entity_id=membership.entity_id,
                chapter_position=source_index,
                role=membership.role,
                rationale=(f"Merged from {story.title}. {membership.rationale}"),
                confidence=float(membership.confidence),
            )
            for source_index, story in enumerate(sources)
            for membership in story.memberships
        ]
        evidence_ids = list(
            dict.fromkeys(
                link.evidence_item_id
                for story in sources
                for link in story.evidence_links
            )
        )
        merged = self.repository.create_record(
            session,
            user_id,
            StoryCreateRequest(
                title=title,
                summary=summary,
                primary_goal="; ".join(
                    value for story in sources if (value := story.primary_goal)
                )
                or None,
                transformation="; ".join(
                    value for story in sources if (value := story.transformation)
                )
                or None,
                confidence=confidence,
                chapters=[
                    StoryChapterInput(
                        title=story.title,
                        summary=story.summary,
                        position=index,
                    )
                    for index, story in enumerate(sources)
                ],
                memberships=memberships,
                evidence_ids=evidence_ids,
            ),
        )
        for story in sources:
            story.status = StoryStatus.ARCHIVED.value
        session.commit()
        return self.repository.to_view(session, merged)

    def split(
        self,
        session: Session,
        user_id: uuid.UUID,
        story_id: uuid.UUID,
        request: StorySplitRequest,
    ) -> StoryView:
        source = self.repository.get_record(session, user_id, story_id)
        selected_ids = set(request.membership_ids)
        selected = [
            membership
            for membership in source.memberships
            if membership.id in selected_ids
        ]
        if len(selected) != len(selected_ids):
            raise StoryValidationError(
                "Every selected membership must belong to the source story."
            )
        if len(selected) == len(source.memberships):
            raise StoryValidationError(
                "A split must leave at least one membership in the source story."
            )

        entity_ids = [membership.entity_id for membership in selected]
        evidence_ids = self.repository.evidence_ids_for_entities(
            session, user_id, entity_ids
        )
        created = self.repository.create_record(
            session,
            user_id,
            StoryCreateRequest(
                title=request.title,
                summary=request.summary
                or f"A focused narrative split from {source.title}.",
                primary_goal=source.primary_goal,
                transformation=source.transformation,
                confidence=float(source.confidence),
                chapters=[
                    StoryChapterInput(
                        title=request.title,
                        summary=request.summary,
                        position=0,
                    )
                ],
                memberships=[
                    StoryMembershipInput(
                        entity_type=EntityType(membership.entity_type),
                        entity_id=membership.entity_id,
                        chapter_position=0,
                        role=membership.role,
                        rationale=(
                            f"Split from {source.title}. {membership.rationale}"
                        ),
                        confidence=float(membership.confidence),
                    )
                    for membership in selected
                ],
                evidence_ids=evidence_ids,
            ),
        )
        for membership in selected:
            session.delete(membership)
        session.commit()
        return self.repository.to_view(session, created)

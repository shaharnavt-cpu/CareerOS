"""Tests for building the persisted story/chapter/membership graph."""

import uuid
from datetime import UTC, datetime

from app.models import Story, StoryChapter, StoryMembership
from app.schemas.knowledge import EntityType
from app.schemas.stories import (
    StoryChapterInput,
    StoryCreateRequest,
    StoryMembershipInput,
)
from app.services.story_repository import StoryRepository


class FakeSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)

    def flush(self) -> None:
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = uuid.uuid4()
            if hasattr(value, "created_at") and value.created_at is None:
                value.created_at = datetime.now(UTC)
            if hasattr(value, "updated_at") and value.updated_at is None:
                value.updated_at = datetime.now(UTC)


class IsolatedStoryRepository(StoryRepository):
    def _ensure_user(self, session, user_id) -> None:
        del session, user_id

    def _validate_entity_owner(self, session, user_id, entity_type, entity_id) -> None:
        del session, user_id, entity_type, entity_id

    def get_record(self, session, user_id, story_id):
        del user_id
        return next(
            item
            for item in session.added
            if isinstance(item, Story) and item.id == story_id
        )


def test_repository_persists_story_chapters_and_polymorphic_membership() -> None:
    session = FakeSession()
    experience_id = uuid.uuid4()

    story = IsolatedStoryRepository().create_record(  # type: ignore[arg-type]
        session,
        uuid.uuid4(),
        StoryCreateRequest(
            title="Research leadership",
            summary="A coherent research progression.",
            chapters=[StoryChapterInput(title="Foundation", position=0)],
            memberships=[
                StoryMembershipInput(
                    entity_type=EntityType.EXPERIENCE,
                    entity_id=experience_id,
                    chapter_position=0,
                    rationale="Shared research goal.",
                    confidence=0.9,
                )
            ],
        ),
    )

    assert story.title == "Research leadership"
    assert sum(isinstance(item, StoryChapter) for item in session.added) == 1
    membership = next(
        item for item in session.added if isinstance(item, StoryMembership)
    )
    assert membership.entity_id == experience_id
    assert membership.story_id == story.id

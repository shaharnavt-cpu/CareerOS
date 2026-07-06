"""Explicit human approval boundary for Career Stories."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.schemas.stories import StoryStatus, StoryView
from app.services.story_repository import (
    StoryRepository,
    StoryValidationError,
    utc_now,
)


class StoryApprovalService:
    """Apply user decisions without allowing AI proposals to self-approve."""

    def __init__(self, repository: StoryRepository | None = None) -> None:
        self.repository = repository or StoryRepository()

    def approve(
        self, session: Session, user_id: uuid.UUID, story_id: uuid.UUID
    ) -> StoryView:
        story = self.repository.get_record(session, user_id, story_id)
        if story.status != StoryStatus.PROPOSED.value:
            raise StoryValidationError("Only proposed stories can be approved.")
        story.status = StoryStatus.APPROVED.value
        story.approved_at = utc_now()
        session.commit()
        return self.repository.to_view(session, story)

    def reject(
        self, session: Session, user_id: uuid.UUID, story_id: uuid.UUID
    ) -> StoryView:
        story = self.repository.get_record(session, user_id, story_id)
        if story.status != StoryStatus.PROPOSED.value:
            raise StoryValidationError("Only proposed stories can be rejected.")
        story.status = StoryStatus.REJECTED.value
        story.approved_at = None
        session.commit()
        return self.repository.to_view(session, story)

    def archive(
        self, session: Session, user_id: uuid.UUID, story_id: uuid.UUID
    ) -> StoryView:
        story = self.repository.get_record(session, user_id, story_id)
        if story.status == StoryStatus.ARCHIVED.value:
            raise StoryValidationError("Story is already archived.")
        story.status = StoryStatus.ARCHIVED.value
        session.commit()
        return self.repository.to_view(session, story)

"""Tests for story approval, merge, and split operations."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models import Story, StoryMembership
from app.schemas.stories import (
    StoryMergeRequest,
    StorySplitRequest,
    StoryStatus,
    StoryView,
)
from app.services.story_approval import StoryApprovalService
from app.services.story_operations import StoryOperationsService
from app.services.story_repository import StoryValidationError


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.deleted = []

    def commit(self) -> None:
        self.commits += 1

    def delete(self, value) -> None:
        self.deleted.append(value)


class OperationsRepository:
    def __init__(self, stories: list[Story]) -> None:
        self.stories = {story.id: story for story in stories}
        self.created_requests = []

    def get_record(self, session, user_id, story_id):
        del session, user_id
        return self.stories[story_id]

    def create_record(self, session, user_id, request, status=StoryStatus.PROPOSED):
        del session
        self.created_requests.append(request)
        now = datetime.now(UTC)
        story = Story(
            id=uuid.uuid4(),
            user_id=user_id,
            title=request.title,
            summary=request.summary,
            primary_goal=request.primary_goal,
            transformation=request.transformation,
            confidence=Decimal(str(request.confidence)),
            status=status.value,
            created_at=now,
            updated_at=now,
        )
        self.stories[story.id] = story
        return story

    def to_view(self, session, story):
        del session
        return StoryView(
            id=story.id,
            title=story.title,
            summary=story.summary,
            primary_goal=story.primary_goal,
            transformation=story.transformation,
            confidence=float(story.confidence),
            status=StoryStatus(story.status),
            created_at=story.created_at,
            updated_at=story.updated_at,
            approved_at=story.approved_at,
        )

    def evidence_ids_for_entities(self, session, user_id, entity_ids):
        del session, user_id, entity_ids
        return []


def make_story(title: str, membership_count: int = 1) -> Story:
    now = datetime.now(UTC)
    story_id = uuid.uuid4()
    story = Story(
        id=story_id,
        user_id=uuid.uuid4(),
        title=title,
        summary=f"Summary for {title}",
        primary_goal="Grow",
        transformation="Progress",
        confidence=Decimal("0.8"),
        status=StoryStatus.PROPOSED.value,
        created_at=now,
        updated_at=now,
    )
    story.memberships = [
        StoryMembership(
            id=uuid.uuid4(),
            user_id=story.user_id,
            story_id=story_id,
            entity_type="EXPERIENCE",
            entity_id=uuid.uuid4(),
            rationale="Connected experience.",
            confidence=Decimal("0.8"),
        )
        for _ in range(membership_count)
    ]
    story.evidence_links = []
    return story


def test_approval_requires_a_proposed_story_and_records_user_decision() -> None:
    story = make_story("Research")
    repository = OperationsRepository([story])
    session = FakeSession()

    approved = StoryApprovalService(repository).approve(  # type: ignore[arg-type]
        session,
        story.user_id,
        story.id,  # type: ignore[arg-type]
    )

    assert approved.status is StoryStatus.APPROVED
    assert story.approved_at is not None
    with pytest.raises(StoryValidationError, match="Only proposed"):
        StoryApprovalService(repository).approve(  # type: ignore[arg-type]
            session,
            story.user_id,
            story.id,  # type: ignore[arg-type]
        )


def test_merge_creates_proposal_and_archives_source_stories() -> None:
    first, second = make_story("Research"), make_story("Leadership")
    second.user_id = first.user_id
    repository = OperationsRepository([first, second])
    session = FakeSession()

    merged = StoryOperationsService(repository).merge(  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
        first.user_id,
        StoryMergeRequest(story_ids=[first.id, second.id], title="Research leader"),
    )

    assert merged.title == "Research leader"
    assert len(repository.created_requests[0].memberships) == 2
    assert first.status == second.status == StoryStatus.ARCHIVED.value
    assert session.commits == 1


def test_split_moves_a_strict_subset_into_a_new_proposal() -> None:
    source = make_story("Broad story", membership_count=2)
    repository = OperationsRepository([source])
    session = FakeSession()
    selected = source.memberships[0]

    created = StoryOperationsService(repository).split(  # type: ignore[arg-type]
        session,  # type: ignore[arg-type]
        source.user_id,
        source.id,
        StorySplitRequest(membership_ids=[selected.id], title="Focused research story"),
    )

    assert created.status is StoryStatus.PROPOSED
    assert repository.created_requests[0].memberships[0].entity_id == selected.entity_id
    assert session.deleted == [selected]


def test_split_rejects_moving_every_membership() -> None:
    source = make_story("Single experience")
    repository = OperationsRepository([source])

    with pytest.raises(StoryValidationError, match="leave at least one"):
        StoryOperationsService(repository).split(  # type: ignore[arg-type]
            FakeSession(),  # type: ignore[arg-type]
            source.user_id,
            source.id,
            StorySplitRequest(
                membership_ids=[source.memberships[0].id], title="Invalid split"
            ),
        )

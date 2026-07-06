"""Tests for story discovery and proposal persistence orchestration."""

import uuid
from datetime import UTC, date, datetime
from types import SimpleNamespace

from app.schemas.stories import StoryStatus, StoryView
from app.services.story_clustering import StorySignal
from app.services.story_discovery import StoryDiscoveryService


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class DiscoveryRepository:
    def __init__(self, signals: list[StorySignal]) -> None:
        self.signals = signals
        self.created = []

    def load_discovery_signals(self, session, user_id):
        del session, user_id
        return self.signals

    def list_records(self, session, user_id, include_archived=False):
        del session, user_id, include_archived
        return []

    def create_record(self, session, user_id, request, status):
        del session, user_id
        record = SimpleNamespace(request=request, status=status)
        self.created.append(record)
        return record

    def to_view(self, session, record):
        del session
        now = datetime.now(UTC)
        return StoryView(
            id=uuid.uuid4(),
            title=record.request.title,
            summary=record.request.summary,
            primary_goal=record.request.primary_goal,
            transformation=record.request.transformation,
            confidence=record.request.confidence,
            status=record.status,
            created_at=now,
            updated_at=now,
            approved_at=None,
        )


def test_discovery_proposes_but_never_approves_a_story() -> None:
    repository = DiscoveryRepository(
        [
            StorySignal(
                experience_id=uuid.uuid4(),
                title="Researcher",
                organization="Lab",
                start_date=date(2025, 1, 1),
                themes=frozenset({"research"}),
            )
        ]
    )
    session = FakeSession()

    result = StoryDiscoveryService(repository=repository).discover(  # type: ignore[arg-type]
        session,
        uuid.uuid4(),  # type: ignore[arg-type]
    )

    assert result.stories[0].status is StoryStatus.PROPOSED
    assert result.experiences_considered == 1
    assert "evidence confidence" in result.signals_used
    assert session.commits == 1

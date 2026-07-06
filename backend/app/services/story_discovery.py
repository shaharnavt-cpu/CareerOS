"""Orchestration for proposing stories from canonical Career Memory."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.schemas.knowledge import EntityType
from app.schemas.stories import StoryDiscoveryResponse, StoryStatus
from app.services.story_clustering import StoryClusteringService
from app.services.story_repository import StoryRepository
from app.services.story_summarization import StorySummarizationService


class StoryDiscoveryService:
    """Discover, explain, summarize, and persist proposed Career Stories."""

    signals_used = [
        "organizations",
        "projects",
        "skills",
        "collaborators",
        "chronology",
        "goals",
        "repeated themes",
        "evidence confidence",
    ]

    def __init__(
        self,
        repository: StoryRepository | None = None,
        clustering: StoryClusteringService | None = None,
        summarization: StorySummarizationService | None = None,
    ) -> None:
        self.repository = repository or StoryRepository()
        self.clustering = clustering or StoryClusteringService()
        self.summarization = summarization or StorySummarizationService()

    def discover(self, session: Session, user_id: uuid.UUID) -> StoryDiscoveryResponse:
        signals = self.repository.load_discovery_signals(session, user_id)
        clusters = self.clustering.cluster(signals)
        existing = self.repository.list_records(session, user_id, include_archived=True)
        existing_experience_sets = {
            frozenset(
                membership.entity_id
                for membership in story.memberships
                if membership.entity_type == EntityType.EXPERIENCE.value
            )
            for story in existing
            if story.status in {StoryStatus.PROPOSED.value, StoryStatus.APPROVED.value}
        }

        created = []
        for cluster in clusters:
            experience_ids = frozenset(
                signal.experience_id for signal in cluster.signals
            )
            if experience_ids in existing_experience_sets:
                continue
            request = self.summarization.summarize(cluster)
            created.append(
                self.repository.create_record(
                    session, user_id, request, status=StoryStatus.PROPOSED
                )
            )
            existing_experience_sets.add(experience_ids)

        session.commit()
        stories = [self.repository.to_view(session, story) for story in created]
        return StoryDiscoveryResponse(
            stories=stories,
            experiences_considered=len(signals),
            signals_used=self.signals_used,
            explanation=(
                "CareerOS proposed reviewable groupings from canonical Career Memory. "
                "No proposal is approved automatically."
            ),
        )

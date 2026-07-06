"""Provider-ready summarization for explainable Career Story proposals."""

from __future__ import annotations

from collections import Counter

from app.schemas.knowledge import EntityType
from app.schemas.stories import (
    StoryChapterInput,
    StoryCreateRequest,
    StoryMembershipInput,
)
from app.services.story_clustering import StoryCluster


class StorySummarizationService:
    """Create reviewable story language without inventing unsupported facts."""

    def summarize(self, cluster: StoryCluster) -> StoryCreateRequest:
        signals = cluster.signals
        organizations = Counter(signal.organization for signal in signals)
        organization = organizations.most_common(1)[0][0]
        common_themes = self._common_values(signal.themes for signal in signals)
        common_skills = self._common_values(signal.skills for signal in signals)
        theme = next(iter(common_themes or common_skills), "professional growth")

        if len(signals) == 1:
            title = f"{signals[0].title} at {organization}"
            summary = signals[0].summary or (
                f"A focused chapter centered on {signals[0].title} at {organization}."
            )
        else:
            title = f"Building {theme.title()} through {organization}"
            roles = ", ".join(signal.title for signal in signals)
            summary = (
                f"A connected progression across {roles}, linked by {theme} and "
                f"work associated with {organization}."
            )

        primary_goal = (
            f"Develop and apply {theme} across related professional experiences."
        )
        transformation = self._transformation(cluster)

        chapters = [
            StoryChapterInput(
                title=signal.title,
                summary=signal.summary or None,
                position=index,
                start_date=signal.start_date,
                end_date=signal.end_date,
            )
            for index, signal in enumerate(signals)
        ]
        memberships: list[StoryMembershipInput] = []
        for index, signal in enumerate(signals):
            rationale = cluster.rationales[signal.experience_id]
            memberships.append(
                StoryMembershipInput(
                    entity_type=EntityType.EXPERIENCE,
                    entity_id=signal.experience_id,
                    chapter_position=index,
                    role="CORE_EXPERIENCE",
                    rationale=rationale,
                    confidence=cluster.confidence,
                )
            )
            memberships.extend(
                StoryMembershipInput(
                    entity_type=related.entity_type,
                    entity_id=related.entity_id,
                    chapter_position=index,
                    role="RELATED_ENTITY",
                    rationale=(
                        f"{related.label} is directly connected to {signal.title}."
                    ),
                    confidence=cluster.confidence,
                )
                for related in signal.related_entities
            )

        evidence_ids = list(
            dict.fromkeys(
                evidence_id for signal in signals for evidence_id in signal.evidence_ids
            )
        )
        return StoryCreateRequest(
            title=title,
            summary=summary,
            primary_goal=primary_goal,
            transformation=transformation,
            confidence=cluster.confidence,
            chapters=chapters,
            memberships=memberships,
            evidence_ids=evidence_ids,
        )

    @staticmethod
    def _common_values(groups) -> list[str]:
        counts = Counter(value for group in groups for value in group)
        return [value for value, _ in counts.most_common(3)]

    @staticmethod
    def _transformation(cluster: StoryCluster) -> str:
        first, last = cluster.signals[0], cluster.signals[-1]
        if len(cluster.signals) == 1:
            return (
                f"Turned the responsibilities of {first.title} into demonstrable "
                "experience and evidence."
            )
        return (
            f"Progressed from {first.title} toward {last.title}, carrying forward "
            "shared skills, goals, and themes."
        )

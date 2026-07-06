"""Explainable clustering for Career Story candidates."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date

from app.schemas.knowledge import EntityType


@dataclass(frozen=True)
class RelatedStoryEntity:
    """A canonical entity connected to an experience signal."""

    entity_type: EntityType
    entity_id: uuid.UUID
    label: str


@dataclass(frozen=True)
class StorySignal:
    """Normalized signals for one canonical experience."""

    experience_id: uuid.UUID
    title: str
    organization: str
    start_date: date | None = None
    end_date: date | None = None
    summary: str = ""
    goals: frozenset[str] = frozenset()
    projects: frozenset[str] = frozenset()
    skills: frozenset[str] = frozenset()
    collaborators: frozenset[str] = frozenset()
    themes: frozenset[str] = frozenset()
    evidence_ids: tuple[uuid.UUID, ...] = ()
    evidence_confidence: float = 0.5
    related_entities: tuple[RelatedStoryEntity, ...] = ()


@dataclass
class StoryCluster:
    """A candidate grouping plus user-facing membership reasons."""

    signals: list[StorySignal]
    confidence: float
    rationales: dict[uuid.UUID, str] = field(default_factory=dict)


class StoryClusteringService:
    """Group experiences using transparent, independently weighted signals."""

    threshold = 0.33

    def cluster(self, signals: list[StorySignal]) -> list[StoryCluster]:
        if not signals:
            return []

        parents = list(range(len(signals)))
        pair_scores: dict[tuple[int, int], tuple[float, list[str]]] = {}

        def find(index: int) -> int:
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        def union(left: int, right: int) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parents[right_root] = left_root

        for left in range(len(signals)):
            for right in range(left + 1, len(signals)):
                score, reasons = self.similarity(signals[left], signals[right])
                pair_scores[(left, right)] = (score, reasons)
                if score >= self.threshold:
                    union(left, right)

        grouped: dict[int, list[int]] = {}
        for index in range(len(signals)):
            grouped.setdefault(find(index), []).append(index)

        clusters: list[StoryCluster] = []
        for indexes in grouped.values():
            members = [signals[index] for index in indexes]
            linked_scores = [
                pair_scores[tuple(sorted((left, right)))][0]
                for offset, left in enumerate(indexes)
                for right in indexes[offset + 1 :]
            ]
            evidence = sum(item.evidence_confidence for item in members) / len(members)
            coherence = (
                sum(linked_scores) / len(linked_scores) if linked_scores else 0.5
            )
            confidence = min(0.98, 0.4 + coherence * 0.4 + evidence * 0.2)
            rationales = {
                signals[index].experience_id: self._membership_rationale(
                    index, indexes, signals, pair_scores
                )
                for index in indexes
            }
            clusters.append(
                StoryCluster(
                    signals=sorted(
                        members,
                        key=lambda item: item.start_date or date.max,
                    ),
                    confidence=round(confidence, 3),
                    rationales=rationales,
                )
            )

        return sorted(
            clusters,
            key=lambda cluster: cluster.signals[0].start_date or date.max,
        )

    def similarity(
        self, left: StorySignal, right: StorySignal
    ) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 0.0

        if self._normalized(left.organization) == self._normalized(right.organization):
            score += 0.26
            reasons.append(f"shared organization ({left.organization})")

        project_score = self._jaccard(left.projects, right.projects)
        if project_score:
            score += 0.16 * project_score
            reasons.append("related projects")

        skill_score = self._jaccard(left.skills, right.skills)
        if skill_score:
            score += 0.18 * skill_score
            reasons.append("repeated skills")

        collaborator_score = self._jaccard(left.collaborators, right.collaborators)
        if collaborator_score:
            score += 0.1 * collaborator_score
            reasons.append("shared collaborators")

        chronology_score = self._chronology(left, right)
        score += 0.12 * chronology_score
        if chronology_score >= 0.6:
            reasons.append("connected chronology")

        goal_score = self._jaccard(left.goals, right.goals)
        if goal_score:
            score += 0.1 * goal_score
            reasons.append("shared goals")

        theme_score = self._jaccard(left.themes, right.themes)
        if theme_score:
            score += 0.06 * theme_score
            reasons.append("repeated themes")

        evidence_score = min(left.evidence_confidence, right.evidence_confidence)
        score += 0.02 * evidence_score
        if evidence_score >= 0.75:
            reasons.append("strong supporting evidence")

        return round(score, 3), reasons

    def _membership_rationale(
        self,
        index: int,
        cluster_indexes: list[int],
        signals: list[StorySignal],
        pair_scores: dict[tuple[int, int], tuple[float, list[str]]],
    ) -> str:
        reasons: list[str] = []
        for other in cluster_indexes:
            if index == other:
                continue
            _, pair_reasons = pair_scores[tuple(sorted((index, other)))]
            reasons.extend(pair_reasons)
        unique = list(dict.fromkeys(reasons))
        if not unique:
            signal = signals[index]
            if signal.evidence_ids:
                return "A distinct experience with direct supporting evidence."
            return "A distinct Career Memory experience worth reviewing as a story."
        return "Included because of " + ", ".join(unique[:4]) + "."

    @staticmethod
    def _normalized(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()

    @staticmethod
    def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    @staticmethod
    def _chronology(left: StorySignal, right: StorySignal) -> float:
        left_start = left.start_date
        left_end = left.end_date or left.start_date
        right_start = right.start_date
        right_end = right.end_date or right.start_date
        if not all((left_start, left_end, right_start, right_end)):
            return 0.2
        assert left_start and left_end and right_start and right_end
        if left_start <= right_end and right_start <= left_end:
            return 1.0
        gap = min(
            abs((right_start - left_end).days), abs((left_start - right_end).days)
        )
        if gap <= 180:
            return 0.8
        if gap <= 365:
            return 0.6
        if gap <= 730:
            return 0.3
        return 0.0

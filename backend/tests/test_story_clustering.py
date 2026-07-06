"""Tests for explainable, overlapping Career Story discovery."""

import uuid
from datetime import date

from app.services.story_clustering import StoryClusteringService, StorySignal


def signal(
    title: str,
    organization: str,
    start: date,
    *,
    skills: set[str] | None = None,
    themes: set[str] | None = None,
) -> StorySignal:
    return StorySignal(
        experience_id=uuid.uuid4(),
        title=title,
        organization=organization,
        start_date=start,
        end_date=date(start.year, 12, 31),
        skills=frozenset(skills or set()),
        themes=frozenset(themes or set()),
        evidence_confidence=0.9,
    )


def test_clustering_connects_shared_organization_skills_and_chronology() -> None:
    research = signal(
        "Research Assistant",
        "Astrophysics Lab",
        date(2024, 1, 1),
        skills={"python", "analysis"},
        themes={"galaxies", "research"},
    )
    lead = signal(
        "Research Lead",
        "Astrophysics Lab",
        date(2024, 8, 1),
        skills={"python", "leadership"},
        themes={"galaxies", "research"},
    )
    unrelated = signal(
        "Volunteer",
        "Food Bank",
        date(2021, 1, 1),
        skills={"service"},
        themes={"community"},
    )

    clusters = StoryClusteringService().cluster([research, lead, unrelated])

    assert sorted(len(cluster.signals) for cluster in clusters) == [1, 2]
    connected = next(cluster for cluster in clusters if len(cluster.signals) == 2)
    assert "shared organization" in connected.rationales[research.experience_id]
    assert 0 <= connected.confidence <= 1


def test_similarity_explains_each_signal_family_it_uses() -> None:
    left = signal(
        "Engineer",
        "Acme",
        date(2025, 1, 1),
        skills={"python"},
        themes={"automation"},
    )
    right = signal(
        "Senior Engineer",
        "Acme",
        date(2025, 6, 1),
        skills={"python"},
        themes={"automation"},
    )

    score, reasons = StoryClusteringService().similarity(left, right)

    assert score >= StoryClusteringService.threshold
    assert "repeated skills" in reasons
    assert "repeated themes" in reasons
    assert "strong supporting evidence" in reasons

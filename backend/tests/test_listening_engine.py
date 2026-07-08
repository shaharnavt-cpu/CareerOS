"""Unit tests for adapters, listeners, fusion, and reasoning handoff."""

from __future__ import annotations

import uuid

import pytest

from app.schemas.knowledge import DEMO_USER_ID, SourceType
from app.schemas.listening import (
    EvidenceCategory,
    EvidenceObject,
    SourceSubmission,
)
from app.services.evidence_fusion import EvidenceFusionService
from app.services.listening import ListeningEngine, ListeningReasoningBridge
from app.services.llm import LocalSemanticReasoningProvider
from app.services.pipeline import KnowledgeReasoningPipeline
from app.services.source_adapters import SourceAdapterRegistry


@pytest.mark.parametrize(
    "source_type",
    [
        SourceType.RESUME,
        SourceType.TRANSCRIPT,
        SourceType.LINKEDIN,
        SourceType.MANUAL,
        SourceType.CONVERSATION,
        SourceType.GENERIC_DOCUMENT,
    ],
)
def test_text_adapter_is_idempotent_and_preserves_provenance(
    source_type: SourceType,
) -> None:
    submission = SourceSubmission(
        source_type=source_type,
        label="Primary source",
        raw_text="Skills\r\nPython  ",
        original_filename="profile.txt",
        metadata={"section": "import"},
    )
    registry = SourceAdapterRegistry()

    first = registry.normalize(submission, DEMO_USER_ID)
    second = registry.normalize(submission, DEMO_USER_ID)

    assert first.id == second.id
    assert first.content_hash == second.content_hash
    assert first.raw_text == "Skills\nPython"
    assert first.provenance["original_filename"] == "profile.txt"
    assert first.provenance["adapter_version"] == "text-adapter-v1"


@pytest.mark.parametrize(
    ("source_type", "raw_text", "expected_category"),
    [
        (
            SourceType.RESUME,
            "Education\nExample University",
            EvidenceCategory.EDUCATION,
        ),
        (
            SourceType.TRANSCRIPT,
            "Example University\nGraduated 2025",
            EvidenceCategory.EDUCATION,
        ),
        (
            SourceType.LINKEDIN,
            "Experience\nEngineer at Acme",
            EvidenceCategory.EXPERIENCE,
        ),
        (
            SourceType.CONVERSATION,
            "I built the Atlas project",
            EvidenceCategory.PROJECT,
        ),
        (SourceType.MANUAL, "Skills: Python", EvidenceCategory.SKILL),
        (
            SourceType.GENERIC_DOCUMENT,
            "Received the research award",
            EvidenceCategory.ACHIEVEMENT,
        ),
    ],
)
def test_source_specific_listeners_emit_standard_evidence(
    source_type: SourceType,
    raw_text: str,
    expected_category: EvidenceCategory,
) -> None:
    _, evidence, _ = ListeningEngine().listen(
        SourceSubmission(
            source_type=source_type,
            label="Source label",
            raw_text=raw_text,
        ),
        DEMO_USER_ID,
    )

    primary = evidence[0]
    assert primary.category is expected_category
    assert primary.raw_excerpt
    assert primary.normalized_excerpt
    assert primary.location["line"] >= 1
    assert primary.provenance["label"] == "Source label"
    assert 0 <= primary.confidence <= 1


def test_listener_extracts_skill_role_and_organization_fragments() -> None:
    _, evidence, _ = ListeningEngine().listen(
        SourceSubmission(
            source_type=SourceType.RESUME,
            label="Resume",
            raw_text=("Experience\nSoftware Engineer at Acme\nSkills\nPython, SQL"),
        ),
        DEMO_USER_ID,
    )

    assert any(
        item.category is EvidenceCategory.ROLE
        and item.raw_excerpt == "Software Engineer"
        for item in evidence
    )
    assert any(
        item.category is EvidenceCategory.ORGANIZATION and item.raw_excerpt == "Acme"
        for item in evidence
    )
    assert {
        item.raw_excerpt for item in evidence if item.category is EvidenceCategory.SKILL
    } == {"Python", "SQL"}


def make_evidence(
    excerpt: str,
    source_id: uuid.UUID,
    *,
    claim_key: str | None = None,
) -> EvidenceObject:
    provenance = {"label": f"Source {source_id}"}
    if claim_key:
        provenance["claim_key"] = claim_key
    return EvidenceObject(
        source_id=source_id,
        source_type=SourceType.RESUME,
        raw_excerpt=excerpt,
        normalized_excerpt=excerpt.casefold(),
        category=EvidenceCategory.EXPERIENCE,
        confidence=0.9,
        provenance=provenance,
    )


def test_fusion_groups_duplicates_and_corroborating_sources() -> None:
    first_source = uuid.uuid4()
    second_source = uuid.uuid4()
    evidence = [
        make_evidence("Software Engineer at Acme", first_source),
        make_evidence("Software Engineer at Acme", first_source),
        make_evidence("Software Engineer at Acme", second_source),
    ]

    clusters = EvidenceFusionService().fuse(evidence)

    assert len(clusters) == 1
    assert len(clusters[0].evidence) == 3
    assert clusters[0].corroborated is True
    assert set(clusters[0].contributing_source_ids) == {first_source, second_source}


def test_fusion_preserves_conflicting_claims_and_every_source() -> None:
    first_source = uuid.uuid4()
    second_source = uuid.uuid4()
    evidence = [
        make_evidence("Engineer at Acme, 2022-2024", first_source),
        make_evidence("Engineer at Acme, 2022-2025", second_source),
    ]

    cluster = EvidenceFusionService().fuse(evidence)[0]

    assert len(cluster.evidence) == 2
    assert cluster.has_conflicts is True
    assert cluster.conflicting_claims[0].evidence_ids == [
        evidence[0].id,
        evidence[1].id,
    ]
    assert "different dates" in cluster.conflicting_claims[0].reason


def test_fusion_groups_expanded_name_with_acronym() -> None:
    evidence = [
        make_evidence(
            "Galaxy Evolution Vertically Integrated Program (GEVIP)", uuid.uuid4()
        ),
        make_evidence("GEVIP was my astronomy research program", uuid.uuid4()),
    ]

    assert len(EvidenceFusionService().fuse(evidence)) == 1


@pytest.mark.asyncio
async def test_fused_evidence_reaches_sprint_four_with_full_provenance() -> None:
    source_one = uuid.uuid4()
    source_two = uuid.uuid4()
    cluster = EvidenceFusionService().fuse(
        [
            EvidenceObject(
                source_id=source_one,
                source_type=SourceType.RESUME,
                raw_excerpt="Python",
                normalized_excerpt="python",
                category=EvidenceCategory.SKILL,
                confidence=0.91,
                provenance={"label": "Resume"},
            ),
            EvidenceObject(
                source_id=source_two,
                source_type=SourceType.CONVERSATION,
                raw_excerpt="Python",
                normalized_excerpt="python",
                category=EvidenceCategory.SKILL,
                confidence=0.82,
                provenance={"label": "Career interview"},
            ),
        ]
    )
    bridge = ListeningReasoningBridge(
        KnowledgeReasoningPipeline(LocalSemanticReasoningProvider())
    )

    response = await bridge.generate(cluster, [])

    assert response.provider == "knowledge-review-intelligence:local-semantic-v1"
    assert len(response.proposals) == 1
    proposal = response.proposals[0]
    assert len(proposal.evidence) == 2
    assert {item.title for item in proposal.evidence} == {
        "Resume",
        "Career interview",
    }
    assert all(item.evidence_id for item in proposal.evidence)
    assert all(item.corroborated for item in proposal.evidence)


@pytest.mark.asyncio
async def test_fusion_conflict_becomes_sprint_four_clarification() -> None:
    cluster = EvidenceFusionService().fuse(
        [
            make_evidence("Engineer at Acme, 2022-2024", uuid.uuid4()),
            make_evidence("Engineer at Acme, 2022-2025", uuid.uuid4()),
        ]
    )
    bridge = ListeningReasoningBridge(
        KnowledgeReasoningPipeline(LocalSemanticReasoningProvider())
    )

    response = await bridge.generate(cluster, [])

    assert response.proposals
    assert all(proposal.clarification for proposal in response.proposals)
    assert all(
        proposal.clarification.reason.value == "CONFLICTING_EVIDENCE"
        for proposal in response.proposals
        if proposal.clarification
    )

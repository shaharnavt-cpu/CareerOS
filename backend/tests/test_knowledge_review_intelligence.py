"""Structured, low-noise Knowledge Review Intelligence tests."""

from __future__ import annotations

import uuid

from app.schemas.knowledge import ReviewProposalType, SourceType
from app.schemas.listening import EvidenceCategory, EvidenceCluster, EvidenceObject
from app.services.knowledge_review_intelligence import KnowledgeReviewIntelligence

RESUME_ID = uuid.uuid4()
TRANSCRIPT_ID = uuid.uuid4()


def evidence(
    text: str,
    category: EvidenceCategory,
    line: int,
    *,
    transcript: bool = False,
) -> EvidenceObject:
    source_id = TRANSCRIPT_ID if transcript else RESUME_ID
    filename = "Transcript.pdf" if transcript else "Resume.pdf"
    return EvidenceObject(
        source_id=source_id,
        source_type=SourceType.TRANSCRIPT if transcript else SourceType.RESUME,
        raw_excerpt=text,
        normalized_excerpt=text.casefold(),
        category=category,
        confidence=0.9,
        location={"line": line},
        provenance={"original_filename": filename, "label": filename},
    )


def clusters(items: list[EvidenceObject]) -> list[EvidenceCluster]:
    return [
        EvidenceCluster(
            category=item.category,
            label=item.raw_excerpt,
            normalized_key=f"item-{index}",
            evidence=[item],
            contributing_source_ids=[item.source_id],
        )
        for index, item in enumerate(items)
    ]


def test_resume_and_transcript_become_structured_low_noise_review_items() -> None:
    items = [
        evidence("[Page 1]", EvidenceCategory.UNKNOWN, 1),
        evidence(
            "The University of Texas at Dallas May 2027",
            EvidenceCategory.EDUCATION,
            5,
        ),
        evidence(
            "Master of Science, Business Analytics and AI (Data Science Track)",
            EvidenceCategory.EDUCATION,
            6,
        ),
        evidence("UT-Dallas", EvidenceCategory.EDUCATION, 4, transcript=True),
        evidence(
            "Business Analytics and Artificial Intelligence",
            EvidenceCategory.EDUCATION,
            8,
            transcript=True,
        ),
        evidence(
            "Data Science Concentration",
            EvidenceCategory.EDUCATION,
            10,
            transcript=True,
        ),
        evidence("Python", EvidenceCategory.SKILL, 20),
        evidence("Python", EvidenceCategory.SKILL, 21),
        evidence("SQL", EvidenceCategory.SKILL, 22),
        evidence(
            "Department of Astronomy, UT Austin, TX Aug 2023 – Jan 2025",
            EvidenceCategory.EXPERIENCE,
            30,
        ),
        evidence(
            "Undergraduate Learning Assistant",
            EvidenceCategory.EXPERIENCE,
            31,
        ),
        evidence(
            "Simplified quantitative concepts for 250 students",
            EvidenceCategory.EXPERIENCE,
            32,
        ),
    ]

    result = KnowledgeReviewIntelligence().synthesize(clusters(items))

    education = [
        item
        for item in result.proposals
        if item.proposal_type is ReviewProposalType.EDUCATION
    ]
    assert len(education) == 1
    assert education[0].proposed_value["institution_name"] == (
        "University of Texas at Dallas"
    )
    assert education[0].proposed_value["degree"] == "Master of Science"
    assert education[0].proposed_value["track"] == "Data Science"
    assert set(education[0].source_names) == {"Resume.pdf", "Transcript.pdf"}

    skill_sets = [
        item
        for item in result.proposals
        if item.proposal_type is ReviewProposalType.SKILL_SET
    ]
    assert len(skill_sets) == 1
    assert skill_sets[0].proposed_value["skills"] == ["Python", "SQL"]

    experience = next(
        item
        for item in result.proposals
        if item.proposal_type is ReviewProposalType.EXPERIENCE
    )
    assert experience.proposed_value["organization_name"] == (
        "University of Texas at Austin"
    )
    assert experience.proposed_value["department"] == "Department of Astronomy"
    assert experience.proposed_value["title"] == "Undergraduate Learning Assistant"

    assert len(result.proposals) < len(items)
    assert result.hidden_supporting_evidence_count > 0
    assert all(proposal.evidence for proposal in result.proposals)
    assert all(proposal.reasoning_summary for proposal in result.proposals)

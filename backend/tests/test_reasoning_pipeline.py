"""Unit tests for the hybrid Knowledge Reasoning Engine."""

import uuid

import pytest

from app.core.config import Settings
from app.schemas.knowledge import (
    ClarificationReason,
    EntityType,
    ExistingMemoryItem,
    ProposalOperation,
    ProposalRelationship,
    ReasoningRequest,
    SemanticAssessment,
    SourceType,
)
from app.services.confidence import ConfidenceAggregator
from app.services.extraction import EntityExtractor
from app.services.llm import LocalSemanticReasoningProvider, build_reasoning_provider
from app.services.normalization import SourceNormalizer
from app.services.pipeline import KnowledgeReasoningPipeline
from app.services.proposals import ProposalBuilder, ReasoningValidationError


@pytest.fixture
def resume_request() -> ReasoningRequest:
    return ReasoningRequest(
        raw_source=(
            "Education\r\n"
            "• The University of Texas at Austin | BS in Astronomy\r\n"
            "Skills\r\n"
            "Python, SQL\r\n"
            "Projects\r\n"
            "Gas Kinematics Capstone"
        ),
        source_type=SourceType.RESUME,
        source_name="Resume.txt",
    )


def test_normalization_is_stable_and_preserves_locations(
    resume_request: ReasoningRequest,
) -> None:
    normalizer = SourceNormalizer()

    first = normalizer.normalize(resume_request)
    second = normalizer.normalize(resume_request)

    assert first.id == second.id
    assert first.content_hash == second.content_hash
    assert first.lines[1].number == 2
    assert first.lines[1].text.startswith("The University")


def test_extractor_identifies_sections_and_splits_skills(
    resume_request: ReasoningRequest,
) -> None:
    source = SourceNormalizer().normalize(resume_request)

    candidates = EntityExtractor().extract(source)

    assert [candidate.hinted_type for candidate in candidates] == [
        EntityType.EDUCATION,
        EntityType.SKILL,
        EntityType.SKILL,
        EntityType.PROJECT,
    ]
    assert [candidate.raw_value for candidate in candidates[1:3]] == ["Python", "SQL"]


@pytest.mark.asyncio
async def test_pipeline_generates_deterministic_explainable_proposals(
    resume_request: ReasoningRequest,
) -> None:
    pipeline = KnowledgeReasoningPipeline(LocalSemanticReasoningProvider())

    first = await pipeline.run(resume_request)
    second = await pipeline.run(resume_request)

    assert first == second
    assert first.summary.proposals == 4
    assert {proposal.entity_type for proposal in first.proposals} == {
        EntityType.EDUCATION,
        EntityType.SKILL,
        EntityType.PROJECT,
    }
    assert all(proposal.evidence for proposal in first.proposals)
    assert all(proposal.reasoning_summary for proposal in first.proposals)
    assert all(0 <= proposal.confidence <= 1 for proposal in first.proposals)


@pytest.mark.asyncio
async def test_pipeline_marks_existing_memory_as_an_update() -> None:
    canonical_id = uuid.uuid4()
    request = ReasoningRequest(
        raw_source="Skills\nPython",
        existing_memory=[
            ExistingMemoryItem(
                id=canonical_id,
                entity_type=EntityType.SKILL,
                value={"name": "Python", "normalized_name": "python"},
            )
        ],
    )

    response = await KnowledgeReasoningPipeline(LocalSemanticReasoningProvider()).run(
        request
    )

    assert response.proposals[0].operation is ProposalOperation.UPDATE
    assert response.proposals[0].duplicate_of == canonical_id


def test_builder_replaces_generic_question_with_specific_clarification() -> None:
    source = SourceNormalizer().normalize(
        ReasoningRequest(raw_source="GEVIP", source_name="Conversation")
    )
    candidate = EntityExtractor().extract(source)[0]
    assessment = SemanticAssessment(
        candidate_id=candidate.id,
        entity_type=EntityType.PROGRAM,
        proposed_value={"name": "GEVIP"},
        semantic_confidence=0.4,
        reasoning_summary="GEVIP may be a structured program.",
        missing_fields=["program category"],
        clarification_question="Tell me more.",
    )

    proposal = ProposalBuilder().build(source, [candidate], [assessment], [])[0]

    assert proposal.clarification is not None
    assert "GEVIP" in proposal.clarification.question
    assert not proposal.clarification.question.startswith("Tell me more")


def test_builder_rejects_missing_semantic_assessments() -> None:
    source = SourceNormalizer().normalize(ReasoningRequest(raw_source="Skills\nPython"))
    candidates = EntityExtractor().extract(source)

    with pytest.raises(ReasoningValidationError, match="exactly one"):
        ProposalBuilder().build(source, candidates, [], [])


def test_relationship_validation_filters_unsupported_links() -> None:
    source = SourceNormalizer().normalize(
        ReasoningRequest(raw_source="Programs\nGEVIP\nSkills\nPython")
    )
    candidates = EntityExtractor().extract(source)
    program, skill = candidates
    assessments = [
        SemanticAssessment(
            candidate_id=program.id,
            entity_type=EntityType.PROGRAM,
            proposed_value={"name": "GEVIP"},
            semantic_confidence=0.9,
            reasoning_summary="A structured program.",
        ),
        SemanticAssessment(
            candidate_id=skill.id,
            entity_type=EntityType.SKILL,
            proposed_value={"name": "Python", "normalized_name": "python"},
            semantic_confidence=0.9,
            reasoning_summary="A technical skill.",
            relationships=[
                ProposalRelationship(
                    target_proposal_id=program.id,
                    relationship_type="demonstrated_by",
                ),
                ProposalRelationship(
                    target_proposal_id="missing-candidate",
                    relationship_type="invalid",
                ),
            ],
        ),
    ]

    proposals = ProposalBuilder().build(source, candidates, assessments, [])

    skill_proposal = next(
        proposal for proposal in proposals if proposal.entity_type is EntityType.SKILL
    )
    assert len(skill_proposal.relationships) == 1
    assert skill_proposal.relationships[0].relationship_type == "DEMONSTRATED_BY"


@pytest.mark.parametrize(
    ("has_evidence", "semantic_confidence", "conflicts", "expected"),
    [
        (False, 0.95, [], ClarificationReason.MISSING_EVIDENCE),
        (True, 0.95, ["2024 versus 2025"], ClarificationReason.CONFLICTING_EVIDENCE),
        (True, 0.2, [], ClarificationReason.LOW_CONFIDENCE),
        (True, 0.95, [], None),
    ],
)
def test_clarifications_have_only_allowed_deterministic_reasons(
    has_evidence: bool,
    semantic_confidence: float,
    conflicts: list[str],
    expected: ClarificationReason | None,
) -> None:
    source = SourceNormalizer().normalize(ReasoningRequest(raw_source="Skills\nPython"))
    candidate = EntityExtractor().extract(source)[0]
    assessment = SemanticAssessment(
        candidate_id=candidate.id,
        entity_type=EntityType.SKILL,
        proposed_value={"name": "Python", "normalized_name": "python"},
        semantic_confidence=semantic_confidence,
        reasoning_summary="Python is a technical skill.",
        conflicting_evidence=conflicts,
    )
    confidence = ConfidenceAggregator()
    score = confidence.aggregate(candidate, assessment, has_evidence=has_evidence)

    assert (
        confidence.clarification_reason(score, assessment, has_evidence=has_evidence)
        is expected
    )


def test_local_deterministic_provider_does_not_require_api_key() -> None:
    provider = build_reasoning_provider(
        Settings(
            reasoning_provider="local-deterministic",
            llm_api_key=None,
        )
    )

    assert isinstance(provider, LocalSemanticReasoningProvider)
    assert provider.name == "local-semantic-v1"

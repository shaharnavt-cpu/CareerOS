"""Coverage for project identity resolution and reviewed enrichment."""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.enrichments import get_enrichment_service
from app.db.session import SessionLocal, engine
from app.main import app
from app.models import (
    CanonicalMemoryRecord,
    CareerMemoryEnrichment,
    DiagnosisResult,
    DiagnosisSession,
    ProofArtifact,
    ProofArtifactVersion,
    ReviewProposal,
    User,
)
from app.schemas.diagnosis import DiagnosisSessionCreateRequest
from app.schemas.enrichments import (
    EnrichmentCreateRequest,
    EnrichmentStatus,
    EnrichmentUpdateRequest,
    MemoryResolutionKind,
)
from app.schemas.knowledge import (
    EntityType,
    EvidenceReference,
    KnowledgeProposal,
    ReviewProposalType,
    SourceType,
)
from app.schemas.proof_artifacts import ProofArtifactCreateRequest
from app.services.career_diagnosis import CareerDiagnosisService
from app.services.memory_enrichment import (
    PARSE_QUALITY_WARNING,
    CareerMemoryEnrichmentService,
    EnrichmentStateError,
    ProjectEnrichmentExtractor,
)
from app.services.memory_identity import MemoryIdentityResolver
from app.services.proof_artifacts import ProofArtifactService
from app.services.review_repository import ReviewRepository

GAS_TITLE = "Gas Kinematics and 3D Galaxy Morphology Honors Capstone"
DETAIL = """Research question: Whether spectral and imaging data could be used to
study relationships between galaxy morphology and rotational velocity dispersion.
Data or inputs: Spectral data and imaging data.
Methods: Statistical analysis, Gaussian fitting, modeling, uncertainty and error
propagation, visualization, and technical communication.
Findings: The analysis found no clear trend, so the result was inconclusive.
Limitations: The available observations did not support a conclusive trend.
Outputs: Honors capstone poster and technical report.
"""


def _require_postgres() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")


def _seed_memory(
    user_id: uuid.UUID, *, decision: str = "APPROVED"
) -> uuid.UUID:
    proposal_id = f"gas-memory-{user_id}"
    with SessionLocal.begin() as session:
        session.add(
            User(
                id=user_id,
                clerk_user_id=f"enrichment-test-{user_id}",
                email=f"enrichment-test-{user_id}@example.invalid",
                display_name="Enrichment Test User",
            )
        )
        session.flush()
        session.add(
            ReviewProposal(
                id=proposal_id,
                user_id=user_id,
                proposal_type="PROJECT",
                entity_type="PROJECT",
                title=GAS_TITLE,
                identity_key=f"gas-{user_id}",
                proposal_data={"title": GAS_TITLE},
                decision=decision,
            )
        )
        session.flush()
        memory = CanonicalMemoryRecord(
            user_id=user_id,
            identity_key=f"gas-{user_id}",
            memory_type="PROJECT",
            title=GAS_TITLE,
            structured_fields={
                "title": GAS_TITLE,
                "summary": "Resume-level honors capstone project evidence.",
            },
            evidence_ids=["resume-evidence"],
            source_ids=["resume-source"],
            confidence=Decimal("0.900"),
            review_proposal_id=proposal_id,
        )
        session.add(memory)
        session.flush()
        return memory.id


def _cleanup_user(user_id: uuid.UUID) -> None:
    with SessionLocal.begin() as session:
        session.execute(
            delete(ProofArtifactVersion).where(
                ProofArtifactVersion.user_id == user_id
            )
        )
        session.execute(delete(ProofArtifact).where(ProofArtifact.user_id == user_id))
        session.execute(
            delete(DiagnosisResult).where(DiagnosisResult.user_id == user_id)
        )
        session.execute(
            delete(DiagnosisSession).where(DiagnosisSession.user_id == user_id)
        )
        session.execute(
            delete(CareerMemoryEnrichment).where(
                CareerMemoryEnrichment.user_id == user_id
            )
        )
        session.execute(
            delete(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.user_id == user_id
            )
        )
        session.execute(delete(ReviewProposal).where(ReviewProposal.user_id == user_id))
        session.execute(delete(User).where(User.id == user_id))


def _memory_record(title: str) -> CanonicalMemoryRecord:
    return CanonicalMemoryRecord(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        identity_key=str(uuid.uuid4()),
        memory_type="PROJECT",
        title=title,
        structured_fields={"title": title},
        evidence_ids=[],
        source_ids=[],
        confidence=Decimal("0.900"),
        review_proposal_id=f"proposal-{uuid.uuid4()}",
    )


def test_identity_resolver_matches_gas_alias_and_separates_unicorn() -> None:
    gas = _memory_record(GAS_TITLE)
    resolver = MemoryIdentityResolver()

    matched = resolver.resolve(
        title="Using Gas Kinematics to estimate 3D morphology of galaxies",
        text="Honors capstone using spectral and imaging data.",
        memories=[gas],
    )
    unicorn = resolver.resolve(
        title="The UNICORN Project",
        text="A separate GEVIP astronomy research project.",
        memories=[gas],
    )

    assert matched.resolution is MemoryResolutionKind.ENRICH_EXISTING
    assert matched.matched_memory_id == gas.id
    assert matched.confidence >= 0.72
    assert unicorn.resolution is MemoryResolutionKind.CREATE_NEW
    assert unicorn.matched_memory_id is None


def test_identity_resolver_reuses_exact_pending_proposal() -> None:
    pending = ReviewProposal(
        id=f"pending-{uuid.uuid4()}",
        user_id=uuid.uuid4(),
        proposal_type="PROJECT",
        entity_type="PROJECT",
        title="A Distinct Analytics Project",
        identity_key=str(uuid.uuid4()),
        proposal_data={
            "proposed_value": {"title": "A Distinct Analytics Project"}
        },
    )

    resolved = MemoryIdentityResolver().resolve(
        title="A Distinct Analytics Project",
        proposals=[pending],
    )

    assert resolved.resolution is MemoryResolutionKind.DUPLICATE_PROPOSAL
    assert resolved.matched_proposal_id == pending.id


def test_high_confidence_project_proposal_becomes_enrichment_not_duplicate() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    memory_id = _seed_memory(user_id)
    evidence_id = uuid.uuid4()
    proposal = KnowledgeProposal(
        id=f"duplicate-project-{user_id}",
        entity_type=EntityType.PROJECT,
        proposal_type=ReviewProposalType.PROJECT,
        proposed_value={
            "title": "Using Gas Kinematics to estimate 3D morphology of galaxies",
            "summary": DETAIL,
        },
        confidence=0.91,
        evidence=[
            EvidenceReference(
                source_id="manual-source",
                source_type=SourceType.MANUAL,
                title="Detailed capstone notes",
                excerpt=DETAIL,
                evidence_id=evidence_id,
            )
        ],
        reasoning_summary="Project title and detail identify an existing capstone.",
    )
    try:
        with SessionLocal.begin() as session:
            ReviewRepository().upsert_proposals(session, [proposal], user_id)
        second_evidence_id = uuid.uuid4()
        repeated = proposal.model_copy(
            update={
                "id": f"repeated-project-{user_id}",
                "evidence": [
                    EvidenceReference(
                        source_id="second-manual-source",
                        source_type=SourceType.MANUAL,
                        title="Additional capstone notes",
                        excerpt=DETAIL,
                        evidence_id=second_evidence_id,
                    )
                ],
            }
        )
        with SessionLocal.begin() as session:
            ReviewRepository().upsert_proposals(session, [repeated], user_id)

        with SessionLocal() as session:
            duplicate = session.get(ReviewProposal, proposal.id)
            repeated_duplicate = session.get(ReviewProposal, repeated.id)
            enrichments = session.scalars(
                select(CareerMemoryEnrichment).where(
                    CareerMemoryEnrichment.canonical_memory_id == memory_id
                )
            ).all()
            enrichment = enrichments[0]

        assert duplicate is None
        assert repeated_duplicate is None
        assert len(enrichments) == 1
        assert enrichment is not None
        assert enrichment.status == EnrichmentStatus.PROPOSED.value
        assert enrichment.evidence_ids == [
            str(evidence_id),
            str(second_evidence_id),
        ]
        serialized = json.dumps(enrichment.structured_enrichment)
        assert "project_type" not in serialized
        assert '\"project_name\"' not in serialized
        assert enrichment.structured_enrichment["findings_or_results"] == (
            "The analysis found no clear trend, so the result was inconclusive."
        )
        assert enrichment.identity_resolution["resolution"] == "ENRICH_EXISTING"
    finally:
        _cleanup_user(user_id)


def test_duplicate_proposal_can_be_converted_to_enrichment() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    memory_id = _seed_memory(user_id)
    evidence_id = uuid.uuid4()
    proposal = KnowledgeProposal(
        id=f"convert-project-{user_id}",
        entity_type=EntityType.PROJECT,
        proposal_type=ReviewProposalType.PROJECT,
        proposed_value={"title": "Gas Kinematics capstone", "summary": DETAIL},
        confidence=0.89,
        evidence=[
            EvidenceReference(
                source_id="manual-source",
                source_type=SourceType.MANUAL,
                title="Duplicate capstone draft",
                excerpt=DETAIL,
                evidence_id=evidence_id,
            )
        ],
        reasoning_summary="This draft repeats the approved capstone.",
    )
    try:
        with SessionLocal.begin() as session:
            session.add(
                ReviewProposal(
                    id=proposal.id,
                    user_id=user_id,
                    proposal_type="PROJECT",
                    entity_type="PROJECT",
                    title="Gas Kinematics capstone",
                    identity_key=f"convert-{user_id}",
                    proposal_data=proposal.model_dump(mode="json"),
                )
            )
        with SessionLocal() as session:
            converted = CareerMemoryEnrichmentService(
                user_id=user_id
            ).convert_proposal(session, memory_id, proposal.id)
        with SessionLocal() as session:
            duplicate = session.get(ReviewProposal, proposal.id)

        assert converted.status is EnrichmentStatus.PROPOSED
        assert converted.target_memory.id == memory_id
        assert converted.evidence_ids == [str(evidence_id)]
        assert duplicate is not None
        assert duplicate.decision == "REJECTED"
    finally:
        _cleanup_user(user_id)


def test_approve_enrichment_updates_memory_proof_and_diagnosis() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    memory_id = _seed_memory(user_id)
    enrichment_service = CareerMemoryEnrichmentService(user_id=user_id)
    try:
        with SessionLocal() as session:
            proposed = enrichment_service.create(
                session,
                memory_id,
                EnrichmentCreateRequest(enrichment_text=DETAIL),
            )
        assert proposed.structured_enrichment["tools_or_methods"] == [
            "statistical analysis",
            "Gaussian fitting",
            "modeling",
            "uncertainty and error propagation",
            "data visualization",
            "technical communication",
        ]
        assert ". using" not in proposed.structured_enrichment[
            "resume_bullet_claims"
        ][0]
        assert "collaborators_or_context" not in proposed.structured_enrichment
        assert proposed.structured_enrichment["role_specific_framing"] == (
            proposed.structured_enrichment["role_relevance"]
        )
        assert "Gaussian fitting" in proposed.structured_enrichment[
            "proof_artifact_summary"
        ]
        with SessionLocal() as session:
            approved = enrichment_service.update(
                session,
                proposed.id,
                EnrichmentUpdateRequest(status=EnrichmentStatus.APPROVED),
            )
        with SessionLocal() as session:
            memory = session.get(CanonicalMemoryRecord, memory_id)
            artifact = ProofArtifactService(user_id=user_id).create(
                session,
                ProofArtifactCreateRequest(
                    source_memory_id=memory_id,
                    target_role="Data Analytics / AI internship",
                ),
            )
        with SessionLocal() as session:
            diagnosis = CareerDiagnosisService(user_id=user_id).create_and_run(
                session,
                DiagnosisSessionCreateRequest(
                    target_role="Data Analytics / AI internship"
                ),
            )

        assert approved.status is EnrichmentStatus.APPROVED
        assert memory is not None
        assert memory.structured_fields["approved_enrichment_ids"] == [
            str(proposed.id)
        ]
        assert "Gaussian fitting" in artifact.latest_version.structured_sections[
            "method"
        ]
        assert "no clear overall trend" in artifact.latest_version.structured_sections[
            "outcome_or_insight"
        ].casefold()
        assert "conclusive trend" in artifact.latest_version.structured_sections[
            "limitations"
        ]
        assert "now has stronger proof" in diagnosis.result.recognition_gap
    finally:
        _cleanup_user(user_id)


def test_rejected_enrichment_does_not_affect_proof_artifacts() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    memory_id = _seed_memory(user_id)
    service = CareerMemoryEnrichmentService(user_id=user_id)
    try:
        with SessionLocal() as session:
            proposed = service.create(
                session,
                memory_id,
                EnrichmentCreateRequest(enrichment_text=DETAIL),
            )
        with SessionLocal() as session:
            service.update(
                session,
                proposed.id,
                EnrichmentUpdateRequest(status=EnrichmentStatus.REJECTED),
            )
        with SessionLocal() as session:
            memory = session.get(CanonicalMemoryRecord, memory_id)
            artifact = ProofArtifactService(user_id=user_id).create(
                session,
                ProofArtifactCreateRequest(
                    source_memory_id=memory_id,
                    target_role="Data Analytics internship",
                ),
            )

        assert memory is not None
        assert "approved_enrichment_ids" not in memory.structured_fields
        assert "gaussian" not in artifact.latest_version.content.casefold()
        assert "no clear trend" not in artifact.latest_version.content.casefold()
    finally:
        _cleanup_user(user_id)


def test_archiving_approved_enrichment_rebuilds_original_memory() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    memory_id = _seed_memory(user_id)
    service = CareerMemoryEnrichmentService(user_id=user_id)
    try:
        with SessionLocal.begin() as session:
            memory = session.get(CanonicalMemoryRecord, memory_id)
            assert memory is not None
            memory.structured_fields = {
                **memory.structured_fields,
                "warnings_not_to_claim": ["Preserve this original warning."],
            }
        with SessionLocal() as session:
            proposed = service.create(
                session,
                memory_id,
                EnrichmentCreateRequest(enrichment_text=DETAIL),
            )
        with SessionLocal() as session:
            service.update(
                session,
                proposed.id,
                EnrichmentUpdateRequest(status=EnrichmentStatus.APPROVED),
            )
        with SessionLocal() as session:
            service.update(
                session,
                proposed.id,
                EnrichmentUpdateRequest(status=EnrichmentStatus.ARCHIVED),
            )
        with SessionLocal() as session:
            memory = session.get(CanonicalMemoryRecord, memory_id)

        assert memory is not None
        assert "enriched_method" not in memory.structured_fields
        assert memory.structured_fields["warnings_not_to_claim"] == [
            "Preserve this original warning."
        ]
        assert memory.evidence_ids == ["resume-evidence"]
        assert memory.source_ids == ["resume-source"]
    finally:
        _cleanup_user(user_id)


def test_unapproved_memory_cannot_be_enriched() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    memory_id = _seed_memory(user_id, decision="REJECTED")
    try:
        with SessionLocal() as session, pytest.raises(EnrichmentStateError):
            CareerMemoryEnrichmentService(user_id=user_id).create(
                session,
                memory_id,
                EnrichmentCreateRequest(enrichment_text=DETAIL),
            )
    finally:
        _cleanup_user(user_id)


def test_duplicate_approved_enrichment_returns_actionable_409() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    memory_id = _seed_memory(user_id)
    service = CareerMemoryEnrichmentService(user_id=user_id)
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_enrichment_service] = lambda: service
    try:
        with SessionLocal() as session:
            proposed = service.create(
                session,
                memory_id,
                EnrichmentCreateRequest(enrichment_text=DETAIL),
            )
        with SessionLocal() as session:
            approved = service.update(
                session,
                proposed.id,
                EnrichmentUpdateRequest(status=EnrichmentStatus.APPROVED),
            )

        with TestClient(app) as client:
            duplicate = client.post(
                f"/api/career-memory/{memory_id}/enrichments",
                json={"enrichment_text": DETAIL},
            )

        assert duplicate.status_code == 409
        detail = duplicate.json()["detail"]
        assert detail["code"] == "DUPLICATE_ENRICHMENT"
        assert detail["message"] == (
            "This evidence already appears to be saved for this project. "
            "No duplicate enrichment was created."
        )
        assert detail["existing_enrichment_id"] == str(approved.id)
        assert detail["existing_status"] == EnrichmentStatus.APPROVED.value

        with SessionLocal() as session:
            records = session.scalars(
                select(CareerMemoryEnrichment).where(
                    CareerMemoryEnrichment.user_id == user_id,
                    CareerMemoryEnrichment.canonical_memory_id == memory_id,
                )
            ).all()
        assert len(records) == 1
        assert records[0].id == approved.id
        assert records[0].status == EnrichmentStatus.APPROVED.value
    finally:
        app.dependency_overrides = original_overrides
        _cleanup_user(user_id)


def test_low_detail_parse_warning_and_no_hallucinated_method() -> None:
    fields, warnings = ProjectEnrichmentExtractor().extract(
        "Data: spectral data.", GAS_TITLE
    )

    assert PARSE_QUALITY_WARNING in warnings
    assert fields["data_or_inputs"] == "spectral data."
    assert "tools_or_methods" not in fields
    assert "Gaussian fitting" not in str(fields)


def test_prose_parse_does_not_treat_project_type_as_output_or_method_as_limit() -> None:
    fields, _ = ProjectEnrichmentExtractor().extract(
        "Using Gas Kinematics to estimate the 3D morphology of galaxies, Honors "
        "Capstone Project. Goal: investigate whether spectral and imaging data "
        "reveal a relationship between galaxy morphology and rotational velocity "
        "dispersion. Methods: statistical analysis, Gaussian fitting, modeling, "
        "uncertainty/error propagation, and visualization. Result: no clear trend; "
        "the finding was inconclusive.",
        GAS_TITLE,
    )

    assert "outputs" not in fields
    assert fields["limitations"] == "no clear trend; the finding was inconclusive."
    assert fields["resume_bullet_claims"][0].startswith("Investigated whether")


def test_non_uncertainty_project_hooks_stay_source_specific() -> None:
    fields, _ = ProjectEnrichmentExtractor().extract(
        "Research question: How can a student resource make research opportunities "
        "easier to discover?\nMethods: Requirements gathering, information "
        "architecture, prototyping, and technical communication.\nFindings: The "
        "project produced a separate student-facing resource concept.",
        "The UNICORN Project",
    )

    assert fields["resume_bullet_claims"][0].startswith(
        "Explored a project question—How can"
    )
    assert "requirements gathering" in [
        item.casefold() for item in fields["skills_demonstrated"]
    ]
    assert "uncertainty" not in fields["role_relevance"].casefold()
    assert "uncertainty" not in fields["proof_artifact_angles"][0].casefold()

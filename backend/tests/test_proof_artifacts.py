"""Regression coverage for the deterministic Proof Artifact Builder."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.proof_artifacts import get_proof_artifact_service
from app.db.session import SessionLocal, engine
from app.main import app
from app.models import (
    CanonicalMemoryRecord,
    CareerFeedbackEvent,
    DiagnosisResult,
    DiagnosisSession,
    ListeningEvidence,
    ListeningSource,
    ProofArtifact,
    ProofArtifactVersion,
    ReviewProposal,
    User,
)
from app.schemas.diagnosis import (
    DiagnosisFocus,
    DiagnosisSessionCreateRequest,
    FeedbackEventCreateRequest,
    FeedbackEventStatus,
    FeedbackEventUpdateRequest,
)
from app.schemas.proof_artifacts import (
    ProofArtifactCreateRequest,
    ProofArtifactRegenerateRequest,
    ProofArtifactStatus,
    ProofArtifactType,
    ProofArtifactUpdateRequest,
    ProofArtifactVersionUpdateRequest,
    ProofReadinessLabel,
    ProofTargetAudience,
)
from app.services.career_diagnosis import (
    CareerDiagnosisService,
    CareerFeedbackService,
)
from app.services.proof_artifacts import (
    ProofArtifactNotFoundError,
    ProofArtifactService,
    ProofArtifactValidationError,
)

GAS_MEMORY_TITLE = "Gas Kinematics and 3D Galaxy Morphology Honors Capstone"
GAS_SOURCE_LABEL = "Honors capstone source packet"
GAS_EVIDENCE = (
    "Investigated gas kinematics and 3D galaxy morphology using spectral and "
    "imaging observations. Applied data analysis, statistical modeling, "
    "uncertainty and error propagation, and data visualization, then presented "
    "the technical findings clearly."
)


@dataclass(frozen=True)
class SeededMemory:
    memory_id: uuid.UUID
    proposal_id: str
    evidence_id: uuid.UUID | None
    source_id: uuid.UUID | None


def _require_postgres() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")


def _cleanup_user(user_id: uuid.UUID) -> None:
    """Delete tenant data in foreign-key-safe order."""

    with SessionLocal.begin() as session:
        session.execute(
            delete(ProofArtifactVersion).where(ProofArtifactVersion.user_id == user_id)
        )
        session.execute(delete(ProofArtifact).where(ProofArtifact.user_id == user_id))
        session.execute(
            delete(DiagnosisResult).where(DiagnosisResult.user_id == user_id)
        )
        session.execute(
            delete(DiagnosisSession).where(DiagnosisSession.user_id == user_id)
        )
        session.execute(
            delete(CareerFeedbackEvent).where(CareerFeedbackEvent.user_id == user_id)
        )
        session.execute(
            delete(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.user_id == user_id
            )
        )
        session.execute(delete(ReviewProposal).where(ReviewProposal.user_id == user_id))
        session.execute(
            delete(ListeningEvidence).where(ListeningEvidence.user_id == user_id)
        )
        session.execute(
            delete(ListeningSource).where(ListeningSource.user_id == user_id)
        )
        session.execute(delete(User).where(User.id == user_id))


def _seed_gas_memory(user_id: uuid.UUID, *, with_evidence: bool = True) -> SeededMemory:
    proposal_id = f"approved-gas-capstone-{user_id}"
    evidence_id: uuid.UUID | None = None
    source_id: uuid.UUID | None = None
    with SessionLocal.begin() as session:
        session.add(
            User(
                id=user_id,
                clerk_user_id=f"proof-artifact-test-{user_id}",
                email=f"proof-artifact-test-{user_id}@example.invalid",
                display_name="Proof Artifact Test User",
            )
        )
        session.flush()

        if with_evidence:
            source = ListeningSource(
                user_id=user_id,
                source_type="GENERIC_DOCUMENT",
                label=GAS_SOURCE_LABEL,
                original_filename="honors-capstone.txt",
                media_type="text/plain",
                raw_text=GAS_EVIDENCE,
                source_metadata={"fixture": "proof-artifact"},
                provenance={"ingestion": "test"},
                content_hash=f"proof-source-{user_id}",
                adapter_version="test-v1",
                status="READY",
            )
            session.add(source)
            session.flush()
            source_id = source.id
            evidence = ListeningEvidence(
                user_id=user_id,
                source_id=source.id,
                source_type="GENERIC_DOCUMENT",
                raw_excerpt=GAS_EVIDENCE,
                normalized_excerpt=GAS_EVIDENCE,
                excerpt_hash=f"proof-evidence-{user_id}",
                category="PROJECT",
                confidence=Decimal("0.940"),
                location={"section": "Honors capstone"},
                provenance={"source_label": GAS_SOURCE_LABEL},
            )
            session.add(evidence)
            session.flush()
            evidence_id = evidence.id

        session.add(
            ReviewProposal(
                id=proposal_id,
                user_id=user_id,
                proposal_type="PROJECT",
                entity_type="PROJECT",
                title=GAS_MEMORY_TITLE,
                identity_key=f"gas-capstone-{user_id}",
                proposal_data={"title": GAS_MEMORY_TITLE},
                decision="APPROVED",
            )
        )
        session.flush()
        memory = CanonicalMemoryRecord(
            user_id=user_id,
            identity_key=f"gas-capstone-{user_id}",
            memory_type="PROJECT",
            title=GAS_MEMORY_TITLE,
            structured_fields={
                "title": GAS_MEMORY_TITLE,
                "project_type": "Honors Capstone",
                "summary": (
                    "Investigated how spectral and imaging observations supported "
                    "claims about gas kinematics and galaxy morphology."
                ),
                "problem": (
                    "Test whether observable spectral and imaging patterns supported "
                    "claims about galaxy structure."
                ),
                "data": ["spectral observations", "imaging observations"],
                "methods": [
                    "data analysis",
                    "statistical modeling",
                    "uncertainty and error propagation",
                    "data visualization",
                    "technical presentation",
                ],
            },
            evidence_ids=[str(evidence_id)] if evidence_id else [],
            source_ids=[str(source_id)] if source_id else [],
            confidence=Decimal("0.920"),
            review_proposal_id=proposal_id,
        )
        session.add(memory)
        session.flush()
        memory_id = memory.id

    return SeededMemory(
        memory_id=memory_id,
        proposal_id=proposal_id,
        evidence_id=evidence_id,
        source_id=source_id,
    )


def _seed_rejected_only(user_id: uuid.UUID) -> None:
    with SessionLocal.begin() as session:
        session.add(
            User(
                id=user_id,
                clerk_user_id=f"proof-rejected-test-{user_id}",
                email=f"proof-rejected-test-{user_id}@example.invalid",
                display_name="Rejected Proof Test User",
            )
        )
        session.flush()
        session.add(
            ReviewProposal(
                id=f"rejected-gas-capstone-{user_id}",
                user_id=user_id,
                proposal_type="PROJECT",
                entity_type="PROJECT",
                title="Rejected analytics project",
                identity_key=f"rejected-project-{user_id}",
                proposal_data={"title": "Rejected analytics project"},
                decision="REJECTED",
            )
        )


def _replace_memory_details(
    user_id: uuid.UUID,
    memory_id: uuid.UUID,
    *,
    title: str,
    structured_fields: dict[str, object],
    evidence_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
) -> None:
    """Replace approved fixture details for focused deterministic-rule tests."""

    with SessionLocal.begin() as session:
        memory = session.scalar(
            select(CanonicalMemoryRecord).where(
                CanonicalMemoryRecord.id == memory_id,
                CanonicalMemoryRecord.user_id == user_id,
            )
        )
        assert memory is not None
        memory.title = title
        memory.structured_fields = structured_fields
        if evidence_ids is not None:
            memory.evidence_ids = evidence_ids
        if source_ids is not None:
            memory.source_ids = source_ids


def _create_request(
    memory_id: uuid.UUID,
    *,
    diagnosis_result_id: uuid.UUID | None = None,
) -> ProofArtifactCreateRequest:
    return ProofArtifactCreateRequest(
        source_memory_id=memory_id,
        target_role="Data Analytics / AI internship",
        target_audience=ProofTargetAudience.APPLICATION_UPLOAD,
        artifact_type=ProofArtifactType.CASE_STUDY,
        source_diagnosis_result_id=diagnosis_result_id,
    )


def test_create_case_study_uses_approved_gas_memory_without_inventing_python() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            eligible = service.list_eligible_memories(session)
            artifact = service.create(session, _create_request(seeded.memory_id))

        assert len(eligible) == 1
        assert eligible[0].id == seeded.memory_id
        assert eligible[0].evidence_ids == [str(seeded.evidence_id)]
        assert eligible[0].source_labels == [GAS_SOURCE_LABEL]

        version = artifact.latest_version
        assert artifact.status is ProofArtifactStatus.DRAFT
        assert artifact.source_memory_id == seeded.memory_id
        assert artifact.version_count == 1
        assert version.version_number == 1
        assert version.title == (
            "Data Analytics Case Study: Modeling Galaxy Morphology from Spectral "
            "and Imaging Data"
        )
        assert "Data Analytics / AI internship" in version.claim
        assert "analyze complex data" in version.claim
        assert "reason about uncertainty" in version.claim
        assert "Python" not in json.dumps(version.model_dump(mode="json"))
        assert version.evidence_ids == [str(seeded.evidence_id)]
        assert version.evidence_references[0].evidence_id == str(seeded.evidence_id)
        assert version.evidence_references[0].source_label == GAS_SOURCE_LABEL
        assert version.evidence_references[0].excerpt == GAS_EVIDENCE
        assert version.structured_sections["evidence_used"][0]["evidence_id"] == str(
            seeded.evidence_id
        )
        assert version.readiness_score > 0
        assert version.readiness_label is ProofReadinessLabel.STRONG_DRAFT
        assert any("No documented outcome" in warning for warning in version.warnings)
        assert any(
            "No approved performance metric" in warning for warning in version.warnings
        )
        sections = version.structured_sections
        assert sections["problem"] == (
            "The project tested how spectral and imaging observations could be used "
            "to study relationships between galaxy morphology and kinematics."
        )
        assert sections["context"].startswith(
            "Honors capstone / Gas Kinematics project."
        )
        assert "UNICORN" not in sections["context"]
        assert "statistical modeling" in sections["method"]
        assert "uncertainty and error propagation" in sections["method"]
        assert "data visualization" in sections["method"]
        assert "technical communication" in sections["method"]
        assert "repeatable analytical workflow" in sections["outcome_or_insight"]
        assert "supports decision-making" in sections["what_this_proves"]
        assert "do not claim" not in sections["limitations"].casefold()
        assert str(seeded.evidence_id) not in version.content
        assert "CaseStudy" not in version.content
        assert {
            "resume_bullets",
            "cover_letter_paragraph",
            "outreach_blurb",
            "interview_answer",
            "github_readme_outline",
        }.issubset(version.supporting_variants)
        variants = json.dumps(version.supporting_variants, ensure_ascii=False)
        assert "State the approved problem" not in variants
        assert "Name only source-backed inputs" not in variants
        assert "Explain the approved analytical process" not in variants
        assert "approved Career Memory" not in variants
    finally:
        _cleanup_user(user_id)


def test_rejected_or_missing_memory_cannot_be_used() -> None:
    _require_postgres()
    rejected_user_id = uuid.uuid4()
    missing_user_id = uuid.uuid4()
    _seed_rejected_only(rejected_user_id)
    _seed_gas_memory(missing_user_id)
    try:
        with SessionLocal() as session:
            with pytest.raises(ProofArtifactValidationError) as rejected_error:
                ProofArtifactService(user_id=rejected_user_id).create(
                    session, _create_request(uuid.uuid4())
                )
        assert str(rejected_error.value) == (
            "Approve career memories before building a proof artifact."
        )

        with SessionLocal() as session:
            with pytest.raises(ProofArtifactNotFoundError) as missing_error:
                ProofArtifactService(user_id=missing_user_id).create(
                    session, _create_request(uuid.uuid4())
                )
        assert str(missing_error.value) == "Approved source memory not found."
    finally:
        _cleanup_user(rejected_user_id)
        _cleanup_user(missing_user_id)


def test_memory_without_evidence_creates_partial_needs_evidence_draft() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id, with_evidence=False)
    try:
        with SessionLocal() as session:
            artifact = ProofArtifactService(user_id=user_id).create(
                session, _create_request(seeded.memory_id)
            )

        version = artifact.latest_version
        assert version.evidence_ids == []
        assert version.evidence_references == []
        assert version.readiness_score <= 0.39
        assert version.readiness_label is ProofReadinessLabel.NEEDS_EVIDENCE
        assert any("partial draft" in warning for warning in version.warnings)
    finally:
        _cleanup_user(user_id)


def test_diagnosis_link_uses_approved_outcome_and_excludes_archived_outcome() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    feedback_service = CareerFeedbackService(user_id=user_id)
    diagnosis_service = CareerDiagnosisService(user_id=user_id)
    proof_service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            approved = feedback_service.create(
                session,
                FeedbackEventCreateRequest(
                    raw_note=(
                        "The JSOM eLearning Recording Studio Assistant cover letter "
                        "led to an interview invite."
                    ),
                    related_memory_ids=[seeded.memory_id],
                    status=FeedbackEventStatus.APPROVED,
                ),
            )
            archived = feedback_service.create(
                session,
                FeedbackEventCreateRequest(
                    raw_note=(
                        "The Black Box AI Engineer Intern cover letter led to an "
                        "interview invite."
                    ),
                    related_memory_ids=[seeded.memory_id],
                    status=FeedbackEventStatus.ARCHIVED,
                ),
            )
            diagnosis = diagnosis_service.create_and_run(
                session,
                DiagnosisSessionCreateRequest(
                    target_role="Data Analytics / AI internship",
                    selected_focus=DiagnosisFocus.ANALYTICS,
                ),
            )
            artifact = proof_service.create(
                session,
                _create_request(
                    seeded.memory_id,
                    diagnosis_result_id=diagnosis.result.id,
                ),
            )

        version = artifact.latest_version
        assert artifact.source_diagnosis_result_id == diagnosis.result.id
        assert version.outcome_signal_ids == [str(approved.id)]
        assert str(archived.id) not in version.outcome_signal_ids
        assert len(version.outcome_signals) == 1
        assert version.outcome_signals[0].feedback_event_id == approved.id
        assert (
            "JSOM eLearning Recording Studio Assistant"
            in version.outcome_signals[0].summary
        )
        assert "interview invite" in version.outcome_signals[0].summary
        assert "not canonical proof" in version.outcome_signals[0].caveat
        assert "causality" in version.outcome_signals[0].caveat
        assert any("strategy signal" in warning for warning in version.warnings)
        serialized = json.dumps(version.model_dump(mode="json"))
        assert "Black Box AI Engineer Intern" not in serialized
        assert "interview invite" not in version.content.casefold()
    finally:
        _cleanup_user(user_id)


def test_regenerate_adds_a_version_and_preserves_version_one() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            created = service.create(session, _create_request(seeded.memory_id))
            original_content = created.latest_version.content
            regenerated = service.regenerate(
                session,
                created.id,
                ProofArtifactRegenerateRequest(
                    target_role="AI / Automation internship",
                    target_audience=ProofTargetAudience.GITHUB,
                    artifact_type=ProofArtifactType.GITHUB_README,
                ),
            )

        assert regenerated.version_count == 2
        assert regenerated.latest_version.version_number == 2
        assert regenerated.artifact_type is ProofArtifactType.GITHUB_README
        assert regenerated.target_audience is ProofTargetAudience.GITHUB
        assert regenerated.target_role == "AI / Automation internship"
        assert regenerated.status is ProofArtifactStatus.DRAFT
        assert regenerated.latest_version.content.startswith("# ")

        with SessionLocal() as session:
            versions = session.scalars(
                select(ProofArtifactVersion)
                .where(ProofArtifactVersion.artifact_id == created.id)
                .order_by(ProofArtifactVersion.version_number)
            ).all()
        assert [version.version_number for version in versions] == [1, 2]
        assert versions[0].content == original_content
        assert versions[1].content == regenerated.latest_version.content
    finally:
        _cleanup_user(user_id)


def test_edited_version_persists_and_warns_about_unsupported_numeric_claim() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    edited_content = "This project improved employer response by 42%."
    try:
        with SessionLocal() as session:
            created = service.create(session, _create_request(seeded.memory_id))
            edited = service.update_version(
                session,
                created.id,
                created.latest_version.id,
                ProofArtifactVersionUpdateRequest(
                    title="Edited analytics case study",
                    claim="A user-edited claim that still requires evidence review.",
                    content=edited_content,
                ),
            )

        assert edited.version_count == 1
        assert edited.title == "Edited analytics case study"
        assert edited.latest_version.title == "Edited analytics case study"
        assert edited.latest_version.content == edited_content
        assert edited.latest_version.readiness_score <= 0.59
        assert edited.latest_version.readiness_label is ProofReadinessLabel.DRAFTABLE
        numeric_warning = next(
            warning
            for warning in edited.latest_version.warnings
            if warning.startswith("Edited text contains numeric claims")
        )
        assert "42%" in numeric_warning

        with SessionLocal() as session:
            persisted = service.get(session, created.id)
        assert persisted.latest_version.content == edited_content
        assert numeric_warning in persisted.latest_version.warnings
    finally:
        _cleanup_user(user_id)


def test_safe_edit_preserves_internal_evidence_link_without_exposing_id() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            created = service.create(session, _create_request(seeded.memory_id))
            edited = service.update_version(
                session,
                created.id,
                created.latest_version.id,
                ProofArtifactVersionUpdateRequest(
                    content=(
                        f"{created.latest_version.content}\n\n"
                        "Reviewed for clarity in this work sample."
                    )
                ),
            )

        assert "## Evidence used" in edited.latest_version.content
        assert seeded.evidence_id is not None
        assert str(seeded.evidence_id) not in edited.latest_version.content
        assert edited.latest_version.evidence_ids == [str(seeded.evidence_id)]
        assert not any(
            warning.startswith("Edited text contains numeric claims")
            for warning in edited.latest_version.warnings
        )
        assert edited.latest_version.readiness_label is ProofReadinessLabel.STRONG_DRAFT
    finally:
        _cleanup_user(user_id)


def test_artifact_metadata_and_ready_status_are_durable() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            created = service.create(session, _create_request(seeded.memory_id))
            updated = service.update(
                session,
                created.id,
                ProofArtifactUpdateRequest(
                    title="Application-ready analytics work sample",
                    status=ProofArtifactStatus.READY,
                ),
            )

        assert updated.title == "Application-ready analytics work sample"
        assert updated.target_audience is ProofTargetAudience.APPLICATION_UPLOAD
        assert updated.status is ProofArtifactStatus.READY
        assert updated.version_count == 1

        with SessionLocal() as session:
            persisted = service.get(session, created.id)
        assert persisted.status is ProofArtifactStatus.READY
        assert persisted.title == "Application-ready analytics work sample"
    finally:
        _cleanup_user(user_id)


def test_local_deterministic_builder_needs_no_llm_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _require_postgres()
    monkeypatch.setenv("REASONING_PROVIDER", "local-deterministic")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    try:
        with SessionLocal() as session:
            artifact = ProofArtifactService(user_id=user_id).create(
                session, _create_request(seeded.memory_id)
            )

        assert artifact.latest_version.structured_sections["generator_version"] == (
            "local-deterministic-proof-v0"
        )
        assert artifact.latest_version.content
    finally:
        _cleanup_user(user_id)


def test_proof_artifact_api_exposes_memory_crud_and_version_shapes() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_proof_artifact_service] = lambda: service
    try:
        with TestClient(app) as client:
            memories = client.get("/api/proof-artifacts/eligible-memories")
            created = client.post(
                "/api/proof-artifacts",
                json={
                    "source_memory_id": str(seeded.memory_id),
                    "target_role": "Data Analytics / AI internship",
                    "target_audience": "APPLICATION_UPLOAD",
                    "artifact_type": "CASE_STUDY",
                },
            )
            assert memories.status_code == 200
            assert memories.json()[0]["id"] == str(seeded.memory_id)
            assert memories.json()[0]["source_labels"] == [GAS_SOURCE_LABEL]
            assert created.status_code == 201
            artifact_id = created.json()["id"]
            version_id = created.json()["latest_version"]["id"]

            fetched = client.get(f"/api/proof-artifacts/{artifact_id}")
            listed = client.get("/api/proof-artifacts")
            edited = client.patch(
                f"/api/proof-artifacts/{artifact_id}/versions/{version_id}",
                json={"content": "Edited case study without a new metric."},
            )
            regenerated = client.post(
                f"/api/proof-artifacts/{artifact_id}/regenerate",
                json={"target_audience": "PORTFOLIO"},
            )
            ready = client.patch(
                f"/api/proof-artifacts/{artifact_id}",
                json={"status": "READY"},
            )

        assert fetched.status_code == 200
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == artifact_id
        assert edited.status_code == 200
        assert edited.json()["latest_version"]["content"] == (
            "Edited case study without a new metric."
        )
        assert regenerated.status_code == 200
        assert regenerated.json()["version_count"] == 2
        assert regenerated.json()["latest_version"]["version_number"] == 2
        assert ready.status_code == 200
        assert ready.json()["status"] == "READY"
        assert "evidence_references" in created.json()["latest_version"]
        assert "outcome_signals" in created.json()["latest_version"]
        assert "supporting_variants" in created.json()["latest_version"]
    finally:
        app.dependency_overrides = original_overrides
        _cleanup_user(user_id)


def test_foreign_evidence_never_leaks_or_counts_toward_readiness() -> None:
    _require_postgres()
    owner_id = uuid.uuid4()
    foreign_user_id = uuid.uuid4()
    owner = _seed_gas_memory(owner_id, with_evidence=False)
    foreign = _seed_gas_memory(foreign_user_id)
    assert foreign.evidence_id is not None
    assert foreign.source_id is not None
    _replace_memory_details(
        owner_id,
        owner.memory_id,
        title="Operations planning project",
        structured_fields={
            "title": "Operations planning project",
            "summary": "Documented a planning workflow for a student organization.",
        },
        evidence_ids=[str(foreign.evidence_id)],
        source_ids=[str(foreign.source_id)],
    )
    try:
        with SessionLocal() as session:
            artifact = ProofArtifactService(user_id=owner_id).create(
                session, _create_request(owner.memory_id)
            )

        version = artifact.latest_version
        serialized = json.dumps(version.model_dump(mode="json"))
        assert GAS_EVIDENCE not in serialized
        assert all(
            reference.excerpt is None for reference in version.evidence_references
        )
        assert (
            "statistical modeling"
            not in version.structured_sections["skills_demonstrated"]
        )
        assert version.readiness_score <= 0.39
        assert version.readiness_label is ProofReadinessLabel.NEEDS_EVIDENCE
    finally:
        _cleanup_user(owner_id)
        _cleanup_user(foreign_user_id)


def test_dangling_evidence_id_does_not_count_toward_readiness() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id, with_evidence=False)
    _replace_memory_details(
        user_id,
        seeded.memory_id,
        title="Student operations planning project",
        structured_fields={
            "title": "Student operations planning project",
            "summary": "Documented a planning workflow.",
        },
        evidence_ids=[str(uuid.uuid4())],
        source_ids=[str(uuid.uuid4())],
    )
    try:
        with SessionLocal() as session:
            artifact = ProofArtifactService(user_id=user_id).create(
                session, _create_request(seeded.memory_id)
            )

        assert artifact.latest_version.readiness_score <= 0.39
        assert (
            artifact.latest_version.readiness_label
            is ProofReadinessLabel.NEEDS_EVIDENCE
        )
    finally:
        _cleanup_user(user_id)


def test_saved_artifact_remains_readable_when_source_approval_is_withdrawn() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            created = service.create(session, _create_request(seeded.memory_id))

        with SessionLocal.begin() as session:
            proposal = session.get(ReviewProposal, seeded.proposal_id)
            assert proposal is not None
            proposal.decision = "PENDING_REVIEW"

        with SessionLocal() as session:
            fetched = service.get(session, created.id)
            listed = service.list(session)

        assert fetched.id == created.id
        assert fetched.latest_version.content == created.latest_version.content
        assert created.id in {artifact.id for artifact in listed}

        with SessionLocal() as session:
            with pytest.raises(ProofArtifactValidationError):
                service.regenerate(
                    session, created.id, ProofArtifactRegenerateRequest()
                )
    finally:
        _cleanup_user(user_id)


def test_target_role_and_audience_changes_require_regeneration() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            created = service.create(session, _create_request(seeded.memory_id))

        with SessionLocal() as session:
            with pytest.raises(ProofArtifactValidationError):
                service.update(
                    session,
                    created.id,
                    ProofArtifactUpdateRequest(
                        target_role="Retail operations internship",
                        target_audience=ProofTargetAudience.PORTFOLIO,
                    ),
                )

        with SessionLocal() as session:
            persisted = service.get(session, created.id)
        assert persisted.target_role == created.target_role
        assert persisted.target_audience is created.target_audience
        assert persisted.latest_version.content == created.latest_version.content
    finally:
        _cleanup_user(user_id)


def test_only_latest_proof_artifact_version_can_be_edited() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            created = service.create(session, _create_request(seeded.memory_id))
            version_one_id = created.latest_version.id
            regenerated = service.regenerate(
                session,
                created.id,
                ProofArtifactRegenerateRequest(target_role="Analytics internship"),
            )

        with SessionLocal() as session:
            with pytest.raises(ProofArtifactValidationError):
                service.update_version(
                    session,
                    created.id,
                    version_one_id,
                    ProofArtifactVersionUpdateRequest(title="Stale version title"),
                )

        with SessionLocal() as session:
            persisted = service.get(session, created.id)
        assert persisted.title == regenerated.title
        assert persisted.latest_version.id == regenerated.latest_version.id
        assert persisted.latest_version.version_number == 2
    finally:
        _cleanup_user(user_id)


def test_retail_target_is_not_classified_as_ai() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id, with_evidence=False)
    _replace_memory_details(
        user_id,
        seeded.memory_id,
        title="Retail customer service analysis",
        structured_fields={
            "title": "Retail customer service analysis",
            "summary": "Analyzed service patterns and documented findings.",
        },
    )
    request = _create_request(seeded.memory_id).model_copy(
        update={"target_role": "Retail operations internship"}
    )
    try:
        with SessionLocal() as session:
            artifact = ProofArtifactService(user_id=user_id).create(session, request)

        assert "AI / Automation" not in artifact.latest_version.title
    finally:
        _cleanup_user(user_id)


def test_generic_modeling_is_not_promoted_to_statistical_modeling() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id, with_evidence=False)
    _replace_memory_details(
        user_id,
        seeded.memory_id,
        title="Product prototype project",
        structured_fields={
            "title": "Product prototype project",
            "summary": "Created a 3D modeling workflow and documented the prototype.",
        },
    )
    request = _create_request(seeded.memory_id).model_copy(
        update={"target_role": "Product design internship"}
    )
    try:
        with SessionLocal() as session:
            artifact = ProofArtifactService(user_id=user_id).create(session, request)

        skills = artifact.latest_version.structured_sections["skills_demonstrated"]
        assert "statistical modeling" not in skills
    finally:
        _cleanup_user(user_id)


def test_special_galaxy_title_requires_galaxy_evidence() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id, with_evidence=False)
    memory_title = "Materials inspection study"
    _replace_memory_details(
        user_id,
        seeded.memory_id,
        title=memory_title,
        structured_fields={
            "title": memory_title,
            "summary": "Compared spectral and imaging data for materials inspection.",
        },
    )
    request = _create_request(seeded.memory_id).model_copy(
        update={"target_role": "Data analytics internship"}
    )
    try:
        with SessionLocal() as session:
            artifact = ProofArtifactService(user_id=user_id).create(session, request)

        assert artifact.latest_version.title != (
            "Data Analytics Case Study: Modeling Galaxy Morphology from Spectral "
            "and Imaging Data"
        )
        assert memory_title in artifact.latest_version.title
    finally:
        _cleanup_user(user_id)


def test_rendered_case_study_uses_readable_evidence_without_internal_id() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    assert seeded.evidence_id is not None
    try:
        with SessionLocal() as session:
            artifact = ProofArtifactService(user_id=user_id).create(
                session, _create_request(seeded.memory_id)
            )

        content = artifact.latest_version.content
        assert "## Evidence used" in content
        assert GAS_SOURCE_LABEL in content
        assert "Project scope" in content
        assert "Analytical method" in content
        assert str(seeded.evidence_id) not in content
        assert artifact.latest_version.evidence_ids == [str(seeded.evidence_id)]
        assert artifact.latest_version.evidence_references[0].evidence_id == str(
            seeded.evidence_id
        )
    finally:
        _cleanup_user(user_id)


def test_velocity_dispersion_problem_is_polished_when_source_backed() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id, with_evidence=False)
    _replace_memory_details(
        user_id,
        seeded.memory_id,
        title=GAS_MEMORY_TITLE,
        structured_fields={
            "title": GAS_MEMORY_TITLE,
            "summary": (
                "Studied galaxy morphology and rotational velocity dispersion "
                "using spectral and imaging data."
            ),
            "methods": [
                "statistical analysis",
                "modeling",
                "uncertainty and error propagation",
                "communicated technical findings",
            ],
        },
    )
    try:
        with SessionLocal() as session:
            artifact = ProofArtifactService(user_id=user_id).create(
                session, _create_request(seeded.memory_id)
            )

        assert artifact.latest_version.structured_sections["problem"] == (
            "The project tested whether spectral and imaging data could be used to "
            "study relationships between galaxy morphology and rotational velocity "
            "dispersion."
        )
        method = artifact.latest_version.structured_sections["method"]
        assert "statistical analysis" in method
        assert "modeling" in method
        assert "uncertainty and error propagation" in method
        assert "technical communication" in method
        assert "statistical modeling" not in method
    finally:
        _cleanup_user(user_id)


def test_legacy_user_facing_text_hides_internal_ids_and_placeholders() -> None:
    evidence_id = uuid.uuid4()
    sections = {
        "problem": "A documented problem.",
        "data_or_inputs": "Documented inputs.",
        "method": "A documented method.",
        "outcome_or_insight": "A documented takeaway.",
        "limitations": "A concise limitation.",
        "what_this_proves": "A transferable capability.",
    }
    legacy = (
        f"# Data Analytics CaseStudy\n\n- Source (evidence {evidence_id})\n\n"
        f"Evidence ID: {evidence_id}\n\nState the approved problem in one paragraph."
    )

    cleaned = ProofArtifactService._clean_user_facing_text(legacy, sections)

    assert "Case Study" in cleaned
    assert "CaseStudy" not in cleaned
    assert str(evidence_id) not in cleaned
    assert "Evidence ID" not in cleaned
    assert "A documented problem." in cleaned


def test_corrected_feedback_wins_over_stale_diagnosis_snapshot() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    feedback_service = CareerFeedbackService(user_id=user_id)
    diagnosis_service = CareerDiagnosisService(user_id=user_id)
    proof_service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            feedback = feedback_service.create(
                session,
                FeedbackEventCreateRequest(
                    raw_note=(
                        "The Black Box AI Engineer Intern cover letter led to an "
                        "interview invite."
                    ),
                    related_memory_ids=[seeded.memory_id],
                    status=FeedbackEventStatus.APPROVED,
                ),
            )
            diagnosis = diagnosis_service.create_and_run(
                session,
                DiagnosisSessionCreateRequest(
                    target_role="Data Analytics / AI internship",
                    selected_focus=DiagnosisFocus.ANALYTICS,
                ),
            )
            feedback_service.update(
                session,
                feedback.id,
                FeedbackEventUpdateRequest(
                    raw_note=(
                        "The JSOM eLearning Recording Studio Assistant cover letter "
                        "led to an interview invite."
                    )
                ),
            )
            artifact = proof_service.create(
                session,
                _create_request(
                    seeded.memory_id,
                    diagnosis_result_id=diagnosis.result.id,
                ),
            )

        serialized = json.dumps(
            artifact.latest_version.outcome_signals[0].model_dump(mode="json")
        )
        assert "JSOM eLearning Recording Studio Assistant" in serialized
        assert "Black Box AI Engineer Intern" not in serialized
    finally:
        _cleanup_user(user_id)


def test_unsupported_numeric_warning_persists_across_partial_edits() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_gas_memory(user_id)
    service = ProofArtifactService(user_id=user_id)
    try:
        with SessionLocal() as session:
            created = service.create(session, _create_request(seeded.memory_id))
            warned = service.update_version(
                session,
                created.id,
                created.latest_version.id,
                ProofArtifactVersionUpdateRequest(
                    claim="This project improved employer response by 42%."
                ),
            )
            persisted = service.update_version(
                session,
                created.id,
                created.latest_version.id,
                ProofArtifactVersionUpdateRequest(
                    content="A clean narrative edit without a metric."
                ),
            )

        assert any(
            "42%" in warning and warning.startswith("Edited text contains numeric")
            for warning in warned.latest_version.warnings
        )
        assert any(
            "42%" in warning and warning.startswith("Edited text contains numeric")
            for warning in persisted.latest_version.warnings
        )
        assert persisted.latest_version.readiness_score <= 0.59
        assert persisted.latest_version.readiness_label is ProofReadinessLabel.DRAFTABLE
    finally:
        _cleanup_user(user_id)

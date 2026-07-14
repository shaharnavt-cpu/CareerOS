"""Regression coverage for the deterministic Career Memory compiler."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import delete, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal, engine
from app.models import (
    CanonicalMemoryRecord,
    CareerFeedbackEvent,
    CareerMemoryEnrichment,
    ListeningEvidence,
    ListeningSource,
    ProofArtifact,
    ProofArtifactVersion,
    ReviewProposal,
    User,
)
from app.schemas.career_memory import CompiledCareerMemoryProfile
from app.schemas.proof_artifacts import ProofArtifactCreateRequest
from app.services.career_memory_compiler import CareerMemoryCompiler
from app.services.proof_artifacts import ProofArtifactService

GAS_TITLE = "Gas Kinematics and 3D Galaxy Morphology Honors Capstone"
UNICORN_TITLE = "The UNICORN Project"
SPARSE_TITLE = "Sparse Instrumentation Project Note"


@dataclass(frozen=True)
class SeededCompilerMemory:
    gas_memory_id: uuid.UUID
    unicorn_memory_id: uuid.UUID
    sparse_memory_id: uuid.UUID
    gas_approved_enrichment_id: uuid.UUID
    unicorn_approved_enrichment_id: uuid.UUID
    excluded_enrichment_ids: tuple[uuid.UUID, ...]
    approved_feedback_id: uuid.UUID
    archived_feedback_id: uuid.UUID


def _require_postgres() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")


def _cleanup_user(user_id: uuid.UUID) -> None:
    """Delete compiler fixture data in foreign-key-safe order."""

    with SessionLocal.begin() as session:
        session.execute(
            delete(ProofArtifactVersion).where(ProofArtifactVersion.user_id == user_id)
        )
        session.execute(delete(ProofArtifact).where(ProofArtifact.user_id == user_id))
        session.execute(
            delete(CareerFeedbackEvent).where(CareerFeedbackEvent.user_id == user_id)
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
        session.execute(
            delete(ListeningEvidence).where(ListeningEvidence.user_id == user_id)
        )
        session.execute(
            delete(ListeningSource).where(ListeningSource.user_id == user_id)
        )
        session.execute(delete(User).where(User.id == user_id))


def _identity_resolution(memory_id: uuid.UUID, title: str) -> dict[str, Any]:
    return {
        "resolution": "ENRICH_EXISTING",
        "confidence": 1.0,
        "matched_memory_id": str(memory_id),
        "matched_memory_title": title,
        "matched_proposal_id": None,
        "reasons": ["The user explicitly selected this approved Career Memory."],
        "evidence_ids": [],
        "recommended_review_action": "CREATE_ENRICHMENT",
    }


def _enrichment(
    *,
    user_id: uuid.UUID,
    memory_id: uuid.UUID,
    memory_title: str,
    status: str,
    structured: dict[str, Any],
    source_id: uuid.UUID | None = None,
    source_label: str | None = None,
    evidence_ids: list[str] | None = None,
) -> CareerMemoryEnrichment:
    return CareerMemoryEnrichment(
        user_id=user_id,
        canonical_memory_id=memory_id,
        source_id=source_id,
        source_label=source_label or "Reviewed project notes",
        status=status,
        enrichment_type="PROJECT_FULL_ENRICHMENT",
        structured_enrichment=structured,
        evidence_ids=evidence_ids or [],
        confidence=Decimal("0.930"),
        reasoning="Project details were explicitly reviewed for this memory.",
        identity_resolution=_identity_resolution(memory_id, memory_title),
        warnings=[],
    )


def _seed_compiler_memories(user_id: uuid.UUID) -> SeededCompilerMemory:
    with SessionLocal.begin() as session:
        session.add(
            User(
                id=user_id,
                clerk_user_id=f"compiler-test-{user_id}",
                email=f"compiler-test-{user_id}@example.invalid",
                display_name="Compiler Test User",
            )
        )
        session.flush()

        gas_source = ListeningSource(
            user_id=user_id,
            source_type="MANUAL",
            label="Gas capstone source packet",
            raw_text=(
                "Honors capstone evidence about gas kinematics and galaxy morphology."
            ),
            source_metadata={},
            provenance={},
            content_hash=f"gas-compiler-{user_id}",
            adapter_version="compiler-test-v1",
            status="READY",
        )
        unicorn_source = ListeningSource(
            user_id=user_id,
            source_type="MANUAL",
            label="UNICORN project source packet",
            raw_text=(
                "GEVIP project evidence about astronomical image inspection and "
                "categorization."
            ),
            source_metadata={},
            provenance={},
            content_hash=f"unicorn-compiler-{user_id}",
            adapter_version="compiler-test-v1",
            status="READY",
        )
        session.add_all([gas_source, unicorn_source])
        session.flush()

        gas_evidence = ListeningEvidence(
            user_id=user_id,
            source_id=gas_source.id,
            source_type="MANUAL",
            raw_excerpt=(
                "The honors capstone studied gas kinematics and 3D galaxy morphology "
                "and produced a poster and technical report."
            ),
            normalized_excerpt=None,
            excerpt_hash=f"gas-evidence-{user_id}",
            category="PROJECT",
            confidence=Decimal("0.940"),
            location={},
            provenance={},
        )
        unicorn_evidence = ListeningEvidence(
            user_id=user_id,
            source_id=unicorn_source.id,
            source_type="MANUAL",
            raw_excerpt=(
                "The separate UNICORN GEVIP project reviewed telescope imaging and "
                "detection candidates for reliable categorization."
            ),
            normalized_excerpt=None,
            excerpt_hash=f"unicorn-evidence-{user_id}",
            category="PROJECT",
            confidence=Decimal("0.910"),
            location={},
            provenance={},
        )
        session.add_all([gas_evidence, unicorn_evidence])
        session.flush()

        proposals = {
            "gas": ReviewProposal(
                id=f"compiler-gas-{user_id}",
                user_id=user_id,
                proposal_type="PROJECT",
                entity_type="PROJECT",
                title=GAS_TITLE,
                identity_key=f"compiler-gas-{user_id}",
                proposal_data={"title": GAS_TITLE},
                decision="APPROVED",
            ),
            "unicorn": ReviewProposal(
                id=f"compiler-unicorn-{user_id}",
                user_id=user_id,
                proposal_type="PROJECT",
                entity_type="PROJECT",
                title=UNICORN_TITLE,
                identity_key=f"compiler-unicorn-{user_id}",
                proposal_data={"title": UNICORN_TITLE},
                decision="APPROVED",
            ),
            "sparse": ReviewProposal(
                id=f"compiler-sparse-{user_id}",
                user_id=user_id,
                proposal_type="PROJECT",
                entity_type="PROJECT",
                title=SPARSE_TITLE,
                identity_key=f"compiler-sparse-{user_id}",
                proposal_data={"title": SPARSE_TITLE},
                decision="APPROVED",
            ),
        }
        session.add_all(proposals.values())
        session.flush()

        gas_memory = CanonicalMemoryRecord(
            user_id=user_id,
            identity_key=f"compiler-gas-{user_id}",
            memory_type="PROJECT",
            title=GAS_TITLE,
            structured_fields={
                "title": GAS_TITLE,
                "aliases": ["Gas Kinematics", "3D Galaxy Morphology capstone"],
                "summary": "Honors capstone project, separate from UNICORN.",
            },
            evidence_ids=[str(gas_evidence.id)],
            source_ids=[str(gas_source.id)],
            confidence=Decimal("0.920"),
            review_proposal_id=proposals["gas"].id,
        )
        unicorn_memory = CanonicalMemoryRecord(
            user_id=user_id,
            identity_key=f"compiler-unicorn-{user_id}",
            memory_type="PROJECT",
            title=UNICORN_TITLE,
            structured_fields={
                "title": UNICORN_TITLE,
                "aliases": ["UNICORN", "GEVIP UNICORN"],
                "summary": "Earlier GEVIP project, separate from Gas Kinematics.",
            },
            evidence_ids=[str(unicorn_evidence.id)],
            source_ids=[str(unicorn_source.id)],
            confidence=Decimal("0.900"),
            review_proposal_id=proposals["unicorn"].id,
        )
        sparse_memory = CanonicalMemoryRecord(
            user_id=user_id,
            identity_key=f"compiler-sparse-{user_id}",
            memory_type="PROJECT",
            title=SPARSE_TITLE,
            structured_fields={"title": SPARSE_TITLE, "summary": "A short note."},
            evidence_ids=[],
            source_ids=[],
            confidence=Decimal("0.610"),
            review_proposal_id=proposals["sparse"].id,
        )
        session.add_all([gas_memory, unicorn_memory, sparse_memory])
        session.flush()

        gas_approved = _enrichment(
            user_id=user_id,
            memory_id=gas_memory.id,
            memory_title=gas_memory.title,
            status="APPROVED",
            source_id=gas_source.id,
            source_label=gas_source.label,
            evidence_ids=[str(gas_evidence.id)],
            structured={
                "project_title": GAS_TITLE,
                "research_question": (
                    "Whether H-alpha gas velocity dispersion can help interpret the "
                    "3D morphology of high-redshift galaxies and whether it relates "
                    "to the GALFIT axis ratio b/a."
                ),
                "data_or_inputs": [
                    "CEERS and RUBIES catalogs",
                    "JWST/NIRSpec spectroscopy",
                    "JWST/NIRCam imaging",
                    "GALFIT axis ratios (b/a)",
                    "spectral and imaging data",
                ],
                "tools_or_methods": [
                    "catalog crossmatching by RA/DEC",
                    "H-alpha line identification using redshift",
                    "Gaussian fitting with nearby [NII] components",
                    "line-width to velocity-dispersion conversion",
                    "instrumental broadening correction",
                    "uncertainty and error propagation",
                    "covariance-matrix errors from the p_cov diagonal",
                    "S/N filtering",
                    "manual visual inspection and quality cuts",
                    "sigma_gas versus b/a plotting",
                    "low- and high-mass-bin comparison",
                ],
                "findings_or_results": [
                    "No clear overall trend was found, with significant scatter.",
                    "The expected trend appeared clearer only in the high-mass bin.",
                ],
                "limitations": [
                    "limited sample size",
                    "slit-galaxy misalignment",
                    "turbulence, feedback, mergers, and disturbed gas motions",
                    "unresolved high-redshift kinematics and problematic fits",
                ],
                "outputs": [
                    "honors capstone poster",
                    "URF poster presentation",
                    "technical report",
                ],
                "warnings_not_to_claim": [
                    "Do not claim a conclusive trend.",
                    "Do not claim quantified business impact or a deployed ML system.",
                ],
            },
        )
        unicorn_approved = _enrichment(
            user_id=user_id,
            memory_id=unicorn_memory.id,
            memory_title=unicorn_memory.title,
            status="APPROVED",
            source_id=unicorn_source.id,
            source_label=unicorn_source.label,
            evidence_ids=[str(unicorn_evidence.id)],
            structured={
                "project_title": UNICORN_TITLE,
                "research_question": (
                    "How to organize, inspect, categorize, and review astronomical "
                    "imaging and detection data for a reliable labeling workflow."
                ),
                "data_or_inputs": [
                    "astronomical telescope imaging data",
                    "FITS files and inspection plots",
                    "detection and source candidates",
                ],
                "tools_or_methods": [
                    "manual inspection of images and plots",
                    "detection review",
                    "categorization and labeling",
                    "t-SNE exploratory organization",
                    "grouping and sorting images by visual features",
                    "identifying spurious detections, hot pixels, noise, and artifacts",
                    "technical documentation and proposal review",
                ],
                "findings_or_results": [
                    "Improved the efficiency and consistency of the supported "
                    "labeling and review workflow."
                ],
                "outputs": ["reviewed image categories", "technical documentation"],
                "warnings_not_to_claim": [
                    "Do not claim a deployed or production ML model.",
                    "Do not claim a quantified performance gain.",
                ],
            },
        )
        proposed = _enrichment(
            user_id=user_id,
            memory_id=gas_memory.id,
            memory_title=gas_memory.title,
            status="PROPOSED",
            structured={"tools_or_methods": ["PROPOSED-ONLY-PYTORCH"]},
        )
        rejected = _enrichment(
            user_id=user_id,
            memory_id=gas_memory.id,
            memory_title=gas_memory.title,
            status="REJECTED",
            structured={"findings_or_results": ["REJECTED-ONLY-99-PERCENT"]},
        )
        archived = _enrichment(
            user_id=user_id,
            memory_id=gas_memory.id,
            memory_title=gas_memory.title,
            status="ARCHIVED",
            structured={"data_or_inputs": ["ARCHIVED-ONLY-SDSS"]},
        )
        session.add_all([gas_approved, unicorn_approved, proposed, rejected, archived])
        session.flush()

        approved_feedback = CareerFeedbackEvent(
            user_id=user_id,
            raw_note=(
                "The Gas Kinematics case study was followed by an interview invite."
            ),
            event_type="ARTIFACT_SUCCESS",
            structured_summary=(
                "An approved outcome note links the Gas case study to one interview "
                "invite."
            ),
            artifact_type="PROJECT",
            artifact_label="Gas Kinematics case study",
            outcome="INTERVIEW_INVITE",
            event_metadata={},
            related_memory_ids=[str(gas_memory.id)],
            suggested_future_use=(
                "Reuse the clear uncertainty framing as strategy, not factual proof."
            ),
            status="APPROVED",
        )
        archived_feedback = CareerFeedbackEvent(
            user_id=user_id,
            raw_note="An old Gas draft received a callback.",
            event_type="ARTIFACT_SUCCESS",
            structured_summary="Archived outcome that must not affect compilation.",
            artifact_type="PROJECT",
            artifact_label="Old Gas draft",
            outcome="CALLBACK",
            event_metadata={},
            related_memory_ids=[str(gas_memory.id)],
            suggested_future_use="Do not use this archived signal.",
            status="ARCHIVED",
        )
        session.add_all([approved_feedback, archived_feedback])
        session.flush()

        return SeededCompilerMemory(
            gas_memory_id=gas_memory.id,
            unicorn_memory_id=unicorn_memory.id,
            sparse_memory_id=sparse_memory.id,
            gas_approved_enrichment_id=gas_approved.id,
            unicorn_approved_enrichment_id=unicorn_approved.id,
            excluded_enrichment_ids=(proposed.id, rejected.id, archived.id),
            approved_feedback_id=approved_feedback.id,
            archived_feedback_id=archived_feedback.id,
        )


def _compile(
    user_id: uuid.UUID,
    memory_id: uuid.UUID,
    target_role: str | None = None,
) -> CompiledCareerMemoryProfile:
    with SessionLocal() as session:
        return CareerMemoryCompiler(user_id=user_id).compile(
            session, memory_id, target_role=target_role
        )


def _factual_text(profile: CompiledCareerMemoryProfile) -> str:
    """Render factual fields without boundaries, warnings, or role interpretation."""

    values: list[str] = [profile.research_question_or_problem or ""]
    for field in (
        profile.data_or_inputs,
        profile.methods,
        profile.tools,
        profile.workflow_steps,
        profile.findings_or_results,
        profile.limitations,
        profile.outputs,
        profile.collaborators_or_context,
        profile.proof_claims,
        profile.resume_bullet_claims,
    ):
        values.extend(field)
    return " ".join(values).casefold()


def _profile_text(profile: CompiledCareerMemoryProfile) -> str:
    return " ".join(
        str(value)
        for key, value in profile.model_dump(mode="json").items()
        if key not in {"evidence_used"}
    ).casefold()


def _assert_contains_any(text_value: str, *alternatives: str) -> None:
    assert any(item.casefold() in text_value for item in alternatives), (
        f"Expected one of {alternatives!r} in compiled text."
    )


def test_compiler_uses_approved_enrichment_and_excludes_other_statuses() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        profile = _compile(user_id, seeded.gas_memory_id)
        rendered = _profile_text(profile)

        assert profile.enrichment_ids_used == [seeded.gas_approved_enrichment_id]
        assert not set(seeded.excluded_enrichment_ids).intersection(
            profile.enrichment_ids_used
        )
        assert "proposed-only-pytorch" not in rendered
        assert "rejected-only-99-percent" not in rendered
        assert "archived-only-sdss" not in rendered
    finally:
        _cleanup_user(user_id)


def test_compiler_keeps_gas_and_unicorn_factual_profiles_separate() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        gas = _compile(user_id, seeded.gas_memory_id, "Data Scientist Intern")
        unicorn = _compile(user_id, seeded.unicorn_memory_id, "AI Engineer Intern")
        gas_facts = _factual_text(gas)
        unicorn_facts = _factual_text(unicorn)

        assert gas.memory_id == seeded.gas_memory_id
        assert gas.canonical_title == GAS_TITLE
        assert gas.enrichment_ids_used == [seeded.gas_approved_enrichment_id]
        assert "t-sne" not in gas_facts
        assert "hot pixel" not in gas_facts

        assert unicorn.memory_id == seeded.unicorn_memory_id
        assert unicorn.canonical_title == UNICORN_TITLE
        assert unicorn.enrichment_ids_used == [seeded.unicorn_approved_enrichment_id]
        for forbidden in (
            "h-alpha",
            "nirspec",
            "nircam",
            "galfit",
            "ceers",
            "rubies",
            "sigma_gas",
            "gas kinematics",
        ):
            assert forbidden not in unicorn_facts
    finally:
        _cleanup_user(user_id)


def test_compiler_builds_rich_gas_profile_from_supported_detail() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        profile = _compile(user_id, seeded.gas_memory_id, "Data Scientist Intern")
        factual = _factual_text(profile)
        complete = _profile_text(profile)

        for expected in (
            "ceers",
            "rubies",
            "nirspec",
            "nircam",
            "galfit",
            "b/a",
            "h-alpha",
            "gaussian fitting",
            "ra/dec",
            "instrumental broadening",
            "uncertainty",
            "p_cov",
            "s/n filtering",
            "sigma_gas",
            "no clear",
            "significant scatter",
        ):
            assert expected in factual
        _assert_contains_any(factual, "[nii]", "[n ii]", "nii")
        _assert_contains_any(factual, "mass bin", "mass-bin")
        assert "conclusive trend" in complete
        assert profile.proof_claims
        assert profile.confidence > 0.5
    finally:
        _cleanup_user(user_id)


def test_compiler_builds_rich_unicorn_ai_profile_from_supported_detail() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        profile = _compile(user_id, seeded.unicorn_memory_id, "AI Engineer Intern")
        factual = _factual_text(profile)
        complete = _profile_text(profile)

        for expected in (
            "image",
            "fits",
            "inspection",
            "detection review",
            "categorization",
            "labeling",
            "t-sne",
            "hot pixels",
            "noise",
            "technical documentation",
        ):
            assert expected in factual
        _assert_contains_any(complete, "data quality", "data-quality")
        _assert_contains_any(complete, "human-in-the-loop", "human in the loop")
        assert "production ml model" in complete
        assert profile.proof_claims
    finally:
        _cleanup_user(user_id)


def test_compiler_labels_approved_outcomes_as_signals_and_excludes_archived() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        profile = _compile(user_id, seeded.gas_memory_id)
        factual = _factual_text(profile)

        assert profile.outcome_signal_ids_used == [seeded.approved_feedback_id]
        assert seeded.archived_feedback_id not in profile.outcome_signal_ids_used
        assert len(profile.outcome_signals) == 1
        signal = profile.outcome_signals[0]
        assert signal.feedback_event_id == seeded.approved_feedback_id
        _assert_contains_any(signal.caveat.casefold(), "signal", "not proof")
        assert "interview invite" not in factual
        assert "callback" not in factual
    finally:
        _cleanup_user(user_id)


def test_target_role_changes_interpretation_but_not_factual_evidence() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        untargeted = _compile(user_id, seeded.gas_memory_id)
        targeted = _compile(
            user_id,
            seeded.gas_memory_id,
            "Python Production ML Deployment Engineer",
        )

        assert _factual_text(targeted) == _factual_text(untargeted)
        assert "python" not in _factual_text(targeted)
        assert "deployment engineer" not in _factual_text(targeted)
        assert targeted.target_role_interpretation
        assert "python production ml deployment engineer" in (
            targeted.target_role_interpretation or ""
        ).casefold()
    finally:
        _cleanup_user(user_id)


def test_sparse_memory_reports_missing_or_weak_sections_without_invention() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        profile = _compile(user_id, seeded.sparse_memory_id, "Data Scientist Intern")
        missing = " ".join(profile.missing_or_weak_sections).casefold()
        factual = _factual_text(profile)

        assert profile.missing_or_weak_sections
        _assert_contains_any(missing, "result", "outcome", "finding")
        _assert_contains_any(missing, "tool", "method")
        _assert_contains_any(missing, "output", "link")
        assert "python" not in factual
        assert "quantified" not in factual
        assert profile.confidence < 0.7
    finally:
        _cleanup_user(user_id)


def test_sparse_named_projects_do_not_gain_capabilities_from_identity_alone() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    with SessionLocal.begin() as session:
        session.add(
            User(
                id=user_id,
                clerk_user_id=f"compiler-sparse-named-{user_id}",
                email=f"compiler-sparse-named-{user_id}@example.invalid",
                display_name="Sparse Named Project Test User",
            )
        )
        session.flush()
        memories: dict[str, CanonicalMemoryRecord] = {}
        for key, title in (("gas", GAS_TITLE), ("unicorn", UNICORN_TITLE)):
            proposal = ReviewProposal(
                id=f"compiler-sparse-{key}-{user_id}",
                user_id=user_id,
                proposal_type="PROJECT",
                entity_type="PROJECT",
                title=title,
                identity_key=f"compiler-sparse-{key}-{user_id}",
                proposal_data={"title": title},
                decision="APPROVED",
            )
            session.add(proposal)
            session.flush()
            memory = CanonicalMemoryRecord(
                user_id=user_id,
                identity_key=f"compiler-sparse-{key}-{user_id}",
                memory_type="PROJECT",
                title=title,
                structured_fields={
                    "title": title,
                    "summary": "A brief approved project note without method detail.",
                },
                evidence_ids=[],
                source_ids=[],
                confidence=Decimal("0.610"),
                review_proposal_id=proposal.id,
            )
            session.add(memory)
            session.flush()
            memories[key] = memory

    try:
        gas_profile = _compile(user_id, memories["gas"].id, "Data Scientist Intern")
        unicorn_profile = _compile(
            user_id,
            memories["unicorn"].id,
            "AI Engineer Intern",
        )
        assert not gas_profile.methods
        assert not unicorn_profile.methods
        for profile in (gas_profile, unicorn_profile):
            assert "does not yet support" in profile.role_relevance.casefold()

        with SessionLocal() as session:
            gas_artifact = ProofArtifactService(user_id=user_id).create(
                session,
                ProofArtifactCreateRequest(
                    source_memory_id=memories["gas"].id,
                    target_role="Data Scientist Intern",
                ),
            )
        with SessionLocal() as session:
            unicorn_artifact = ProofArtifactService(user_id=user_id).create(
                session,
                ProofArtifactCreateRequest(
                    source_memory_id=memories["unicorn"].id,
                    target_role="AI Engineer Intern",
                ),
            )

        assert gas_artifact.latest_version.title != (
            "Data Science Case Study: Testing Galaxy Morphology with JWST "
            "Spectroscopy and Imaging"
        )
        assert unicorn_artifact.latest_version.title == (
            "AI / Automation Proof Case Study: The UNICORN Project"
        )
        gas_content = gas_artifact.latest_version.content.casefold()
        unicorn_content = unicorn_artifact.latest_version.content.casefold()
        for unsupported in (
            "debug messy data",
            "data cleaning, modeling, validation",
            "reason about uncertainty",
        ):
            assert unsupported not in gas_content
        for unsupported in (
            "image inspection and categorization",
            "human-in-the-loop review",
            "t-sne for exploratory organization",
            "data-quality and labeling workflow",
        ):
            assert unsupported not in unicorn_content
        assert "approved evidence is not yet detailed enough" in gas_content
        assert "approved evidence is not yet detailed enough" in unicorn_content
    finally:
        _cleanup_user(user_id)


def test_proof_artifacts_use_compiled_gas_and_unicorn_profiles() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        service = ProofArtifactService(user_id=user_id)
        with SessionLocal() as session:
            gas = service.create(
                session,
                ProofArtifactCreateRequest(
                    source_memory_id=seeded.gas_memory_id,
                    target_role="Data Scientist Intern",
                ),
            )
        with SessionLocal() as session:
            unicorn = service.create(
                session,
                ProofArtifactCreateRequest(
                    source_memory_id=seeded.unicorn_memory_id,
                    target_role="AI Engineer Intern",
                ),
            )

        gas_text = " ".join(
            (
                gas.latest_version.title,
                gas.latest_version.content,
                str(gas.latest_version.structured_sections),
            )
        ).casefold()
        unicorn_text = " ".join(
            (
                unicorn.latest_version.title,
                unicorn.latest_version.content,
                str(unicorn.latest_version.structured_sections),
            )
        ).casefold()

        assert gas.latest_version.title == (
            "Data Science Case Study: Testing Galaxy Morphology with JWST "
            "Spectroscopy and Imaging"
        )
        for expected in (
            "jwst",
            "h-alpha",
            "galfit",
            "gaussian fitting",
            "uncertainty",
            "sigma_gas",
            "no clear",
        ):
            assert expected in gas_text
        assert "sigma_gas" in gas.latest_version.content.casefold()
        gas_outcome = str(
            gas.latest_version.structured_sections["outcome_or_insight"]
        ).casefold()
        assert "careful hypothesis testing" in gas_outcome
        _assert_contains_any(
            gas_outcome,
            "rather than failure",
            "not a failure",
        )
        gas_question = str(
            gas.latest_version.structured_sections["reviewer_question"]
        ).casefold()
        for expected in ("data cleaning", "modeling", "validation", "uncertainty"):
            assert expected in gas_question

        assert unicorn.latest_version.title == (
            "AI/Data Workflow Case Study: Image Inspection and Categorization in "
            "the UNICORN Project"
        )
        for expected in ("image", "inspection", "categorization", "t-sne"):
            assert expected in unicorn_text
        _assert_contains_any(unicorn_text, "data quality", "data-quality")
        unicorn_question = str(
            unicorn.latest_version.structured_sections["reviewer_question"]
        ).casefold()
        _assert_contains_any(unicorn_question, "data quality", "data-quality")
        assert "labeling" in unicorn_question
        for forbidden in (
            "h-alpha",
            "galfit",
            "ceers",
            "rubies",
            "sigma_gas",
        ):
            assert forbidden not in unicorn_text
        assert GAS_TITLE.casefold() not in unicorn_text
        assert "gas kinematics" not in unicorn.latest_version.content.casefold()
        assert "gas kinematics" not in str(
            unicorn.latest_version.structured_sections["context"]
        ).casefold()
        assert not any(
            "gas kinematics" in warning.casefold()
            for warning in unicorn.latest_version.warnings
        )
        assert "gas kinematics" in str(
            unicorn.latest_version.structured_sections["compiled_profile"][
                "project_boundary"
            ]
        ).casefold()
    finally:
        _cleanup_user(user_id)

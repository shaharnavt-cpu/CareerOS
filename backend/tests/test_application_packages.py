"""Regression coverage for evidence-backed Application Package Builder."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.application_packages import get_application_package_service
from app.core.config import Settings
from app.db.session import SessionLocal, engine
from app.fixtures.application_writing_demo import build_maya_chen_demo_writing_input
from app.main import app
from app.models import (
    ApplicationPackage,
    ApplicationPackageVersion,
    CanonicalMemoryRecord,
    CareerMemoryEnrichment,
    ListeningEvidence,
    ListeningSource,
    ReviewProposal,
)
from app.schemas.application_packages import (
    ApplicationPackageCreateRequest,
    ApplicationPackageOutputsUpdateRequest,
    ApplicationPackageStatus,
    ApplicationPackageUpdateRequest,
    ApplicationPackageView,
    ApplicationQuestion,
    EvidenceSourceType,
    EvidenceSupportType,
)
from app.schemas.proof_artifacts import (
    ProofArtifactCreateRequest,
    ProofArtifactStatus,
    ProofArtifactUpdateRequest,
)
from app.services.application_packages import (
    ApplicationPackageNotFoundError,
    ApplicationPackageService,
    ApplicationPackageValidationError,
    _EditedClaim,
)
from app.services.career_memory_compiler import CareerMemoryCompiler
from app.services.proof_artifacts import ProofArtifactService
from tests.test_application_writing_claim_contract import _valid_output
from tests.test_career_memory_compiler import (
    GAS_TITLE,
    UNICORN_TITLE,
    SeededCompilerMemory,
    _enrichment,
    _seed_compiler_memories,
)
from tests.test_career_memory_compiler import (
    _cleanup_user as _cleanup_compiler_user,
)


@dataclass(frozen=True)
class RichPackageFixture:
    user_id: uuid.UUID
    seeded: SeededCompilerMemory


def _required_application_questions() -> list[ApplicationQuestion]:
    return [
        ApplicationQuestion(
            question_id="motivation",
            question_text="Why are you interested in this role?",
            required=True,
        ),
        ApplicationQuestion(
            question_id="complex-data-project",
            question_text="Describe a project where you analyzed complex data.",
            required=True,
        ),
        ApplicationQuestion(
            question_id="quality-reliability",
            question_text="How did you ensure the quality or reliability of your work?",
            required=True,
        ),
    ]


def _application_package_service(user_id: uuid.UUID) -> ApplicationPackageService:
    """Keep the non-live suite isolated from workstation provider settings."""

    return ApplicationPackageService(
        user_id=user_id,
        settings=Settings(
            _env_file=None,
            application_writer_provider="local-deterministic",
            application_writer_data_policy="private",
        ),
    )


def _require_postgres() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")


def _cleanup_package_user(user_id: uuid.UUID) -> None:
    with SessionLocal.begin() as session:
        session.execute(
            delete(ApplicationPackageVersion).where(
                ApplicationPackageVersion.user_id == user_id
            )
        )
        session.execute(
            delete(ApplicationPackage).where(ApplicationPackage.user_id == user_id)
        )
    _cleanup_compiler_user(user_id)


@pytest.fixture
def rich_package_fixture() -> Iterator[RichPackageFixture]:
    _require_postgres()
    user_id = uuid.uuid4()
    seeded = _seed_compiler_memories(user_id)
    try:
        yield RichPackageFixture(user_id=user_id, seeded=seeded)
    finally:
        _cleanup_package_user(user_id)


def _create_and_generate(
    fixture: RichPackageFixture,
    *,
    selected_memory_ids: list[uuid.UUID],
    role_title: str,
    target_description: str,
    company: str = "Test Company",
    required_skills: list[str] | None = None,
    preferred_skills: list[str] | None = None,
    responsibilities: list[str] | None = None,
    application_questions: list[ApplicationQuestion] | None = None,
) -> ApplicationPackageView:
    service = _application_package_service(fixture.user_id)
    with SessionLocal() as session:
        created = service.create(
            session,
            ApplicationPackageCreateRequest(
                role_title=role_title,
                company=company,
                target_description=target_description,
                required_skills=required_skills or [],
                preferred_skills=preferred_skills or [],
                responsibilities=responsibilities or [],
                application_questions=(
                    _required_application_questions()
                    if application_questions is None
                    else application_questions
                ),
                selected_memory_ids=selected_memory_ids,
            ),
        )
        return service.generate(session, created.package_id)


def _substantive_claim_text(package: ApplicationPackageView) -> str:
    """Render factual surfaces without warning/do-not-claim or target-only copy."""

    assert package.latest_version is not None
    outputs = package.latest_version.outputs
    values = [
        outputs.positioning_summary.primary_positioning,
        outputs.positioning_summary.strongest_evidence,
        *outputs.positioning_summary.secondary_evidence,
        *(
            bullet.bullet_text
            for group in outputs.resume_bullets
            for bullet in group.bullets
        ),
        *outputs.cover_letter.body_paragraphs,
        *(snippet.text for snippet in outputs.application_snippets[1:]),
    ]
    return " ".join(values).casefold()


def _resume_edit_payload(
    package: ApplicationPackageView,
    replacement: str,
) -> list[dict[str, object]]:
    assert package.latest_version is not None
    groups = [
        group.model_dump(mode="json")
        for group in package.latest_version.outputs.resume_bullets
    ]
    assert groups
    bullets = groups[0]["bullets"]
    assert isinstance(bullets, list) and bullets
    assert isinstance(bullets[0], dict)
    bullets[0]["bullet_text"] = replacement
    return groups


def _add_approved_limitation(
    fixture: RichPackageFixture,
    limitation: str,
) -> None:
    with SessionLocal.begin() as session:
        enrichment = session.get(
            CareerMemoryEnrichment,
            fixture.seeded.gas_approved_enrichment_id,
        )
        assert enrichment is not None
        structured = dict(enrichment.structured_enrichment)
        structured["limitations"] = [
            limitation,
            *structured.get("limitations", []),
        ]
        enrichment.structured_enrichment = structured


def _seed_unapproved_memory(user_id: uuid.UUID) -> uuid.UUID:
    proposal_id = f"proposed-package-memory-{user_id}"
    with SessionLocal.begin() as session:
        proposal = ReviewProposal(
            id=proposal_id,
            user_id=user_id,
            proposal_type="PROJECT",
            entity_type="PROJECT",
            title="Unreviewed Cloud Project",
            identity_key=f"proposed-package-memory-{user_id}",
            proposal_data={"title": "Unreviewed Cloud Project"},
            decision="PROPOSED",
        )
        session.add(proposal)
        session.flush()
        memory = CanonicalMemoryRecord(
            user_id=user_id,
            identity_key=f"proposed-package-memory-{user_id}",
            memory_type="PROJECT",
            title="Unreviewed Cloud Project",
            structured_fields={
                "title": "Unreviewed Cloud Project",
                "summary": "Unapproved AWS and Kubernetes claims.",
            },
            evidence_ids=[],
            source_ids=[],
            confidence=Decimal("0.800"),
            review_proposal_id=proposal_id,
        )
        session.add(memory)
        session.flush()
        return memory.id


NULLABLE_SKILL_TITLE = "Technical Skills"
GALAXY_VIP_TITLE = "Galaxy Evolution VIP"


def _seed_nullable_skill_memory(
    user_id: uuid.UUID,
    *,
    with_direct_evidence: bool = False,
    direct_evidence_skills: tuple[str, ...] = ("Python", "SQL", "Excel", "R"),
) -> uuid.UUID:
    """Approve a generic Technical Skills memory with no research/problem field.

    Skill, education, and employment memories legitimately compile with
    ``research_question_or_problem`` set to ``None`` because none of the
    research/project/problem/objective/goal/summary/description fields exist.
    """

    proposal_id = f"approved-skill-memory-{user_id}"
    with SessionLocal.begin() as session:
        proposal = ReviewProposal(
            id=proposal_id,
            user_id=user_id,
            proposal_type="SKILL_SET",
            entity_type="SKILL",
            title=NULLABLE_SKILL_TITLE,
            identity_key=f"approved-skill-memory-{user_id}",
            proposal_data={"title": NULLABLE_SKILL_TITLE},
            decision="APPROVED",
        )
        session.add(proposal)
        session.flush()
        evidence_ids: list[str] = []
        source_ids: list[str] = []
        if with_direct_evidence:
            supported_skills = ", ".join(direct_evidence_skills)
            source = ListeningSource(
                user_id=user_id,
                source_type="MANUAL",
                label="Reviewed Technical Skills work samples",
                raw_text=(
                    "Reviewed work samples document technical work using "
                    f"{supported_skills}."
                ),
                source_metadata={},
                provenance={},
                content_hash=f"approved-skill-source-{user_id}",
                adapter_version="application-package-test-v1",
                status="READY",
            )
            session.add(source)
            session.flush()
            evidence = ListeningEvidence(
                user_id=user_id,
                source_id=source.id,
                source_type="MANUAL",
                raw_excerpt=(
                    f"Documented technical work used {supported_skills}."
                ),
                normalized_excerpt=None,
                excerpt_hash=f"approved-skill-evidence-{user_id}",
                category="SKILL",
                confidence=Decimal("0.930"),
                location={},
                provenance={},
            )
            session.add(evidence)
            session.flush()
            evidence_ids = [str(evidence.id)]
            source_ids = [str(source.id)]
        memory = CanonicalMemoryRecord(
            user_id=user_id,
            identity_key=f"approved-skill-memory-{user_id}",
            memory_type="SKILL_SET",
            title=NULLABLE_SKILL_TITLE,
            structured_fields={
                "name": NULLABLE_SKILL_TITLE,
                "category": "Technical Skills",
                "skills": ["Python", "SQL", "Excel", "R"],
            },
            evidence_ids=evidence_ids,
            source_ids=source_ids,
            confidence=Decimal("0.900"),
            review_proposal_id=proposal_id,
        )
        session.add(memory)
        session.flush()
        return memory.id


def _seed_galaxy_vip_memory(user_id: uuid.UUID) -> uuid.UUID:
    """Approve a fourth, independently sourced project memory."""

    proposal_id = f"approved-galaxy-vip-memory-{user_id}"
    with SessionLocal.begin() as session:
        proposal = ReviewProposal(
            id=proposal_id,
            user_id=user_id,
            proposal_type="PROJECT",
            entity_type="PROJECT",
            title=GALAXY_VIP_TITLE,
            identity_key=f"approved-galaxy-vip-memory-{user_id}",
            proposal_data={"title": GALAXY_VIP_TITLE},
            decision="APPROVED",
        )
        session.add(proposal)
        session.flush()
        memory = CanonicalMemoryRecord(
            user_id=user_id,
            identity_key=f"approved-galaxy-vip-memory-{user_id}",
            memory_type="PROJECT",
            title=GALAXY_VIP_TITLE,
            structured_fields={
                "title": GALAXY_VIP_TITLE,
                "research_question": (
                    "How observational evidence informs models of galaxy evolution."
                ),
                "summary": "A literature analysis and presentation project.",
            },
            evidence_ids=[],
            source_ids=[],
            confidence=Decimal("0.880"),
            review_proposal_id=proposal_id,
        )
        session.add(memory)
        session.flush()
        session.add(
            _enrichment(
                user_id=user_id,
                memory_id=memory.id,
                memory_title=memory.title,
                status="APPROVED",
                structured={
                    "project_title": GALAXY_VIP_TITLE,
                    "research_question": (
                        "How observational evidence informs models of galaxy evolution."
                    ),
                    "data_or_inputs": ["peer-reviewed galaxy evolution literature"],
                    "tools_or_methods": [
                        "literature analysis and synthesis",
                        "technical presentation",
                    ],
                    "findings_or_results": [
                        "Synthesized competing explanations without claiming new "
                        "observational results."
                    ],
                    "warnings_not_to_claim": [
                        "Do not attribute Gas or UNICORN project methods to this "
                        "memory."
                    ],
                },
            )
        )
        return memory.id


def _resume_bullet_texts(package: ApplicationPackageView) -> list[str]:
    assert package.latest_version is not None
    return [
        bullet.bullet_text
        for group in package.latest_version.outputs.resume_bullets
        for bullet in group.bullets
    ]


def test_problem_phrase_returns_empty_for_null_and_blank_values() -> None:
    problem_phrase = ApplicationPackageService._problem_phrase

    assert problem_phrase(None) == ""
    assert problem_phrase("") == ""
    assert problem_phrase("   ") == ""
    assert problem_phrase(" . ") == ""
    # A populated research description is normalized and lower-cased as before.
    assert problem_phrase(
        "The project tested whether gas kinematics relates to morphology."
    ) == "gas kinematics relates to morphology"


def test_local_resume_atoms_ignore_incidental_short_target_title_match() -> None:
    """A short target title must not become proof for a memory-scoped bullet."""

    writing_input = build_maya_chen_demo_writing_input()
    writing_input.target_role = "Data"
    unicorn_memory_id = "demo-memory-image-quality"
    unicorn_bullet = (
        "Analyzed astronomical telescope imaging data with manual inspection of and "
        "detection review to investigate how to organize, inspect, categorize, and "
        "review and keep the final interpretation grounded in evidence."
    )
    draft = _valid_output(writing_input)
    draft.resume_bullet_groups[0].memory_id = unicorn_memory_id
    draft.resume_bullet_groups[0].bullets[0].text = unicorn_bullet

    service = _application_package_service(uuid.uuid4())
    claims = service._local_candidate_claims(
        draft,
        writing_input,
        [SimpleNamespace(profile=SimpleNamespace(memory_id=unicorn_memory_id))],
    )
    resume_claim = next(
        claim
        for claim in claims
        if claim.field_path == "resume_bullet_groups.0.bullets.0.text"
    )
    atom_by_id = {
        atom.evidence_atom_id: atom for atom in writing_input.evidence_ledger
    }
    atoms = [atom_by_id[atom_id] for atom_id in resume_claim.evidence_atom_ids]

    assert resume_claim.claim_type.value == "resume-bullet"
    assert resume_claim.claim_text == unicorn_bullet
    assert atoms
    assert all(atom.canonical_memory_id == unicorn_memory_id for atom in atoms)
    assert all(atom.support_type.value != "target-context" for atom in atoms)
    assert ApplicationPackageService._mask_generated_target_labels(
        "Data analysis supports this Data role.",
        {"role_title": "Data", "company": None},
    ) == "Data analysis supports this target role."


def test_selection_requires_explicit_current_user_approved_memory_ids(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    pending_id = _seed_unapproved_memory(fixture.user_id)
    service = _application_package_service(fixture.user_id)

    with SessionLocal() as session:
        eligible = service.list_eligible_memories(session, "Data Science Intern")
        eligible_ids = {item.id for item in eligible}
        assert {
            fixture.seeded.gas_memory_id,
            fixture.seeded.unicorn_memory_id,
            fixture.seeded.sparse_memory_id,
        } <= eligible_ids
        assert pending_id not in eligible_ids

        created = service.create(
            session,
            ApplicationPackageCreateRequest(
                role_title="Data Science Intern",
                selected_memory_ids=[fixture.seeded.gas_memory_id],
            ),
        )
        assert created.selected_memory_ids == [fixture.seeded.gas_memory_id]
        assert created.latest_version is None

        with pytest.raises(
            ApplicationPackageValidationError,
            match="current-user approved Career Memory",
        ):
            service.create(
                session,
                ApplicationPackageCreateRequest(
                    role_title="Cloud Engineer Intern",
                    selected_memory_ids=[pending_id],
                ),
            )

    foreign_service = _application_package_service(uuid.uuid4())
    with SessionLocal() as session:
        with pytest.raises(
            ApplicationPackageValidationError,
            match="current-user approved Career Memory",
        ):
            foreign_service.create(
                session,
                ApplicationPackageCreateRequest(
                    role_title="Data Science Intern",
                    selected_memory_ids=[fixture.seeded.gas_memory_id],
                ),
            )
        with pytest.raises(ApplicationPackageNotFoundError):
            foreign_service.get(session, created.package_id)


def test_generation_uses_approved_enrichment_and_keeps_outcomes_strategy_only(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.gas_memory_id],
        role_title="Data Science Intern",
        target_description="Data analysis, modeling, uncertainty, and communication.",
        application_questions=[
            _required_application_questions()[0],
            ApplicationQuestion(
                question_id="optional-additional-context",
                question_text="Is there any additional context you want to share?",
                required=False,
            ),
        ],
    )
    latest = generated.latest_version
    assert latest is not None

    assert generated.memory_ids_used == [fixture.seeded.gas_memory_id]
    assert generated.enrichment_ids_used == [fixture.seeded.gas_approved_enrichment_id]
    assert generated.outcome_signal_ids_used == [fixture.seeded.approved_feedback_id]
    assert not set(fixture.seeded.excluded_enrichment_ids).intersection(
        generated.enrichment_ids_used
    )
    assert fixture.seeded.archived_feedback_id not in generated.outcome_signal_ids_used
    assert [item.question_id for item in generated.application_snippets] == [
        "motivation"
    ]

    with SessionLocal() as session:
        record = session.scalar(
            select(ApplicationPackageVersion).where(
                ApplicationPackageVersion.id == latest.id
            )
        )
        assert record is not None
        compiled_text = json.dumps(
            record.compiled_profile_snapshots_json,
            ensure_ascii=False,
        ).casefold()

    for excluded in (
        "proposed-only-pytorch",
        "rejected-only-99-percent",
        "archived-only-sdss",
    ):
        assert excluded not in compiled_text
        assert excluded not in generated.model_dump_json().casefold()
    for enrichment_id in fixture.seeded.excluded_enrichment_ids:
        assert str(enrichment_id) not in generated.model_dump_json()

    strategy_trace = [
        item
        for item in generated.evidence_trace
        if item.outcome_signal_id == fixture.seeded.approved_feedback_id
    ]
    assert len(strategy_trace) == 1
    assert strategy_trace[0].source_type is EvidenceSourceType.STRATEGY_SIGNAL
    assert strategy_trace[0].support_type is EvidenceSupportType.STRATEGY_ONLY
    assert "not factual proof" in (strategy_trace[0].caveat or "").casefold()
    assert (
        "strategy signal only"
        in " ".join(generated.cover_letter.strategy_notes).casefold()
    )
    assert "interview invite" not in _substantive_claim_text(generated)
    assert all(
        str(fixture.seeded.approved_feedback_id) not in entry.evidence_ids
        for entry in latest.claim_ledger
    )


def test_gas_data_science_package_is_detailed_without_invented_impact(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.gas_memory_id],
        role_title="Data Science Intern",
        target_description=(
            "Analyze data, build statistical models, reason about uncertainty, "
            "validate results, and communicate technical findings."
        ),
    )
    claims = _substantive_claim_text(generated)

    for supported in (
        "ceers",
        "rubies",
        "jwst/nirspec",
        "h-alpha",
        "gaussian",
        "ra/dec",
        "no clear trend",
        "significant scatter",
    ):
        assert supported in claims
    trace_text = " ".join(item.detail for item in generated.evidence_trace).casefold()
    for supported_trace_detail in ("jwst/nircam", "galfit"):
        assert supported_trace_detail in trace_text
    assert generated.latest_version is not None
    with SessionLocal() as session:
        version = session.scalar(
            select(ApplicationPackageVersion).where(
                ApplicationPackageVersion.id == generated.latest_version.id
            )
        )
        assert version is not None
        compiled_text = json.dumps(
            version.compiled_profile_snapshots_json,
            ensure_ascii=False,
        ).casefold()
    for supported_profile_detail in (
        "line-width to gas velocity-dispersion",
        "s/n filtering",
        "manual visual inspection",
    ):
        assert supported_profile_detail in compiled_text

    for invented in (
        "99 percent",
        "99%",
        "increased revenue",
        "business impact",
        "deployed",
        "production ml",
        "conclusive trend",
    ):
        assert invented not in claims
    assert generated.resume_bullets
    assert all(
        bullet.bullet_text.startswith(
            ("Analyzed", "Applied", "Validated", "Crossmatched")
        )
        for group in generated.resume_bullets
        for bullet in group.bullets
    )
    assert all(
        "No quantified outcome" not in " ".join(bullet.warnings)
        for group in generated.resume_bullets
        for bullet in group.bullets
    )
    assert any(
        warning.code == "NO_QUANTIFIED_OUTCOME" for warning in generated.warnings
    )
    version_view = generated.latest_version
    draft_text = " ".join(
        [
            version_view.outputs.positioning_summary.primary_positioning,
            version_view.outputs.cover_letter.full_text,
            *(
                bullet.bullet_text
                for group in version_view.outputs.resume_bullets
                for bullet in group.bullets
            ),
            *(snippet.text for snippet in version_view.outputs.application_snippets),
        ]
    ).casefold()
    for awkward in (
        "focused on the project tested whether",
        "the documented result was",
        "approved memory",
        "approved evidence",
    ):
        assert awkward not in draft_text
    assert 230 <= len(version_view.outputs.cover_letter.full_text.split()) <= 420
    assert all(
        len(bullet.bullet_text.split()) <= 38
        for group in version_view.outputs.resume_bullets
        for bullet in group.bullets
    )
    assert all(
        len(snippet.text.split()) <= 120
        for snippet in version_view.outputs.application_snippets
    )
    assert version_view.quality_review.primary_issue
    assert version_view.provider_metadata.provider == "local-deterministic"
    mechanical_outputs = version_view.outputs.model_copy(deep=True)
    mechanical_outputs.cover_letter.full_text = (
        "My approved work focused on the project tested whether the target fit."
    )
    mechanical_review = ApplicationPackageService._evaluate_output_quality(
        mechanical_outputs
    )
    assert mechanical_review.naturalness == "Needs attention"
    assert "mechanical" in mechanical_review.primary_issue.casefold()


def test_unicorn_ai_package_preserves_project_boundary(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    with SessionLocal.begin() as session:
        enrichment = session.get(
            CareerMemoryEnrichment,
            fixture.seeded.unicorn_approved_enrichment_id,
        )
        assert enrichment is not None
        structured = dict(enrichment.structured_enrichment)
        structured["findings_or_results"] = (
            "Improved labeling and review efficiency and better organization of "
            "image categories."
        )
        enrichment.structured_enrichment = structured

    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.unicorn_memory_id],
        # Manual QA exposed a separate title-truncation defect that left this as
        # "Data". Generation must not mistake the word "data" in a UNICORN bullet
        # for a target-context evidence atom.
        role_title="Data",
        target_description=(
            "AI-ready data quality, image labeling, human-in-the-loop review, "
            "automation, and Python."
        ),
    )
    claims = _substantive_claim_text(generated)

    assert generated.memory_ids_used == [fixture.seeded.unicorn_memory_id]
    assert generated.enrichment_ids_used == [
        fixture.seeded.unicorn_approved_enrichment_id
    ]
    assert fixture.seeded.gas_approved_enrichment_id not in (
        generated.enrichment_ids_used
    )
    for supported in (
        "image",
        "fits",
        "inspection",
        "detection review",
        "categorization",
        "t-sne",
    ):
        assert supported in claims
    for target_only in ("data quality", "human-in-the-loop"):
        assert target_only not in claims
    for gas_only in (
        "gas kinematics",
        "h-alpha",
        "[nii]",
        "nirspec",
        "nircam",
        "galfit",
        "ceers",
        "rubies",
        "sigma_gas",
        "velocity dispersion",
    ):
        assert gas_only not in claims
    assert "deployed" not in claims
    for mechanical in (
        "the approved evidence reports",
        "the documented result was",
        "approved memory",
        "approved evidence",
    ):
        assert mechanical not in claims
    assert "through manual inspection and detection review" in claims
    assert "goal of organizing, inspecting, and reviewing" in claims
    assert "by manually inspecting plots and images" in claims
    assert "reviewing detection candidates" in claims
    assert "improved efficiency in labeling and review" in claims
    assert "labeling or review efficiency" not in claims
    assert "source or detection candidates" not in claims
    assert "through inspected" not in claims
    assert "to investigate organizing" not in claims
    assert not re.search(
        r"\b(?:and|or|of|to|for|with|through|around|using|as)\s+"
        r"(?:and|or|then)\b",
        claims,
    )
    assert generated.latest_version is not None
    resume_claims = [
        item
        for item in generated.latest_version.claim_ledger
        if item.surface == "resume"
    ]
    assert resume_claims
    assert all(
        item.memory_ids == [fixture.seeded.unicorn_memory_id]
        for item in resume_claims
    )


def test_single_article_titled_project_uses_natural_candidate_grammar(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.unicorn_memory_id],
        role_title="Data Analyst Intern",
        target_description=(
            "Analyze image data, review labeling workflows, and document findings."
        ),
        application_questions=[],
    )

    assert generated.latest_version is not None
    outputs = generated.latest_version.outputs
    cover = outputs.cover_letter
    cover_text = cover.full_text.casefold()
    resume_text = " ".join(
        bullet.bullet_text
        for group in outputs.resume_bullets
        for bullet in group.bullets
    ).casefold()

    assert generated.application_snippets == []
    assert "my the unicorn project" not in cover_text
    assert "in the unicorn project" in cover_text
    assert "ability to labeling" not in cover_text
    assert "a labeling and categorization workflow" in cover_text
    assert "my strongest projects" not in cover_text
    assert "this project required" in cover.opening_paragraph.casefold()
    assert cover_text.count(
        "labeling and categorization workflow, technical documentation, "
        "and manual inspection of plots and images"
    ) <= 1
    secondary_paragraph = cover.body_paragraphs[1].casefold()
    assert "gave me experience with" not in secondary_paragraph
    assert "labeling and categorization workflow" not in secondary_paragraph
    assert "habit of keeping the final interpretation grounded in evidence" in (
        secondary_paragraph
    )
    assert "data analyst intern team" not in cover.closing_paragraph.casefold()
    assert cover.closing_paragraph.casefold().count("discuss") == 1
    assert cover.closing_paragraph.casefold().count("role") == 1
    assert "reviewing detection candidates" in resume_text
    assert "source or detection candidates" not in resume_text

    invalid_outputs = outputs.model_copy(deep=True)
    invalid_outputs.cover_letter.full_text = (
        "In my The Example Project, the work strengthened my ability to labeling "
        "and categorization workflow."
    )
    invalid_review = ApplicationPackageService._evaluate_output_quality(
        invalid_outputs
    )
    assert invalid_review.naturalness == "Needs attention"
    assert any("grammar" in note.casefold() for note in invalid_review.notes)

    repeated_outputs = outputs.model_copy(deep=True)
    capability_chain = (
        "labeling and categorization, technical documentation, and manual inspection"
    )
    repeated_outputs.cover_letter.full_text = (
        f"This project required {capability_chain}.\n\n"
        f"I would bring {capability_chain} to the role."
    )
    repeated_review = ApplicationPackageService._evaluate_output_quality(
        repeated_outputs
    )
    assert repeated_review.repetition == "High"
    assert any("repeated" in note.casefold() for note in repeated_review.notes)


def test_unsupported_cloud_and_deployment_requirements_warn_without_claiming_them(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.gas_memory_id],
        role_title="Cloud ML Engineer Intern",
        target_description=(
            "Build production ML deployment workflows with AWS, Azure, GCP, "
            "cloud infrastructure, Kubernetes, and Docker."
        ),
        required_skills=[
            "AWS",
            "Azure",
            "GCP",
            "cloud infrastructure",
            "Kubernetes",
            "Docker",
            "production ML deployment",
        ],
    )
    warning_requirements = {
        item.requirement
        for item in generated.warnings
        if item.code == "UNSUPPORTED_TARGET_REQUIREMENT"
    }
    assert {
        "AWS",
        "Azure",
        "GCP",
        "cloud infrastructure",
        "Kubernetes",
        "Docker",
        "production ML deployment",
    } <= warning_requirements
    warning_text = " ".join(item.message for item in generated.warnings).casefold()
    assert "selected proof does not currently support deployment" in warning_text
    assert "selected proof does not currently support that cloud experience" in (
        warning_text
    )
    assert all(
        f"Unsupported target requirement: {requirement}" in generated.unsupported_claims
        for requirement in warning_requirements
    )

    claims = _substantive_claim_text(generated)
    for unsupported_claim in (
        "aws",
        "azure",
        "gcp",
        "cloud infrastructure",
        "kubernetes",
        "docker",
        "deployed",
        "deployment",
    ):
        assert unsupported_claim not in claims
    target_trace = next(
        item
        for item in generated.evidence_trace
        if item.source_type is EvidenceSourceType.TARGET_CONTEXT
    )
    assert target_trace.support_type is EvidenceSupportType.RELEVANCE_ONLY
    assert "not proof" in (target_trace.caveat or "").casefold()


def test_sparse_memory_does_not_invent_technical_capability(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    with SessionLocal.begin() as session:
        sparse = session.get(CanonicalMemoryRecord, fixture.seeded.sparse_memory_id)
        assert sparse is not None
        session.add(
            _enrichment(
                user_id=fixture.user_id,
                memory_id=sparse.id,
                memory_title=sparse.title,
                status="APPROVED",
                structured={"data_or_inputs": ["customer records"]},
            )
        )
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.sparse_memory_id],
        role_title="Instrumentation Engineering Intern",
        target_description=(
            "Investigate instrument behavior and communicate technical findings."
        ),
        required_skills=["technical communication"],
        application_questions=[],
    )
    claims = _substantive_claim_text(generated)
    assert generated.cover_letter is not None

    assert generated.resume_bullets == []
    assert "careful project investigation" not in claims
    assert "technical communication" not in claims
    assert "developed documented experience with" not in (
        generated.cover_letter.opening_paragraph.casefold()
    )
    assert generated.application_snippets == []
    assert "technical communication" in {
        item.requirement.casefold()
        for item in generated.warnings
        if item.code == "UNSUPPORTED_TARGET_REQUIREMENT" and item.requirement
    }


def _assert_no_blank_or_none_bullets(package: ApplicationPackageView) -> None:
    for bullet_text in _resume_bullet_texts(package):
        assert bullet_text.strip(), "résumé bullets must never be blank"
        assert "None" not in bullet_text, "the literal value 'None' must never surface"


def test_nullable_skill_memory_with_gas_and_unicorn_generates_cleanly(
    rich_package_fixture: RichPackageFixture,
) -> None:
    """Scenario A: a null research_question memory must not break generation."""

    fixture = rich_package_fixture
    skill_memory_id = _seed_nullable_skill_memory(
        fixture.user_id,
        with_direct_evidence=True,
    )

    # The Technical Skills memory legitimately compiles with no research problem.
    with SessionLocal() as session:
        skill_profile = CareerMemoryCompiler(user_id=fixture.user_id).compile(
            session, skill_memory_id, target_role="Data Science Intern"
        )
    assert skill_profile.research_question_or_problem is None

    service = _application_package_service(fixture.user_id)
    with SessionLocal() as session:
        eligible_ids = {
            item.id
            for item in service.list_eligible_memories(session, "Data Science Intern")
        }
    # Generic non-research memories remain eligible and selectable.
    assert skill_memory_id in eligible_ids

    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[
            fixture.seeded.gas_memory_id,
            fixture.seeded.unicorn_memory_id,
            skill_memory_id,
        ],
        role_title="Data Science Intern",
        target_description=(
            "Analyze scientific data, communicate uncertainty, and use Python."
        ),
        application_questions=[],
    )

    # A successful, immutable first version was created.
    assert generated.latest_version is not None
    assert generated.latest_version.version_number == 1
    assert generated.version_count == 1
    assert skill_memory_id in generated.memory_ids_used

    _assert_no_blank_or_none_bullets(generated)
    claims = _substantive_claim_text(generated)

    # No fabricated research problem is attributed to the Technical Skills memory.
    for invented in (
        "investigate technical skills",
        "the project focused on",
        "the project tested whether",
    ):
        assert invented not in claims

    # Gas and UNICORN evidence stay correctly separated: gas-only jargon never
    # appears in the UNICORN résumé group and vice versa.
    gas_bullets = _bullets_for_memory_title(generated, GAS_TITLE)
    unicorn_bullets = _bullets_for_memory_title(generated, UNICORN_TITLE)
    for gas_only in ("h-alpha", "nirspec", "galfit", "ceers", "velocity dispersion"):
        assert gas_only not in unicorn_bullets
    for unicorn_only in ("t-sne", "detection review"):
        assert unicorn_only not in gas_bullets

    # Zero application questions produce zero application answers.
    assert generated.application_snippets == []


def _bullets_for_memory_title(package: ApplicationPackageView, title: str) -> str:
    """Casefolded résumé bullet text attributed to a single memory title."""

    assert package.latest_version is not None
    values = [
        bullet.bullet_text
        for group in package.latest_version.outputs.resume_bullets
        if title in (group.memory_title or "")
        for bullet in group.bullets
    ]
    return " ".join(values).casefold()


def test_nullable_skill_memory_without_proof_omits_unsupported_capabilities(
    rich_package_fixture: RichPackageFixture,
) -> None:
    """Selection metadata alone must not prove concrete technical capabilities."""

    fixture = rich_package_fixture
    skill_memory_id = _seed_nullable_skill_memory(fixture.user_id)

    with SessionLocal() as session:
        skill_profile = CareerMemoryCompiler(user_id=fixture.user_id).compile(
            session, skill_memory_id, target_role="Data Analytics Intern"
        )
    assert skill_profile.research_question_or_problem is None

    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[skill_memory_id],
        role_title="Data Analytics Intern",
        target_description="Use Python and SQL to analyze and report on data.",
        application_questions=[],
    )

    # Generation succeeds and records a successful immutable version.
    assert generated.latest_version is not None
    assert generated.latest_version.version_number == 1
    assert generated.memory_ids_used == [skill_memory_id]

    assert generated.resume_bullets == []
    _assert_no_blank_or_none_bullets(generated)
    claims = _substantive_claim_text(generated)
    for unsupported in ("python", "sql", "excel"):
        assert unsupported not in claims
    for invented in (
        "investigate technical skills",
        "concrete project",
        "the project focused on",
        "the project tested whether",
    ):
        assert invented not in claims
    assert generated.application_snippets == []


def test_nullable_skill_memory_with_direct_evidence_generates_supported_claims(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    skill_memory_id = _seed_nullable_skill_memory(
        fixture.user_id,
        with_direct_evidence=True,
    )

    with SessionLocal() as session:
        profile = CareerMemoryCompiler(user_id=fixture.user_id).compile(
            session, skill_memory_id, target_role="Data Analytics Intern"
        )
    assert profile.research_question_or_problem is None

    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[skill_memory_id],
        role_title="Data Analytics Intern",
        target_description="Use Python and SQL to analyze and report on data.",
        application_questions=[],
    )

    assert generated.latest_version is not None
    assert generated.latest_version.version_number == 1
    assert generated.version_count == 1
    claims = _substantive_claim_text(generated)
    assert "python" in claims
    assert "sql" in claims
    assert "concrete project" not in claims
    assert "investigate technical skills" not in claims
    _assert_no_blank_or_none_bullets(generated)
    assert generated.application_snippets == []


def test_skill_memory_exposes_only_capabilities_named_by_direct_proof(
    rich_package_fixture: RichPackageFixture,
) -> None:
    """One supported skill must not unlock unsupported selection metadata."""

    fixture = rich_package_fixture
    skill_memory_id = _seed_nullable_skill_memory(
        fixture.user_id,
        with_direct_evidence=True,
        direct_evidence_skills=("Python",),
    )

    with SessionLocal() as session:
        profile = CareerMemoryCompiler(user_id=fixture.user_id).compile(
            session, skill_memory_id, target_role="Data Analytics Intern"
        )
    assert {"Python", "SQL"}.issubset(set(profile.skills_demonstrated))

    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[skill_memory_id],
        role_title="Data Analytics Intern",
        target_description="Use Python and SQL to analyze data.",
        required_skills=["Python", "SQL"],
        application_questions=[],
    )
    claims = _substantive_claim_text(generated)

    assert "python" in claims
    assert "sql" not in claims
    assert generated.latest_version is not None
    assert all(
        "sql" not in {tool.casefold() for tool in item.tools_claimed}
        for item in generated.latest_version.claim_ledger
    )
    assert "sql" in {
        item.requirement.casefold()
        for item in generated.warnings
        if item.code == "UNSUPPORTED_TARGET_REQUIREMENT" and item.requirement
    }


def test_all_four_memories_generate_with_separate_evidence_groups(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    skill_memory_id = _seed_nullable_skill_memory(
        fixture.user_id,
        with_direct_evidence=True,
    )
    galaxy_memory_id = _seed_galaxy_vip_memory(fixture.user_id)
    selected_ids = [
        fixture.seeded.gas_memory_id,
        fixture.seeded.unicorn_memory_id,
        skill_memory_id,
        galaxy_memory_id,
    ]

    generated = _create_and_generate(
        fixture,
        selected_memory_ids=selected_ids,
        role_title="Data",
        target_description=(
            "Analyze scientific data, review image quality, synthesize evidence, "
            "and communicate findings."
        ),
        application_questions=[],
    )

    assert generated.selected_memory_ids == selected_ids
    assert set(generated.memory_ids_used) == set(selected_ids)
    assert generated.latest_version is not None
    assert generated.latest_version.version_number == 1
    assert generated.version_count == 1
    assert generated.latest_version.validation_summary.status == "PASS"
    assert generated.application_snippets == []
    _assert_no_blank_or_none_bullets(generated)

    groups_by_memory = {
        group.memory_id: group
        for group in generated.evidence_groups
        if group.memory_id is not None
    }
    assert set(groups_by_memory) == set(selected_ids)
    for memory_id in selected_ids:
        group = groups_by_memory[memory_id]
        assert group.direct_proof or group.approved_enrichment

    gas_bullets = _bullets_for_memory_title(generated, GAS_TITLE)
    unicorn_bullets = _bullets_for_memory_title(generated, UNICORN_TITLE)
    galaxy_bullets = _bullets_for_memory_title(generated, GALAXY_VIP_TITLE)
    for gas_only in ("h-alpha", "nirspec", "galfit", "ceers", "velocity dispersion"):
        assert gas_only not in unicorn_bullets
        assert gas_only not in galaxy_bullets
    for unicorn_only in ("t-sne", "detection review", "hot pixels"):
        assert unicorn_only not in gas_bullets
        assert unicorn_only not in galaxy_bullets


def test_title_only_project_shortcuts_require_substantive_proof_and_keep_provenance(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    placeholder_title = "The UNICORN Project Placeholder"
    with SessionLocal.begin() as session:
        sparse = session.get(CanonicalMemoryRecord, fixture.seeded.sparse_memory_id)
        assert sparse is not None
        sparse.title = placeholder_title
        sparse.structured_fields = {
            "title": placeholder_title,
            "summary": "A short title-only note.",
        }
        sparse.confidence = Decimal("0.990")
        session.add(
            _enrichment(
                user_id=fixture.user_id,
                memory_id=sparse.id,
                memory_title=placeholder_title,
                status="APPROVED",
                structured={"findings_or_results": ["The work improved organization."]},
            )
        )

    exact_title_target = _create_and_generate(
        fixture,
        selected_memory_ids=[
            fixture.seeded.sparse_memory_id,
            fixture.seeded.gas_memory_id,
        ],
        role_title=placeholder_title,
        target_description=f"Review {placeholder_title} context.",
    )
    assert exact_title_target.latest_version is not None
    assert placeholder_title in (
        exact_title_target.positioning_summary.primary_positioning
        if exact_title_target.positioning_summary
        else ""
    )
    assert "limited project context" in (
        exact_title_target.positioning_summary.primary_positioning.casefold()
        if exact_title_target.positioning_summary
        else ""
    )
    positioning_entries = [
        item
        for item in exact_title_target.latest_version.claim_ledger
        if item.surface == "positioning"
    ]
    assert positioning_entries
    assert all(
        item.memory_ids == [fixture.seeded.sparse_memory_id]
        for item in positioning_entries
    )
    assert not any(
        "unicorn demonstrates data-quality" in question.casefold()
        for question in exact_title_target.reviewer_questions
    )

    ai_target = _create_and_generate(
        fixture,
        selected_memory_ids=[
            fixture.seeded.sparse_memory_id,
            fixture.seeded.gas_memory_id,
        ],
        role_title="AI Engineer Intern",
        target_description="Review image labeling data quality.",
    )
    assert ai_target.positioning_summary is not None
    assert GAS_TITLE in ai_target.positioning_summary.primary_positioning
    assert all(
        "strong role match" not in reason.casefold()
        for reason in ai_target.positioning_summary.recommended_emphasis
        if placeholder_title in reason
    )


def test_negated_limitations_do_not_count_as_aws_or_deployment_support(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    _add_approved_limitation(
        fixture,
        "No AWS experience or production ML deployment was part of this project.",
    )
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.gas_memory_id],
        role_title="Cloud ML Engineer Intern",
        target_description="Operate models on AWS in a production ML deployment.",
        required_skills=["AWS", "production ML deployment"],
    )

    unsupported = {
        item.requirement
        for item in generated.warnings
        if item.code == "UNSUPPORTED_TARGET_REQUIREMENT"
    }
    assert {"AWS", "production ML deployment"} <= unsupported
    assert {
        "Unsupported target requirement: AWS",
        "Unsupported target requirement: production ML deployment",
    } <= set(generated.unsupported_claims)


def test_custom_ai_and_c_requirements_use_token_boundaries(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    _add_approved_limitation(
        fixture,
        "A remaining detail was uncertain and required careful documentation.",
    )
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.gas_memory_id],
        role_title="Software and AI Intern",
        target_description="Build AI software in C.",
        required_skills=["AI", "C"],
    )

    unsupported = {
        item.requirement
        for item in generated.warnings
        if item.code == "UNSUPPORTED_TARGET_REQUIREMENT"
    }
    assert {"AI", "C"} <= unsupported
    claims = _substantive_claim_text(generated)
    assert "experience with ai" not in claims
    assert "programmed in c" not in claims


def test_numeric_edit_audit_normalizes_magnitude_suffixes_without_expanding_scope() -> (
    None
):
    memory_id = uuid.uuid4()
    target_snapshot: dict[str, object] = {}
    supported_snapshot = [
        {
            "memory_id": str(memory_id),
            "resume_bullet_claims": ["Analyzed 30,000 samples."],
        }
    ]
    abbreviated = _EditedClaim(
        claim_id="resume-1-1",
        surface="resume",
        text="Analyzed 30K samples.",
        memory_ids=(memory_id,),
    )
    assert (
        ApplicationPackageService._unsupported_numbers_for_claims(
            [abbreviated], supported_snapshot, target_snapshot
        )
        == []
    )

    smaller_snapshot = [
        {
            "memory_id": str(memory_id),
            "resume_bullet_claims": ["Analyzed 30 samples."],
        }
    ]
    assert ApplicationPackageService._unsupported_numbers_for_claims(
        [abbreviated], smaller_snapshot, target_snapshot
    ) == ["30000"]
    assert ApplicationPackageService._normalize_numeric_token("2.5M") == "2500000"
    assert ApplicationPackageService._normalize_numeric_token("10x") == "10x"


def test_resume_cover_letter_and_snippets_have_human_readable_evidence_traces(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[
            fixture.seeded.gas_memory_id,
            fixture.seeded.unicorn_memory_id,
        ],
        role_title="Data and AI Intern",
        target_description=(
            "Data analysis, uncertainty, image data quality, labeling, and "
            "technical communication."
        ),
    )
    latest = generated.latest_version
    assert latest is not None

    for group in generated.resume_bullets:
        assert group.bullets
        for bullet in group.bullets:
            assert bullet.evidence_trace
            assert any(
                trace.support_type is EvidenceSupportType.DIRECT
                and trace.memory_id == group.memory_id
                for trace in bullet.evidence_trace
            )
            assert all(trace.source_label.strip() for trace in bullet.evidence_trace)

    assert generated.cover_letter is not None
    paragraph_traces = generated.cover_letter.evidence_trace_by_paragraph
    assert {item.paragraph_label for item in paragraph_traces} >= {
        "opening",
        "body_1",
        "closing",
    }
    for paragraph in paragraph_traces:
        assert paragraph.paragraph_text.strip()
        assert paragraph.evidence_trace
        if paragraph.paragraph_label != "closing":
            assert any(
                item.support_type is EvidenceSupportType.DIRECT
                for item in paragraph.evidence_trace
            )

    assert [item.question_id for item in generated.application_snippets] == [
        "motivation",
        "complex-data-project",
        "quality-reliability",
    ]
    for snippet in generated.application_snippets:
        assert snippet.text.strip()
        assert snippet.evidence_trace
        assert any(
            item.support_type is EvidenceSupportType.DIRECT
            for item in snippet.evidence_trace
        )

    direct_labels = [
        item.source_label
        for item in generated.evidence_trace
        if item.support_type is EvidenceSupportType.DIRECT
    ]
    assert any("approved memory" in item.casefold() for item in direct_labels)
    assert any("approved enrichment" in item.casefold() for item in direct_labels)
    assert any(GAS_TITLE in item for item in direct_labels)
    assert any(UNICORN_TITLE in item for item in direct_labels)
    assert {entry.surface for entry in latest.claim_ledger} >= {
        "positioning",
        "resume",
        "cover_letter",
        "snippet",
    }


def test_claim_traces_include_every_approved_direct_source(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    extra_enrichment_ids: set[uuid.UUID] = set()
    with SessionLocal.begin() as session:
        for index in range(3):
            enrichment = _enrichment(
                user_id=fixture.user_id,
                memory_id=fixture.seeded.gas_memory_id,
                memory_title=GAS_TITLE,
                status="APPROVED",
                source_label=f"Supplemental reviewed source {index}",
                structured={
                    "tools_or_methods": [f"supplemental reviewed method {index}"]
                },
            )
            session.add(enrichment)
            session.flush()
            extra_enrichment_ids.add(enrichment.id)

    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.gas_memory_id],
        role_title="Data Science Intern",
        target_description="Analyze data and communicate uncertainty.",
    )
    aggregate_direct_ids = {
        item.trace_id
        for item in generated.evidence_trace
        if item.memory_id == fixture.seeded.gas_memory_id
        and item.support_type is EvidenceSupportType.DIRECT
    }
    assert extra_enrichment_ids <= set(generated.enrichment_ids_used)
    assert len(aggregate_direct_ids) >= len(extra_enrichment_ids) + 2
    for group in generated.resume_bullets:
        for bullet in group.bullets:
            bullet_direct_ids = {
                item.trace_id
                for item in bullet.evidence_trace
                if item.support_type is EvidenceSupportType.DIRECT
            }
            assert bullet_direct_ids == aggregate_direct_ids


def test_output_edits_ignore_client_trace_and_identity_injection(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    service = _application_package_service(fixture.user_id)
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.gas_memory_id],
        role_title="Data Science Intern",
        target_description="Analyze data and communicate uncertainty.",
    )
    assert generated.latest_version is not None
    original_group = generated.latest_version.outputs.resume_bullets[0]
    original_bullet = original_group.bullets[0]
    original_trace_ids = [item.trace_id for item in original_bullet.evidence_trace]
    injected_memory_id = uuid.uuid4()
    injected_enrichment_id = uuid.uuid4()
    injected_trace_id = f"forged-{uuid.uuid4()}"

    groups = _resume_edit_payload(
        generated,
        original_bullet.bullet_text + " Reviewed for clarity.",
    )
    groups[0]["memory_id"] = str(injected_memory_id)
    groups[0]["memory_title"] = "Forged foreign memory"
    bullets = groups[0]["bullets"]
    assert isinstance(bullets, list) and bullets
    assert isinstance(bullets[0], dict)
    bullets[0]["evidence_trace"] = [
        {
            "trace_id": injected_trace_id,
            "source_type": "APPROVED_ENRICHMENT",
            "support_type": "DIRECT",
            "source_label": "Forged approved proof",
            "detail": "Client-supplied proof must never become authoritative.",
            "memory_id": str(injected_memory_id),
            "memory_title": "Forged foreign memory",
            "evidence_id": "forged-evidence-id",
            "enrichment_id": str(injected_enrichment_id),
        }
    ]

    with SessionLocal() as session:
        edited = service.update_outputs(
            session,
            generated.package_id,
            ApplicationPackageOutputsUpdateRequest.model_validate(
                {"resume_bullets": groups, "edit_summary": "Clarity edit"}
            ),
        )

    assert edited.latest_version is not None
    saved_group = edited.latest_version.outputs.resume_bullets[0]
    saved_bullet = saved_group.bullets[0]
    assert saved_group.memory_id == original_group.memory_id
    assert saved_group.memory_title == original_group.memory_title
    assert [item.trace_id for item in saved_bullet.evidence_trace] == original_trace_ids
    serialized = edited.latest_version.model_dump_json()
    assert injected_trace_id not in serialized
    assert str(injected_memory_id) not in serialized
    assert str(injected_enrichment_id) not in serialized
    edited_resume_entries = [
        item
        for item in edited.latest_version.claim_ledger
        if item.surface == "resume" and item.user_edited
    ]
    assert edited_resume_entries
    assert all(
        item.support_level == "user_review_required" for item in edited_resume_entries
    )


def test_cross_memory_edit_is_blocking_until_corrected_and_cannot_be_ready(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    service = _application_package_service(fixture.user_id)
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.unicorn_memory_id],
        role_title="AI Engineer Intern",
        target_description="Review image data quality and labeling workflows.",
    )
    assert generated.latest_version is not None
    original_bullet = generated.latest_version.outputs.resume_bullets[0].bullets[0]
    gas_only_edit = (
        "Analyzed H-alpha gas velocity dispersion from JWST/NIRSpec spectra for "
        "the Gas Kinematics capstone."
    )

    with SessionLocal() as session:
        blocked = service.update_outputs(
            session,
            generated.package_id,
            ApplicationPackageOutputsUpdateRequest(
                resume_bullets=_resume_edit_payload(generated, gas_only_edit),
                edit_summary="Add a stronger technical claim.",
            ),
        )
        blocking_warnings = [
            item for item in blocked.warnings if item.severity.value == "BLOCKING"
        ]
        assert blocking_warnings
        blocking_text = " ".join(
            [
                *(item.message for item in blocking_warnings),
                *blocked.unsupported_claims,
            ]
        ).casefold()
        assert any(
            marker in blocking_text
            for marker in ("h-alpha", "gas kinematics", "jwst/nirspec")
        )

        with pytest.raises(
            ApplicationPackageValidationError,
            match="blocking claim warnings",
        ):
            service.update(
                session,
                generated.package_id,
                ApplicationPackageUpdateRequest(status=ApplicationPackageStatus.READY),
            )

        corrected = service.update_outputs(
            session,
            generated.package_id,
            ApplicationPackageOutputsUpdateRequest(
                resume_bullets=_resume_edit_payload(
                    blocked,
                    original_bullet.bullet_text,
                ),
                edit_summary="Remove the unsupported cross-project claim.",
            ),
        )
        assert not [
            item for item in corrected.warnings if item.severity.value == "BLOCKING"
        ]
        corrected_unsupported = " ".join(corrected.unsupported_claims).casefold()
        assert "cross-memory edited claim:" not in corrected_unsupported
        assert all(
            item.code != "CROSS_MEMORY_EDITED_CLAIM" for item in corrected.warnings
        )
        ready = service.update(
            session,
            generated.package_id,
            ApplicationPackageUpdateRequest(status=ApplicationPackageStatus.READY),
        )

    assert ready.status == ApplicationPackageStatus.READY


def test_edit_audit_ignores_unchanged_target_numbers_but_blocks_new_claims(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    service = _application_package_service(fixture.user_id)
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.gas_memory_id],
        role_title="2026 AWS Cloud Intern",
        company="3M",
        target_description="Support AWS cloud services.",
        required_skills=["AWS", "ISO 27001"],
    )
    assert generated.latest_version is not None
    cover = generated.latest_version.outputs.cover_letter.model_dump(mode="json")
    cover["full_text"] = cover["full_text"].replace(
        "Dear 3M Hiring Team,", "Dear 3M Talent Team,", 1
    )
    cover["full_text"] = cover["full_text"].replace(
        "I am applying", "I am excited to apply", 1
    )
    cover["full_text"] += (
        "\n\nI am interested in learning more about ISO 27001.\n\nThank you."
    )

    with SessionLocal() as session:
        reviewed = service.update_outputs(
            session,
            generated.package_id,
            ApplicationPackageOutputsUpdateRequest.model_validate(
                {"cover_letter": cover, "edit_summary": "Polish the closing."}
            ),
        )

    unexpected_edit_warnings = {
        "UNSUPPORTED_EDITED_NUMBER",
        "UNSUPPORTED_EDITED_CLAIM",
    }.intersection(item.code for item in reviewed.warnings)
    assert not unexpected_edit_warnings, [
        (item.code, item.message)
        for item in reviewed.warnings
        if item.code in unexpected_edit_warnings
    ]
    assert reviewed.latest_version is not None
    unsupported_cover = reviewed.latest_version.outputs.cover_letter.model_dump(
        mode="json"
    )
    unsupported_cover["full_text"] = (
        "Dear Hiring Team,\n\nI analyzed 2026 samples, led 30 engineers, served "
        "30K users, implemented ISO 27001, and improved output 10x using "
        "AWS.\n\nThank you."
    )

    with SessionLocal() as session:
        blocked = service.update_outputs(
            session,
            generated.package_id,
            ApplicationPackageOutputsUpdateRequest.model_validate(
                {
                    "cover_letter": unsupported_cover,
                    "edit_summary": "Add an unsupported factual claim.",
                }
            ),
        )
        warning_codes = {item.code for item in blocked.warnings}
        assert {
            "UNSUPPORTED_EDITED_NUMBER",
            "UNSUPPORTED_EDITED_CLAIM",
        } <= warning_codes
        numeric_warning = next(
            item
            for item in blocked.warnings
            if item.code == "UNSUPPORTED_EDITED_NUMBER"
        )
        assert {"10x", "30", "2026", "27001", "30000"} <= {
            item.casefold()
            for item in re.findall(
                r"(?<!\w)(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
                r"(?:%|[kmbx])?(?!\w)",
                numeric_warning.message,
                flags=re.IGNORECASE,
            )
        }
        with pytest.raises(
            ApplicationPackageValidationError,
            match="blocking claim warnings",
        ):
            service.update(
                session,
                generated.package_id,
                ApplicationPackageUpdateRequest(status=ApplicationPackageStatus.READY),
            )


def test_versions_are_immutable_and_target_or_selection_changes_are_stale(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    service = _application_package_service(fixture.user_id)
    with SessionLocal() as session:
        created = service.create(
            session,
            ApplicationPackageCreateRequest(
                role_title="Data Science Intern",
                target_description="Model data and communicate uncertainty.",
                selected_memory_ids=[fixture.seeded.gas_memory_id],
            ),
        )
        first = service.generate(session, created.package_id)
        first_version = first.latest_version
        assert first_version is not None
        first_outputs = first_version.outputs.model_dump(mode="json")
        ready = service.update(
            session,
            created.package_id,
            ApplicationPackageUpdateRequest(status=ApplicationPackageStatus.READY),
        )
        assert ready.status == ApplicationPackageStatus.READY

        changed_target = service.update(
            session,
            created.package_id,
            ApplicationPackageUpdateRequest(
                target_description="Review image data quality for an AI workflow."
            ),
        )
        assert changed_target.is_stale is True
        assert changed_target.status == ApplicationPackageStatus.DRAFT

        changed_selection = service.update(
            session,
            created.package_id,
            ApplicationPackageUpdateRequest(
                selected_memory_ids=[fixture.seeded.unicorn_memory_id]
            ),
        )
        assert changed_selection.is_stale is True
        assert changed_selection.selected_memory_ids == [
            fixture.seeded.unicorn_memory_id
        ]
        assert changed_selection.latest_version is not None
        assert changed_selection.latest_version.selected_memory_ids == [
            fixture.seeded.gas_memory_id
        ]

        with pytest.raises(ApplicationPackageValidationError, match="Regenerate"):
            service.update_outputs(
                session,
                created.package_id,
                ApplicationPackageOutputsUpdateRequest(
                    reviewer_questions=["Stale edit must not be saved."]
                ),
            )
        with pytest.raises(ApplicationPackageValidationError, match="Regenerate"):
            service.update(
                session,
                created.package_id,
                ApplicationPackageUpdateRequest(status=ApplicationPackageStatus.READY),
            )

        regenerated = service.regenerate(session, created.package_id)

    assert regenerated.is_stale is False
    assert regenerated.version_count == 2
    assert regenerated.latest_version is not None
    assert regenerated.latest_version.version_number == 2
    assert regenerated.latest_version.selected_memory_ids == [
        fixture.seeded.unicorn_memory_id
    ]
    assert regenerated.latest_version.memory_ids_used == [
        fixture.seeded.unicorn_memory_id
    ]
    historical = regenerated.versions[1]
    assert historical.id == first_version.id
    assert historical.version_number == 1
    assert historical.selected_memory_ids == [fixture.seeded.gas_memory_id]
    assert historical.memory_ids_used == [fixture.seeded.gas_memory_id]
    assert historical.outputs.model_dump(mode="json") == first_outputs
    assert historical.target_snapshot["target_description"] == (
        "Model data and communicate uncertainty."
    )
    assert historical.input_fingerprint != regenerated.latest_version.input_fingerprint


def test_stale_ready_package_is_exposed_as_draft_after_memory_changes(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    service = _application_package_service(fixture.user_id)
    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[fixture.seeded.gas_memory_id],
        role_title="Data Science Intern",
        target_description="Analyze data and communicate uncertainty.",
    )
    with SessionLocal() as session:
        ready = service.update(
            session,
            generated.package_id,
            ApplicationPackageUpdateRequest(status=ApplicationPackageStatus.READY),
        )
    assert ready.status == ApplicationPackageStatus.READY

    with SessionLocal.begin() as session:
        memory = session.get(CanonicalMemoryRecord, fixture.seeded.gas_memory_id)
        assert memory is not None
        memory.title = f"{memory.title} (reviewed update)"

    with SessionLocal() as session:
        detail = service.get(session, generated.package_id)
        listed = next(
            item
            for item in service.list(session, include_archived=True)
            if item.package_id == generated.package_id
        )

    assert detail.is_stale is True
    assert detail.status == ApplicationPackageStatus.DRAFT
    assert listed.is_stale is True
    assert listed.status == ApplicationPackageStatus.DRAFT


def test_proof_suggestions_only_attach_ready_artifacts(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    with SessionLocal() as session:
        artifact = ProofArtifactService(user_id=fixture.user_id).create(
            session,
            ProofArtifactCreateRequest(
                source_memory_id=fixture.seeded.gas_memory_id,
                target_role="Data Science Intern",
            ),
        )

    generated = _create_and_generate(
        fixture,
        selected_memory_ids=[
            fixture.seeded.gas_memory_id,
            fixture.seeded.unicorn_memory_id,
        ],
        role_title="Data and AI Intern",
        target_description="Data analysis, uncertainty, image review, and labeling.",
    )
    suggestions = {item.memory_id: item for item in generated.suggested_proof_artifacts}
    gas = suggestions[fixture.seeded.gas_memory_id]
    unicorn = suggestions[fixture.seeded.unicorn_memory_id]
    assert gas.action in {"REVIEW", "FINISH"}
    assert gas.action != "ATTACH"
    assert gas.artifact_id == artifact.id
    assert gas.artifact_title == artifact.title
    assert any(term in gas.reason.casefold() for term in ("review", "finish", "draft"))
    assert unicorn.action == "BUILD"
    assert unicorn.artifact_id is None
    assert "short case study" in unicorn.reason

    with SessionLocal() as session:
        ProofArtifactService(user_id=fixture.user_id).update(
            session,
            artifact.id,
            ProofArtifactUpdateRequest(status=ProofArtifactStatus.READY),
        )
        regenerated = _application_package_service(fixture.user_id).regenerate(
            session,
            generated.package_id,
        )

    ready_gas = {
        item.memory_id: item for item in regenerated.suggested_proof_artifacts
    }[fixture.seeded.gas_memory_id]
    assert ready_gas.action == "ATTACH"
    assert ready_gas.artifact_id == artifact.id


def test_application_package_api_crud_generate_edit_regenerate_and_archive(
    rich_package_fixture: RichPackageFixture,
) -> None:
    fixture = rich_package_fixture
    service = _application_package_service(fixture.user_id)
    original_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_application_package_service] = lambda: service
    try:
        with TestClient(app) as client:
            eligible = client.get(
                "/api/application-packages/eligible-memories",
                params={"target_role": "Data Analytics Intern"},
            )
            created = client.post(
                "/api/application-packages",
                json={
                    "display_name": "Test application package",
                    "role_title": "Data Analytics Intern",
                    "company": "Test Company",
                    "location": "Remote",
                    "job_type": "Internship",
                    "target_description": (
                        "Analyze data, validate models, reason about uncertainty, "
                        "and communicate findings."
                    ),
                    "required_skills": ["data analysis", "modeling"],
                    "preferred_skills": ["technical communication"],
                    "responsibilities": ["Validate analytical results"],
                    "application_questions": [
                        question.model_dump(mode="json")
                        for question in _required_application_questions()
                    ],
                    "selected_memory_ids": [str(fixture.seeded.gas_memory_id)],
                },
            )
            assert eligible.status_code == 200
            assert str(fixture.seeded.gas_memory_id) in {
                item["id"] for item in eligible.json()
            }
            assert created.status_code == 201
            created_body = created.json()
            package_id = created_body["package_id"]
            assert created_body["role_title"] == "Data Analytics Intern"
            assert created_body["latest_version"] is None
            assert created_body["version_count"] == 0

            listed = client.get("/api/application-packages")
            detail = client.get(f"/api/application-packages/{package_id}")
            updated = client.patch(
                f"/api/application-packages/{package_id}",
                json={"display_name": "Reviewed test package"},
            )
            generated = client.post(
                f"/api/application-packages/{package_id}/generate",
                json={},
            )
            assert listed.status_code == 200
            assert listed.json()[0]["package_id"] == package_id
            assert detail.status_code == 200
            assert updated.status_code == 200
            assert updated.json()["display_name"] == "Reviewed test package"
            assert generated.status_code == 200
            generated_body = generated.json()
            assert generated_body["version_count"] == 1
            assert generated_body["latest_version"]["generation_reason"] == (
                "GENERATED"
            )
            assert generated_body["resume_bullets"]
            assert generated_body["cover_letter"]["full_text"]
            assert [
                item["question_id"]
                for item in generated_body["application_snippets"]
            ] == [
                "motivation",
                "complex-data-project",
                "quality-reliability",
            ]
            assert generated_body["evidence_trace"]

            original_cover_text = generated_body["cover_letter"]["full_text"]
            edited_cover = dict(generated_body["cover_letter"])
            edited_cover["full_text"] = (
                original_cover_text + "\n\nManually reviewed for this application."
            )
            edited = client.patch(
                f"/api/application-packages/{package_id}/outputs",
                json={
                    "cover_letter": edited_cover,
                    "edit_summary": "Reviewed the closing copy.",
                },
            )
            assert edited.status_code == 200
            edited_body = edited.json()
            assert edited_body["version_count"] == 2
            assert edited_body["latest_version"]["generation_reason"] == "USER_EDIT"
            assert edited_body["cover_letter"]["full_text"].endswith(
                "Manually reviewed for this application."
            )
            assert (
                edited_body["versions"][1]["outputs"]["cover_letter"]["full_text"]
                == original_cover_text
            )
            cover_entries = [
                entry
                for entry in edited_body["latest_version"]["claim_ledger"]
                if entry["surface"] == "cover_letter"
            ]
            assert next(
                entry
                for entry in cover_entries
                if entry["claim_id"] == "cover-letter-full"
            )["user_edited"]
            assert all(
                not entry["user_edited"]
                for entry in cover_entries
                if entry["claim_id"] != "cover-letter-full"
            )

            regenerated = client.post(
                f"/api/application-packages/{package_id}/regenerate",
                json={},
            )
            ready = client.patch(
                f"/api/application-packages/{package_id}",
                json={"status": "READY"},
            )
            archived = client.patch(
                f"/api/application-packages/{package_id}",
                json={"status": "ARCHIVED"},
            )
            default_list = client.get("/api/application-packages")
            archived_list = client.get(
                "/api/application-packages",
                params={"include_archived": True},
            )
            final_detail = client.get(f"/api/application-packages/{package_id}")

        assert regenerated.status_code == 200
        regenerated_body = regenerated.json()
        assert regenerated_body["version_count"] == 3
        assert regenerated_body["latest_version"]["version_number"] == 3
        assert regenerated_body["latest_version"]["generation_reason"] == (
            "REGENERATED"
        )
        assert regenerated_body["versions"][1]["outputs"]["cover_letter"][
            "full_text"
        ].endswith("Manually reviewed for this application.")
        assert ready.status_code == 200
        assert ready.json()["status"] == "READY"
        assert archived.status_code == 200
        assert archived.json()["status"] == "ARCHIVED"
        assert default_list.status_code == 200
        assert all(item["package_id"] != package_id for item in default_list.json())
        assert archived_list.status_code == 200
        assert any(item["package_id"] == package_id for item in archived_list.json())
        assert final_detail.status_code == 200
        assert final_detail.json()["status"] == "ARCHIVED"
        assert final_detail.json()["created_at"]
        assert final_detail.json()["updated_at"]
    finally:
        app.dependency_overrides = original_overrides

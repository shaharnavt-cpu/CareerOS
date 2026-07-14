"""Regression coverage for Application Intelligence."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.applications import get_application_service
from app.db.session import SessionLocal, engine
from app.main import app
from app.models import (
    ApplicationDraft,
    ApplicationMemoryMatch,
    ApplicationOpportunity,
    ApplicationQuestion,
    CanonicalMemoryRecord,
    CareerMemoryEnrichment,
    ListeningEvidence,
    ListeningSource,
    ReviewProposal,
    User,
)
from app.schemas.applications import (
    ApplicationDraftLength,
    ApplicationDraftRequest,
    ApplicationDraftStatus,
    ApplicationDraftType,
    ApplicationDraftUpdateRequest,
    ApplicationOpportunityCreateRequest,
)
from app.services.application_intelligence import ApplicationIntelligenceService

SAMPLE_OPPORTUNITY = """
Data Analytics Intern

We are looking for a student intern to support data analysis, reporting, and
business insight generation. Responsibilities include cleaning data, using
Python or SQL to analyze datasets, creating summaries or visuals, and
communicating findings to non-technical stakeholders. Preferred qualifications
include experience with Excel, Python, SQL, analytics coursework, and project
experience translating data into recommendations.

Application question:
Tell us about a project or experience that prepared you for this analytics internship.
"""


def _require_postgres() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")


def _cleanup_user(user_id: uuid.UUID) -> None:
    with SessionLocal.begin() as session:
        session.execute(
            delete(CareerMemoryEnrichment).where(
                CareerMemoryEnrichment.user_id == user_id
            )
        )
        for model in (
            ApplicationDraft,
            ApplicationMemoryMatch,
            ApplicationQuestion,
            ApplicationOpportunity,
            CanonicalMemoryRecord,
            ReviewProposal,
        ):
            session.execute(delete(model).where(model.user_id == user_id))
        session.execute(
            delete(ListeningEvidence).where(ListeningEvidence.user_id == user_id)
        )
        session.execute(
            delete(ListeningSource).where(ListeningSource.user_id == user_id)
        )
        session.execute(delete(User).where(User.id == user_id))


def _seed_memory(user_id: uuid.UUID) -> dict[str, CanonicalMemoryRecord]:
    memories: dict[str, CanonicalMemoryRecord] = {}
    payloads = [
        (
            "skill",
            "SKILL_SET",
            "Technical Skills",
            {
                "name": "Technical Skills",
                "category": "Technical Skills",
                "skills": ["Python", "SQL", "MySQL", "Excel", "R", "LaTeX"],
            },
            ["skill-evidence"],
        ),
        (
            "project",
            "PROJECT",
            "Gas Kinematics Honors Capstone",
            {
                "title": "Gas Kinematics Honors Capstone",
                "summary": "Python data analysis and visualization project.",
            },
            ["project-evidence"],
        ),
        (
            "experience",
            "EXPERIENCE",
            "Undergraduate Learning Assistant",
            {
                "title": "Undergraduate Learning Assistant",
                "organization_name": "University of Texas at Austin",
                "responsibilities": [
                    "Communicated technical ideas to non-technical students."
                ],
            },
            ["experience-evidence"],
        ),
        (
            "education",
            "EDUCATION",
            "UT Dallas MS Business Analytics and AI",
            {
                "institution_name": "University of Texas at Dallas",
                "degree": "Master of Science",
                "field_of_study": "Business Analytics and AI",
            },
            ["education-evidence"],
        ),
    ]
    with SessionLocal.begin() as session:
        session.add(
            User(
                id=user_id,
                clerk_user_id=f"application-test-{user_id}",
                email=f"application-test-{user_id}@example.invalid",
                display_name="Application Test User",
            )
        )
        session.flush()
        for key, memory_type, title, fields, evidence_ids in payloads:
            proposal_id = f"approved-{key}-{user_id}"
            session.add(
                ReviewProposal(
                    id=proposal_id,
                    user_id=user_id,
                    proposal_type=memory_type,
                    entity_type="SKILL" if memory_type == "SKILL_SET" else memory_type,
                    title=title,
                    identity_key=f"{key}-{user_id}",
                    proposal_data={"id": proposal_id, "title": title},
                    decision="APPROVED",
                )
            )
            session.flush()
            memory = CanonicalMemoryRecord(
                user_id=user_id,
                identity_key=f"{key}-{user_id}",
                memory_type=memory_type,
                title=title,
                structured_fields=fields,
                evidence_ids=evidence_ids,
                source_ids=["resume-source"],
                confidence=Decimal("0.92"),
                review_proposal_id=proposal_id,
                typed_entity_id=uuid.uuid4(),
            )
            session.add(memory)
            memories[key] = memory
        session.add(
            ReviewProposal(
                id=f"rejected-{user_id}",
                user_id=user_id,
                proposal_type="PROJECT",
                entity_type="PROJECT",
                title="Rejected Tableau Project",
                identity_key=f"rejected-{user_id}",
                proposal_data={"title": "Rejected Tableau Project"},
                decision="REJECTED",
            )
        )
    return memories


def _attach_compiled_project_provenance(
    user_id: uuid.UUID,
    memory_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
    with SessionLocal.begin() as session:
        source = ListeningSource(
            user_id=user_id,
            source_type="MANUAL",
            label="Reviewed Gas Kinematics notes",
            raw_text="Reviewed capstone methods and findings.",
            source_metadata={},
            provenance={},
            content_hash=f"application-provenance-{user_id}",
            adapter_version="application-test-v1",
            status="READY",
        )
        session.add(source)
        session.flush()
        evidence = ListeningEvidence(
            user_id=user_id,
            source_id=source.id,
            source_type="MANUAL",
            raw_excerpt=(
                "Used Python to analyze astronomy datasets and communicate a "
                "careful no-clear-trend result."
            ),
            normalized_excerpt=None,
            excerpt_hash=f"application-provenance-evidence-{user_id}",
            category="PROJECT",
            confidence=Decimal("0.950"),
            location={},
            provenance={},
        )
        session.add(evidence)
        session.flush()
        memory = session.get(CanonicalMemoryRecord, memory_id)
        assert memory is not None
        memory.evidence_ids = [str(evidence.id)]
        memory.source_ids = [str(source.id)]
        enrichment = CareerMemoryEnrichment(
            user_id=user_id,
            canonical_memory_id=memory.id,
            source_id=source.id,
            source_label=source.label,
            status="APPROVED",
            enrichment_type="PROJECT_FULL_ENRICHMENT",
            structured_enrichment={
                "research_question_or_problem": (
                    "Test whether gas kinematics relates to galaxy morphology."
                ),
                "data_or_inputs": ["Astronomy datasets"],
                "methods": ["Python data analysis and validation"],
                "findings_or_results": ["No clear overall trend"],
                "outputs": ["Technical report"],
            },
            evidence_ids=[str(evidence.id)],
            confidence=Decimal("0.940"),
            reasoning="The user reviewed these details for this exact project.",
            identity_resolution={
                "resolution": "ENRICH_EXISTING",
                "matched_memory_id": str(memory.id),
            },
            warnings=[],
        )
        session.add(enrichment)
        session.flush()
        return evidence.id, enrichment.id


def test_opportunity_text_is_parsed_into_skills_themes_and_questions() -> None:
    service = ApplicationIntelligenceService()

    analysis = service.analyze_text(SAMPLE_OPPORTUNITY)

    assert analysis.title == "Data Analytics Intern"
    assert {"Python", "SQL", "Excel"}.issubset(set(analysis.skills))
    assert "Communication" in analysis.keywords
    assert analysis.questions == [
        "Tell us about a project or experience that prepared you for this "
        "analytics internship."
    ]


def test_matching_uses_approved_memory_and_excludes_rejected_proposals() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    service = ApplicationIntelligenceService(user_id=user_id)

    try:
        with SessionLocal() as session:
            opportunity = service.create_opportunity(
                session,
                ApplicationOpportunityCreateRequest(raw_text=SAMPLE_OPPORTUNITY),
            )

        titles = [match.memory.title for match in opportunity.matches]
        assert "Rejected Tableau Project" not in titles
        assert titles.index("Technical Skills") < len(titles)
        assert titles.index("Gas Kinematics Honors Capstone") < len(titles)
        assert opportunity.matches[0].match_score >= opportunity.matches[-1].match_score
        assert any(match.evidence_ids for match in opportunity.matches)
        assert "Reporting" in opportunity.gaps
    finally:
        _cleanup_user(user_id)


def test_compiled_match_and_draft_keep_provenance_kinds_separate() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    memories = _seed_memory(user_id)
    project_id = memories["project"].id
    evidence_id, enrichment_id = _attach_compiled_project_provenance(
        user_id,
        project_id,
    )
    service = ApplicationIntelligenceService(user_id=user_id)

    try:
        with SessionLocal() as session:
            opportunity = service.create_opportunity(
                session,
                ApplicationOpportunityCreateRequest(raw_text=SAMPLE_OPPORTUNITY),
            )
            project_match = next(
                match
                for match in opportunity.matches
                if match.canonical_memory_id == project_id
            )

            assert project_match.evidence_ids == [str(evidence_id)]
            assert project_match.approved_enrichment_ids == [enrichment_id]
            assert project_match.memory.evidence_ids == [str(evidence_id)]
            assert str(enrichment_id) not in project_match.evidence_ids
            assert str(enrichment_id) not in project_match.memory.evidence_ids

            stored_match = session.scalar(
                select(ApplicationMemoryMatch).where(
                    ApplicationMemoryMatch.opportunity_id == opportunity.id,
                    ApplicationMemoryMatch.question_id.is_(None),
                    ApplicationMemoryMatch.canonical_memory_id == project_id,
                )
            )
            assert stored_match is not None
            assert stored_match.evidence_ids == {
                "schema_version": "application-match-provenance-v1",
                "listening_evidence_ids": [str(evidence_id)],
                "approved_enrichment_ids": [str(enrichment_id)],
                "compiler_version": "career-memory-compiler-v1",
            }

            # Rows created during the short-lived conflation bug remain readable.
            stored_match.evidence_ids = [str(evidence_id), str(enrichment_id)]
            session.commit()
            legacy_view = service.get_opportunity(session, opportunity.id)
            legacy_project_match = next(
                match
                for match in legacy_view.matches
                if match.canonical_memory_id == project_id
            )
            assert legacy_project_match.evidence_ids == [str(evidence_id)]
            assert legacy_project_match.approved_enrichment_ids == [enrichment_id]

            draft_response = service.generate_draft(
                session,
                opportunity.id,
                ApplicationDraftRequest(
                    question_id=opportunity.questions[0].id,
                    draft_type=ApplicationDraftType.QUESTION_ANSWER,
                ),
            )

        assert str(evidence_id) in draft_response.evidence_used
        assert str(enrichment_id) not in draft_response.evidence_used
        assert draft_response.approved_enrichment_ids_used == [enrichment_id]
        assert str(evidence_id) in draft_response.draft.evidence_ids
        assert str(enrichment_id) not in draft_response.draft.evidence_ids
        assert draft_response.draft.approved_enrichment_ids == [enrichment_id]
        assert draft_response.draft.draft_metadata[
            "approved_enrichment_ids"
        ] == [str(enrichment_id)]
        project_draft_match = next(
            match
            for match in draft_response.matches_used
            if match.canonical_memory_id == project_id
        )
        assert project_draft_match.evidence_ids == [str(evidence_id)]
        assert project_draft_match.approved_enrichment_ids == [enrichment_id]
    finally:
        _cleanup_user(user_id)


def test_draft_generation_preserves_evidence_and_can_be_edited() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    service = ApplicationIntelligenceService(user_id=user_id)

    try:
        with SessionLocal() as session:
            opportunity = service.create_opportunity(
                session,
                ApplicationOpportunityCreateRequest(raw_text=SAMPLE_OPPORTUNITY),
            )
            draft = service.generate_draft(
                session,
                opportunity.id,
                ApplicationDraftRequest(
                    question_id=opportunity.questions[0].id,
                    draft_type=ApplicationDraftType.QUESTION_ANSWER,
                ),
            ).draft
            edited = service.update_draft(
                session,
                draft.id,
                ApplicationDraftUpdateRequest(
                    draft_text=draft.draft_text + " Edited by user.",
                    status=ApplicationDraftStatus.APPROVED,
                ),
            )

        assert "Gas Kinematics" in draft.draft_text
        assert draft.draft_text.startswith("One project that prepared me")
        assert "Tell us about" not in draft.draft_text
        assert "I would highlight" not in draft.draft_text
        assert "Python" in draft.draft_text
        assert "SQL" in draft.draft_text
        assert "Excel" in draft.draft_text
        assert "LaTeX" not in draft.draft_text
        assert "MySQL" not in draft.draft_text
        assert "Rejected Tableau Project" not in draft.draft_text
        assert draft.evidence_ids
        assert draft.draft_metadata["uses_approved_memory_only"] is True
        assert draft.draft_metadata["primary_memory"]["title"] == (
            "Gas Kinematics Honors Capstone"
        )
        assert draft.draft_metadata["primary_memory"]["type"] == "PROJECT"
        assert draft.draft_metadata["supporting_memories"][0]["title"] == (
            "Technical Skills"
        )
        assert edited.status is ApplicationDraftStatus.APPROVED
        assert edited.draft_text.endswith("Edited by user.")
    finally:
        _cleanup_user(user_id)


def test_draft_variants_change_length_and_keep_project_primary() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    service = ApplicationIntelligenceService(user_id=user_id)

    try:
        with SessionLocal() as session:
            opportunity = service.create_opportunity(
                session,
                ApplicationOpportunityCreateRequest(raw_text=SAMPLE_OPPORTUNITY),
            )
            question_id = opportunity.questions[0].id
            short = service.generate_draft(
                session,
                opportunity.id,
                ApplicationDraftRequest(
                    question_id=question_id,
                    draft_type=ApplicationDraftType.QUESTION_ANSWER,
                    length=ApplicationDraftLength.SHORT,
                ),
            ).draft
            medium = service.generate_draft(
                session,
                opportunity.id,
                ApplicationDraftRequest(
                    question_id=question_id,
                    draft_type=ApplicationDraftType.QUESTION_ANSWER,
                    length=ApplicationDraftLength.MEDIUM,
                ),
            ).draft
            detailed = service.generate_draft(
                session,
                opportunity.id,
                ApplicationDraftRequest(
                    question_id=question_id,
                    draft_type=ApplicationDraftType.QUESTION_ANSWER,
                    length=ApplicationDraftLength.DETAILED,
                ),
            ).draft

        assert len(short.draft_text.split()) < len(medium.draft_text.split())
        assert len(medium.draft_text.split()) < len(detailed.draft_text.split())
        assert short.draft_text.split(".")[0] != medium.draft_text.split(".")[0]
        assert medium.draft_text.split(".")[0] != detailed.draft_text.split(".")[0]
        assert detailed.draft_metadata["variant"] == "detailed"
        assert short.draft_metadata["primary_memory"]["type"] == "PROJECT"
        assert short.draft_metadata["primary_memory"]["title"] == (
            "Gas Kinematics Honors Capstone"
        )
        support_types = {
            memory["type"] for memory in short.draft_metadata["supporting_memories"]
        }
        assert "SKILL_SET" in support_types
        assert short.draft_metadata["evidence_ids"]
    finally:
        _cleanup_user(user_id)


def test_draft_without_approved_memory_returns_clear_empty_state() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    service = ApplicationIntelligenceService(user_id=user_id)

    try:
        with SessionLocal() as session:
            opportunity = service.create_opportunity(
                session,
                ApplicationOpportunityCreateRequest(raw_text=SAMPLE_OPPORTUNITY),
            )
            draft = service.generate_draft(
                session,
                opportunity.id,
                ApplicationDraftRequest(
                    question_id=opportunity.questions[0].id,
                    draft_type=ApplicationDraftType.QUESTION_ANSWER,
                ),
            ).draft

        assert "Application drafts need approved Career Memory" in draft.draft_text
        assert "I would highlight" not in draft.draft_text
        assert draft.evidence_ids == []
        assert draft.draft_metadata["primary_memory"] is None
    finally:
        _cleanup_user(user_id)


def test_application_api_returns_expected_schema() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    app.dependency_overrides[get_application_service] = lambda: (
        ApplicationIntelligenceService(user_id=user_id)
    )
    client = TestClient(app)

    try:
        created = client.post(
            "/api/applications/opportunities",
            json={"raw_text": SAMPLE_OPPORTUNITY},
        )
        assert created.status_code == 201
        body = created.json()
        assert body["detected_skills"]
        assert body["matches"]
        assert body["questions"]

        draft = client.post(
            f"/api/applications/questions/{body['questions'][0]['id']}/draft",
            json={"draft_type": "QUESTION_ANSWER", "length": "SHORT"},
        )
        assert draft.status_code == 200
        draft_body: dict[str, Any] = draft.json()
        assert draft_body["evidence_used"]
        assert draft_body["draft"]["draft_metadata"]["uses_approved_memory_only"]
    finally:
        app.dependency_overrides.pop(get_application_service, None)
        _cleanup_user(user_id)


def test_application_api_rejects_blank_opportunity_with_friendly_message() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/applications/opportunities",
        json={"raw_text": "   "},
    )

    assert response.status_code == 422
    assert (
        "Paste a job description"
        in json_text(response.json())
    )


def json_text(value: Any) -> str:
    return str(value)

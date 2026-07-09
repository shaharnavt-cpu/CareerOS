"""Regression coverage for Application Intelligence."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text
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
        for model in (
            ApplicationDraft,
            ApplicationMemoryMatch,
            ApplicationQuestion,
            ApplicationOpportunity,
            CanonicalMemoryRecord,
            ReviewProposal,
        ):
            session.execute(delete(model).where(model.user_id == user_id))
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
                "skills": ["Python", "SQL", "Excel", "R"],
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
        assert draft.draft_text.startswith("A project that prepared me")
        assert "Tell us about" not in draft.draft_text
        assert "I would highlight" not in draft.draft_text
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

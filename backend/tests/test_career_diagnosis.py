"""Regression coverage for Career Diagnosis Engine v0."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.api.diagnosis import get_diagnosis_service, get_feedback_service
from app.db.session import SessionLocal, engine
from app.main import app
from app.models import (
    CanonicalMemoryRecord,
    CareerFeedbackEvent,
    DiagnosisResult,
    DiagnosisSession,
    ReviewProposal,
    User,
)
from app.schemas.diagnosis import (
    DiagnosisFocus,
    DiagnosisSessionCreateRequest,
    FeedbackArtifactType,
    FeedbackEventCreateRequest,
    FeedbackEventStatus,
    FeedbackEventUpdateRequest,
    FeedbackOutcomeType,
)
from app.services.career_diagnosis import (
    CareerDiagnosisService,
    CareerFeedbackService,
    DuplicateFeedbackEventError,
)


def _require_postgres() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        pytest.skip(f"PostgreSQL is unavailable: {error}")


def _cleanup_user(user_id: uuid.UUID) -> None:
    with SessionLocal.begin() as session:
        diagnosis_ids = select(DiagnosisSession.id).where(
            DiagnosisSession.user_id == user_id
        )
        session.execute(
            delete(DiagnosisResult).where(DiagnosisResult.session_id.in_(diagnosis_ids))
        )
        for model in (
            DiagnosisSession,
            CareerFeedbackEvent,
            CanonicalMemoryRecord,
            ReviewProposal,
        ):
            session.execute(delete(model).where(model.user_id == user_id))
        session.execute(delete(User).where(User.id == user_id))


def _seed_memory(user_id: uuid.UUID) -> dict[str, CanonicalMemoryRecord]:
    payloads = [
        (
            "project",
            "PROJECT",
            "Gas Kinematics Honors Capstone",
            {
                "title": "Gas Kinematics Honors Capstone",
                "summary": (
                    "Python data analysis, statistical modeling, uncertainty, and "
                    "visualization research."
                ),
            },
            ["project-evidence", "analysis-evidence"],
        ),
        (
            "skills",
            "SKILL_SET",
            "Technical Skills",
            {"skills": ["Python", "SQL", "Excel", "data analysis"]},
            ["skill-evidence"],
        ),
        (
            "experience",
            "EXPERIENCE",
            "Undergraduate Learning Assistant",
            {
                "title": "Undergraduate Learning Assistant",
                "responsibilities": [
                    "Communicated technical ideas and mentored students."
                ],
            },
            ["experience-evidence"],
        ),
    ]
    memories: dict[str, CanonicalMemoryRecord] = {}
    with SessionLocal.begin() as session:
        session.add(
            User(
                id=user_id,
                clerk_user_id=f"diagnosis-test-{user_id}",
                email=f"diagnosis-test-{user_id}@example.invalid",
                display_name="Diagnosis Test User",
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
                    proposal_data={"title": title},
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
                confidence=Decimal("0.920"),
                review_proposal_id=proposal_id,
            )
            session.add(memory)
            session.flush()
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


def test_diagnosis_without_approved_memory_returns_helpful_empty_state() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    service = CareerDiagnosisService(user_id=user_id)
    try:
        with SessionLocal() as session:
            diagnosis = service.create_and_run(
                session,
                DiagnosisSessionCreateRequest(target_role="Data Analytics Intern"),
            )

        assert diagnosis.status.value == "NEEDS_MEMORY"
        assert diagnosis.result.career_identity == (
            "Approve career memories before running a full diagnosis."
        )
        assert diagnosis.result.evidence_map == []
        assert diagnosis.result.evidence_ids == []
        assert "approved" in diagnosis.result.recognition_gap.lower()
    finally:
        _cleanup_user(user_id)


def test_diagnosis_uses_only_approved_memory_and_preserves_evidence_ids() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    service = CareerDiagnosisService(user_id=user_id)
    try:
        with SessionLocal() as session:
            diagnosis = service.create_and_run(
                session,
                DiagnosisSessionCreateRequest(
                    target_role="Data Analytics / AI internship",
                    frustration_context=(
                        "I feel like my background is scattered and I am not sure "
                        "what employers will recognize."
                    ),
                    selected_focus=DiagnosisFocus.ANALYTICS,
                ),
            )

        titles = [item.memory_title for item in diagnosis.result.evidence_map]
        assert "Gas Kinematics Honors Capstone" in titles
        assert "Rejected Tableau Project" not in titles
        assert "project-evidence" in diagnosis.result.evidence_ids
        assert all(item.evidence_ids for item in diagnosis.result.evidence_map)
        assert "Analytical problem-solver" in diagnosis.result.career_identity
        assert "proof" in diagnosis.result.recognition_gap
        assert any(
            phrase in diagnosis.result.recognition_gap
            for phrase in ("business-facing", "deployable AI")
        )
        assert len(diagnosis.result.proof_sprint.actions) >= 3
        assert "Day 1" in diagnosis.result.proof_sprint.actions[0]
        assert "Gas Kinematics" in diagnosis.result.proof_sprint.objective
        assert "Gas Kinematics" in diagnosis.result.exact_messages["linkedin_outreach"]
        assert "new project" not in diagnosis.result.do_not_waste_time.lower()
        assert "apply to more jobs" not in diagnosis.result.do_not_waste_time.lower()
        assert diagnosis.result.exact_messages["linkedin_outreach"]
        assert diagnosis.result.confidence > 0.5
        assert diagnosis.result.diagnosis_version == "local-deterministic-v0"
    finally:
        _cleanup_user(user_id)


def test_diagnosis_rerun_and_api_session_reads_are_durable() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    diagnosis_service = CareerDiagnosisService(user_id=user_id)
    feedback_service = CareerFeedbackService(user_id=user_id)
    app.dependency_overrides[get_diagnosis_service] = lambda: diagnosis_service
    app.dependency_overrides[get_feedback_service] = lambda: feedback_service
    client = TestClient(app)
    try:
        created = client.post(
            "/api/diagnosis/sessions",
            json={
                "target_role": "Data Analytics / AI internship",
                "selected_focus": "ANALYTICS",
            },
        )
        assert created.status_code == 201
        diagnosis_id = created.json()["id"]
        assert client.get(f"/api/diagnosis/sessions/{diagnosis_id}").status_code == 200
        assert (
            client.post(f"/api/diagnosis/sessions/{diagnosis_id}/rerun").status_code
            == 200
        )
        listed = client.get("/api/diagnosis/sessions")
        assert listed.status_code == 200
        assert listed.json()[0]["id"] == diagnosis_id
    finally:
        app.dependency_overrides.pop(get_diagnosis_service, None)
        app.dependency_overrides.pop(get_feedback_service, None)
        _cleanup_user(user_id)


def test_teach_careeros_parses_success_and_positioning_rules() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    memories = _seed_memory(user_id)
    service = CareerFeedbackService(user_id=user_id)
    try:
        with SessionLocal() as session:
            success = service.create(
                session,
                FeedbackEventCreateRequest(
                    raw_note=(
                        "The JSOM eLearning Recording Studio Assistant cover letter "
                        "led to an "
                        "interview invite."
                    )
                ),
            )
            positioning = service.create(
                session,
                FeedbackEventCreateRequest(
                    raw_note=(
                        "Use Gas Kinematics as a data analysis story, not as an "
                        "astronomy story, for analytics roles."
                    )
                ),
            )

        assert success.event_type.value == "ARTIFACT_SUCCESS"
        assert success.artifact_type == FeedbackArtifactType.COVER_LETTER
        assert success.artifact_label == (
            "JSOM eLearning Recording Studio Assistant cover letter"
        )
        assert success.outcome == FeedbackOutcomeType.INTERVIEW_INVITE
        assert "not a proven cause" in success.structured_summary
        assert "campus" in success.suggested_future_use
        assert "student-worker" in success.suggested_future_use
        assert "technical communication" in success.suggested_future_use
        assert "department-specific" in success.suggested_future_use
        assert positioning.event_type.value == "POSITIONING_RULE"
        assert str(memories["project"].id) in positioning.related_memory_ids
        assert "approved memory" in positioning.suggested_future_use.lower()
    finally:
        _cleanup_user(user_id)


@pytest.mark.parametrize(
    ("note", "artifact_type", "outcome"),
    [
        (
            "This cover letter got me an interview.",
            FeedbackArtifactType.COVER_LETTER,
            FeedbackOutcomeType.INTERVIEW_INVITE,
        ),
        (
            "This application led to an interview invite.",
            FeedbackArtifactType.APPLICATION,
            FeedbackOutcomeType.INTERVIEW_INVITE,
        ),
        (
            "This resume version got a callback.",
            FeedbackArtifactType.RESUME,
            FeedbackOutcomeType.CALLBACK,
        ),
    ],
)
def test_teach_careeros_parses_common_interview_outcomes(
    note: str,
    artifact_type: FeedbackArtifactType,
    outcome: FeedbackOutcomeType,
) -> None:
    parsed = CareerFeedbackService.parse_note(note)

    assert parsed.event_type.value == "ARTIFACT_SUCCESS"
    assert parsed.artifact_type == artifact_type
    assert parsed.outcome == outcome
    assert parsed.artifact_label


def test_duplicate_feedback_event_is_rejected_without_creating_a_second_row() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    service = CareerFeedbackService(user_id=user_id)
    try:
        with SessionLocal() as session:
            existing = service.create(
                session,
                FeedbackEventCreateRequest(
                    raw_note=(
                        "The JSOM eLearning Recording Studio Assistant cover letter "
                        "led to an interview invite."
                    )
                ),
            )
            with pytest.raises(DuplicateFeedbackEventError) as error:
                service.create(
                    session,
                    FeedbackEventCreateRequest(
                        raw_note=(
                            "JSOM eLearning Recording Studio Assistant cover letter "
                            "got me an interview."
                        )
                    ),
                )
            persisted = session.scalars(
                select(CareerFeedbackEvent).where(
                    CareerFeedbackEvent.user_id == user_id
                )
            ).all()

        assert error.value.existing_event_id == existing.id
        assert len(persisted) == 1
    finally:
        _cleanup_user(user_id)


def test_duplicate_feedback_api_returns_actionable_warning() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    service = CareerFeedbackService(user_id=user_id)
    app.dependency_overrides[get_feedback_service] = lambda: service
    client = TestClient(app)
    note = "This cover letter got me an interview."
    try:
        first = client.post("/api/diagnosis/feedback-events", json={"raw_note": note})
        duplicate = client.post(
            "/api/diagnosis/feedback-events", json={"raw_note": note}
        )

        assert first.status_code == 201
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"] == {
            "code": "DUPLICATE_FEEDBACK_EVENT",
            "message": "This looks similar to an existing feedback event.",
            "existing_event_id": first.json()["id"],
        }
    finally:
        app.dependency_overrides.pop(get_feedback_service, None)
        _cleanup_user(user_id)


def test_editing_feedback_raw_note_reparses_fields_and_preserves_status() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    service = CareerFeedbackService(user_id=user_id)
    app.dependency_overrides[get_feedback_service] = lambda: service
    client = TestClient(app)
    try:
        created = client.post(
            "/api/diagnosis/feedback-events",
            json={
                "raw_note": (
                    "The Black Box AI Engineer Intern cover letter led to an "
                    "interview invite."
                ),
                "status": "APPROVED",
            },
        )
        corrected = client.patch(
            f"/api/diagnosis/feedback-events/{created.json()['id']}",
            json={
                "raw_note": (
                    "The JSOM eLearning Recording Studio Assistant cover letter "
                    "led to an interview invite."
                )
            },
        )
        payload = corrected.json()

        assert created.status_code == 201
        assert corrected.status_code == 200
        assert payload["status"] == "APPROVED"
        assert payload["artifact_type"] == "COVER_LETTER"
        assert payload["artifact_label"] == (
            "JSOM eLearning Recording Studio Assistant cover letter"
        )
        assert payload["outcome"] == "INTERVIEW_INVITE"
        assert "JSOM eLearning" in payload["structured_summary"]
        assert payload["event_metadata"]["parser_version"] == (
            "feedback-deterministic-v1"
        )
    finally:
        app.dependency_overrides.pop(get_feedback_service, None)
        _cleanup_user(user_id)


def test_approved_outcome_guides_diagnosis_and_archived_outcome_is_excluded() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    feedback_service = CareerFeedbackService(user_id=user_id)
    diagnosis_service = CareerDiagnosisService(user_id=user_id)
    try:
        with SessionLocal() as session:
            approved = feedback_service.create(
                session,
                FeedbackEventCreateRequest(
                    raw_note=(
                        "The JSOM eLearning Recording Studio Assistant cover letter "
                        "led to an interview invite."
                    ),
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
                    status=FeedbackEventStatus.ARCHIVED,
                ),
            )
            diagnosis = diagnosis_service.create_and_run(
                session,
                DiagnosisSessionCreateRequest(
                    target_role="Campus technical communications assistant",
                    selected_focus=DiagnosisFocus.CAMPUS_JOB,
                ),
            )

        assert diagnosis.result.feedback_event_ids == [str(approved.id)]
        assert str(archived.id) not in diagnosis.result.feedback_event_ids
        assert len(diagnosis.result.outcome_signals) == 1
        signal = diagnosis.result.outcome_signals[0]
        assert signal.feedback_event_id == approved.id
        assert "JSOM eLearning Recording Studio Assistant" in signal.summary
        assert "worked once" in signal.summary
        assert "not proof" in signal.summary
        diagnosis_guidance = " ".join(
            [
                diagnosis.result.recognition_gap,
                *diagnosis.result.proof_sprint.actions,
                diagnosis.result.proof_sprint.application_use,
                *diagnosis.result.exact_next_actions,
                *diagnosis.result.exact_messages.values(),
            ]
        )
        assert "JSOM eLearning Recording Studio Assistant" in diagnosis_guidance
        assert "Black Box AI Engineer Intern" not in diagnosis_guidance
    finally:
        _cleanup_user(user_id)


def test_feedback_event_can_be_approved_and_archived() -> None:
    _require_postgres()
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    service = CareerFeedbackService(user_id=user_id)
    try:
        with SessionLocal() as session:
            event = service.create(
                session,
                FeedbackEventCreateRequest(raw_note="This draft felt too generic."),
            )
            approved = service.update(
                session,
                event.id,
                FeedbackEventUpdateRequest(status=FeedbackEventStatus.APPROVED),
            )
            archived = service.update(
                session,
                event.id,
                FeedbackEventUpdateRequest(status=FeedbackEventStatus.ARCHIVED),
            )

        assert event.event_type.value == "DRAFT_FEEDBACK"
        assert approved.status.value == "APPROVED"
        assert archived.status.value == "ARCHIVED"
    finally:
        _cleanup_user(user_id)


def test_local_deterministic_diagnosis_needs_no_llm_key(monkeypatch) -> None:
    _require_postgres()
    monkeypatch.setenv("REASONING_PROVIDER", "local-deterministic")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    user_id = uuid.uuid4()
    _seed_memory(user_id)
    try:
        with SessionLocal() as session:
            result = CareerDiagnosisService(user_id=user_id).create_and_run(
                session, DiagnosisSessionCreateRequest()
            )
        assert result.status.value == "COMPLETE"
        assert result.result.diagnosis_version == "local-deterministic-v0"
    finally:
        _cleanup_user(user_id)

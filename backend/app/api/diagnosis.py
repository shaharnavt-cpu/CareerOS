"""Career Diagnosis Engine and Teach CareerOS endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.diagnosis import (
    DiagnosisSessionCreateRequest,
    DiagnosisSessionView,
    FeedbackEventCreateRequest,
    FeedbackEventUpdateRequest,
    FeedbackEventView,
)
from app.services.career_diagnosis import (
    CareerDiagnosisService,
    CareerFeedbackService,
    DiagnosisNotFoundError,
)

router = APIRouter(prefix="/diagnosis", tags=["diagnosis"])


def get_diagnosis_service() -> CareerDiagnosisService:
    return CareerDiagnosisService()


def get_feedback_service() -> CareerFeedbackService:
    return CareerFeedbackService()


@router.post(
    "/sessions",
    response_model=DiagnosisSessionView,
    status_code=status.HTTP_201_CREATED,
)
def create_diagnosis_session(
    request: DiagnosisSessionCreateRequest,
    session: Session = Depends(get_db),
    service: CareerDiagnosisService = Depends(get_diagnosis_service),
) -> DiagnosisSessionView:
    return service.create_and_run(session, request)


@router.get("/sessions", response_model=list[DiagnosisSessionView])
def list_diagnosis_sessions(
    session: Session = Depends(get_db),
    service: CareerDiagnosisService = Depends(get_diagnosis_service),
) -> list[DiagnosisSessionView]:
    return service.list_sessions(session)


@router.get("/sessions/{diagnosis_session_id}", response_model=DiagnosisSessionView)
def get_diagnosis_session(
    diagnosis_session_id: uuid.UUID,
    session: Session = Depends(get_db),
    service: CareerDiagnosisService = Depends(get_diagnosis_service),
) -> DiagnosisSessionView:
    return _call(service.get_session, session, diagnosis_session_id)


@router.post(
    "/sessions/{diagnosis_session_id}/rerun",
    response_model=DiagnosisSessionView,
)
def rerun_diagnosis_session(
    diagnosis_session_id: uuid.UUID,
    session: Session = Depends(get_db),
    service: CareerDiagnosisService = Depends(get_diagnosis_service),
) -> DiagnosisSessionView:
    return _call(service.rerun, session, diagnosis_session_id)


@router.post(
    "/feedback-events",
    response_model=FeedbackEventView,
    status_code=status.HTTP_201_CREATED,
)
def create_feedback_event(
    request: FeedbackEventCreateRequest,
    session: Session = Depends(get_db),
    service: CareerFeedbackService = Depends(get_feedback_service),
) -> FeedbackEventView:
    return _call(service.create, session, request)


@router.get("/feedback-events", response_model=list[FeedbackEventView])
def list_feedback_events(
    session: Session = Depends(get_db),
    service: CareerFeedbackService = Depends(get_feedback_service),
) -> list[FeedbackEventView]:
    return service.list(session)


@router.patch("/feedback-events/{feedback_event_id}", response_model=FeedbackEventView)
def update_feedback_event(
    feedback_event_id: uuid.UUID,
    request: FeedbackEventUpdateRequest,
    session: Session = Depends(get_db),
    service: CareerFeedbackService = Depends(get_feedback_service),
) -> FeedbackEventView:
    return _call(service.update, session, feedback_event_id, request)


def _call(function, *args):
    try:
        return function(*args)
    except DiagnosisNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

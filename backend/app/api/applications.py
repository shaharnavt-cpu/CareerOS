"""Application Intelligence endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.applications import (
    ApplicationDraftRequest,
    ApplicationDraftResponse,
    ApplicationDraftUpdateRequest,
    ApplicationDraftView,
    ApplicationMatchResponse,
    ApplicationOpportunityCreateRequest,
    ApplicationOpportunityListItem,
    ApplicationOpportunityView,
    ApplicationQuestionCreateRequest,
    ApplicationQuestionView,
)
from app.services.application_intelligence import (
    ApplicationIntelligenceService,
    ApplicationNotFoundError,
)

router = APIRouter(prefix="/applications", tags=["applications"])


def get_application_service() -> ApplicationIntelligenceService:
    return ApplicationIntelligenceService()


@router.post(
    "/opportunities",
    response_model=ApplicationOpportunityView,
    status_code=status.HTTP_201_CREATED,
)
def create_opportunity(
    request: ApplicationOpportunityCreateRequest,
    session: Session = Depends(get_db),
    service: ApplicationIntelligenceService = Depends(get_application_service),
) -> ApplicationOpportunityView:
    return service.create_opportunity(session, request)


@router.get("/opportunities", response_model=list[ApplicationOpportunityListItem])
def list_opportunities(
    session: Session = Depends(get_db),
    service: ApplicationIntelligenceService = Depends(get_application_service),
) -> list[ApplicationOpportunityListItem]:
    return service.list_opportunities(session)


@router.get(
    "/opportunities/{opportunity_id}", response_model=ApplicationOpportunityView
)
def get_opportunity(
    opportunity_id: uuid.UUID,
    session: Session = Depends(get_db),
    service: ApplicationIntelligenceService = Depends(get_application_service),
) -> ApplicationOpportunityView:
    return _call(service.get_opportunity, session, opportunity_id)


@router.post(
    "/opportunities/{opportunity_id}/match", response_model=ApplicationMatchResponse
)
def recompute_matches(
    opportunity_id: uuid.UUID,
    session: Session = Depends(get_db),
    service: ApplicationIntelligenceService = Depends(get_application_service),
) -> ApplicationMatchResponse:
    return _call(service.recompute_matches, session, opportunity_id)


@router.post(
    "/opportunities/{opportunity_id}/draft", response_model=ApplicationDraftResponse
)
def draft_opportunity(
    opportunity_id: uuid.UUID,
    request: ApplicationDraftRequest,
    session: Session = Depends(get_db),
    service: ApplicationIntelligenceService = Depends(get_application_service),
) -> ApplicationDraftResponse:
    return _call(service.generate_draft, session, opportunity_id, request)


@router.post(
    "/questions",
    response_model=ApplicationQuestionView,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    request: ApplicationQuestionCreateRequest,
    session: Session = Depends(get_db),
    service: ApplicationIntelligenceService = Depends(get_application_service),
) -> ApplicationQuestionView:
    return _call(service.create_question, session, request)


@router.post("/questions/{question_id}/draft", response_model=ApplicationDraftResponse)
def draft_question(
    question_id: uuid.UUID,
    request: ApplicationDraftRequest,
    session: Session = Depends(get_db),
    service: ApplicationIntelligenceService = Depends(get_application_service),
) -> ApplicationDraftResponse:
    return _call(service.generate_question_draft, session, question_id, request)


@router.patch("/drafts/{draft_id}", response_model=ApplicationDraftView)
def update_draft(
    draft_id: uuid.UUID,
    request: ApplicationDraftUpdateRequest,
    session: Session = Depends(get_db),
    service: ApplicationIntelligenceService = Depends(get_application_service),
) -> ApplicationDraftView:
    return _call(service.update_draft, session, draft_id, request)


def _call(function, *args):
    try:
        return function(*args)
    except ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

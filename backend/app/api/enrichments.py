"""Memory identity and reviewed project-enrichment endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import CanonicalMemoryRecord, ReviewProposal
from app.schemas.enrichments import (
    EnrichmentCreateRequest,
    EnrichmentUpdateRequest,
    EnrichmentView,
    MemoryIdentityCandidatesResponse,
)
from app.schemas.knowledge import DEMO_USER_ID, DurableReviewStatus
from app.services.memory_enrichment import (
    CareerMemoryEnrichmentService,
    DuplicateEnrichmentError,
    EnrichmentNotFoundError,
    EnrichmentStateError,
)
from app.services.memory_identity import MemoryIdentityResolver

router = APIRouter(tags=["memory enrichment"])


def get_enrichment_service() -> CareerMemoryEnrichmentService:
    return CareerMemoryEnrichmentService()


def get_identity_resolver() -> MemoryIdentityResolver:
    return MemoryIdentityResolver()


@router.get(
    "/memory-identity/candidates",
    response_model=MemoryIdentityCandidatesResponse,
)
def identity_candidates(
    title: str = Query(min_length=1, max_length=1000),
    text: str = Query(default="", max_length=100_000),
    memory_type: str = Query(default="PROJECT", max_length=64),
    session: Session = Depends(get_db),
    resolver: MemoryIdentityResolver = Depends(get_identity_resolver),
) -> MemoryIdentityCandidatesResponse:
    memories = session.scalars(
        select(CanonicalMemoryRecord)
        .join(
            ReviewProposal,
            ReviewProposal.id == CanonicalMemoryRecord.review_proposal_id,
        )
        .where(
            CanonicalMemoryRecord.user_id == DEMO_USER_ID,
            ReviewProposal.user_id == DEMO_USER_ID,
            ReviewProposal.decision.in_(
                [
                    DurableReviewStatus.APPROVED.value,
                    DurableReviewStatus.EDITED_APPROVED.value,
                ]
            ),
        )
    ).all()
    return MemoryIdentityCandidatesResponse(
        query_title=title,
        candidates=resolver.candidates(
            title=title,
            text=text,
            memory_type=memory_type,
            memories=memories,
        ),
    )


@router.get("/career-memory/enrichments", response_model=list[EnrichmentView])
def list_all_enrichments(
    session: Session = Depends(get_db),
    service: CareerMemoryEnrichmentService = Depends(get_enrichment_service),
) -> list[EnrichmentView]:
    return service.list(session)


@router.post(
    "/career-memory/{memory_id}/enrichments",
    response_model=EnrichmentView,
    status_code=status.HTTP_201_CREATED,
)
def create_enrichment(
    memory_id: uuid.UUID,
    request: EnrichmentCreateRequest,
    session: Session = Depends(get_db),
    service: CareerMemoryEnrichmentService = Depends(get_enrichment_service),
) -> EnrichmentView:
    try:
        return service.create(session, memory_id, request)
    except DuplicateEnrichmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_ENRICHMENT",
                "message": str(exc),
                "existing_enrichment_id": str(exc.existing_enrichment_id),
                "existing_status": exc.existing_status,
            },
        ) from exc
    except EnrichmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except EnrichmentStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get(
    "/career-memory/{memory_id}/enrichments",
    response_model=list[EnrichmentView],
)
def list_memory_enrichments(
    memory_id: uuid.UUID,
    session: Session = Depends(get_db),
    service: CareerMemoryEnrichmentService = Depends(get_enrichment_service),
) -> list[EnrichmentView]:
    try:
        return service.list(session, memory_id)
    except EnrichmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post(
    "/career-memory/{memory_id}/enrichments/from-proposal/{proposal_id}",
    response_model=EnrichmentView,
    status_code=status.HTTP_201_CREATED,
)
def convert_proposal_to_enrichment(
    memory_id: uuid.UUID,
    proposal_id: str,
    session: Session = Depends(get_db),
    service: CareerMemoryEnrichmentService = Depends(get_enrichment_service),
) -> EnrichmentView:
    try:
        return service.convert_proposal(session, memory_id, proposal_id)
    except EnrichmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except EnrichmentStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.patch(
    "/career-memory/enrichments/{enrichment_id}",
    response_model=EnrichmentView,
)
def update_enrichment(
    enrichment_id: uuid.UUID,
    request: EnrichmentUpdateRequest,
    session: Session = Depends(get_db),
    service: CareerMemoryEnrichmentService = Depends(get_enrichment_service),
) -> EnrichmentView:
    try:
        return service.update(session, enrichment_id, request)
    except EnrichmentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except EnrichmentStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

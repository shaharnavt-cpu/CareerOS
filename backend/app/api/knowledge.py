"""Knowledge reasoning, review, and Career Memory endpoints."""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.knowledge import (
    DEMO_USER_ID,
    CareerMemoryResponse,
    DashboardSummaryResponse,
    KnowledgeProposal,
    ProposalEditRequest,
    ProposalReviewRequest,
    ProposalReviewResponse,
    ReasoningRequest,
    ReasoningResponse,
)
from app.services.llm import ReasoningProviderError, build_reasoning_provider
from app.services.memory import CareerMemoryService
from app.services.pipeline import KnowledgeReasoningPipeline
from app.services.proposals import ReasoningValidationError
from app.services.review_service import ReviewedCareerMemoryService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@lru_cache
def get_reasoning_pipeline() -> KnowledgeReasoningPipeline:
    """Build the provider-independent pipeline once per API process."""

    return KnowledgeReasoningPipeline(build_reasoning_provider(get_settings()))


def get_memory_service() -> CareerMemoryService:
    """Return the stateless canonical-memory service."""

    return CareerMemoryService()


def get_review_service() -> ReviewedCareerMemoryService:
    return ReviewedCareerMemoryService()


@router.post("/proposals", response_model=ReasoningResponse)
async def create_proposals(
    request: ReasoningRequest,
    pipeline: KnowledgeReasoningPipeline = Depends(get_reasoning_pipeline),
) -> ReasoningResponse:
    """Run raw source through the complete hybrid reasoning pipeline."""

    try:
        return await pipeline.run(request)
    except ReasoningValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "PROPOSAL_FAILURE",
                "message": "CareerOS could not validate these knowledge proposals.",
            },
        ) from exc
    except ReasoningProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "REASONING_FAILURE",
                "message": "The reasoning service is temporarily unavailable.",
            },
        ) from exc


@router.post("/proposals/review", response_model=ProposalReviewResponse)
def review_proposal(
    request: ProposalReviewRequest,
    session: Session = Depends(get_db),
    reviews: ReviewedCareerMemoryService = Depends(get_review_service),
) -> ProposalReviewResponse:
    """Apply an explicit decision; only approval can write Career Memory."""

    return reviews.review(session, request)


@router.get("/review-proposals", response_model=list[KnowledgeProposal])
def list_review_proposals(
    session: Session = Depends(get_db),
    reviews: ReviewedCareerMemoryService = Depends(get_review_service),
) -> list[KnowledgeProposal]:
    return reviews.list_proposals(session)


@router.patch(
    "/review-proposals/{proposal_id}", response_model=KnowledgeProposal
)
def edit_review_proposal(
    proposal_id: str,
    request: ProposalEditRequest,
    session: Session = Depends(get_db),
    reviews: ReviewedCareerMemoryService = Depends(get_review_service),
) -> KnowledgeProposal:
    if request.proposal.id != proposal_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposal path and payload IDs must match.",
        )
    return reviews.edit(session, request.proposal)


@router.get("/dashboard", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    session: Session = Depends(get_db),
    reviews: ReviewedCareerMemoryService = Depends(get_review_service),
) -> DashboardSummaryResponse:
    return reviews.dashboard(session)


@router.get("/memory", response_model=CareerMemoryResponse)
def get_career_memory(
    session: Session = Depends(get_db),
    memory: CareerMemoryService = Depends(get_memory_service),
) -> CareerMemoryResponse:
    """Return current canonical entities for the Sprint 4 demo user."""

    return memory.get_memory(session, DEMO_USER_ID)

"""Knowledge reasoning, review, and Career Memory endpoints."""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.knowledge import (
    DEMO_USER_ID,
    CareerMemoryResponse,
    ProposalReviewRequest,
    ProposalReviewResponse,
    ReasoningRequest,
    ReasoningResponse,
)
from app.services.llm import ReasoningProviderError, build_reasoning_provider
from app.services.memory import CareerMemoryService
from app.services.pipeline import KnowledgeReasoningPipeline
from app.services.proposals import ReasoningValidationError

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@lru_cache
def get_reasoning_pipeline() -> KnowledgeReasoningPipeline:
    """Build the provider-independent pipeline once per API process."""

    return KnowledgeReasoningPipeline(build_reasoning_provider(get_settings()))


def get_memory_service() -> CareerMemoryService:
    """Return the stateless canonical-memory service."""

    return CareerMemoryService()


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
            detail=str(exc),
        ) from exc
    except ReasoningProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The semantic reasoning provider could not return valid output.",
        ) from exc


@router.post("/proposals/review", response_model=ProposalReviewResponse)
def review_proposal(
    request: ProposalReviewRequest,
    session: Session = Depends(get_db),
    memory: CareerMemoryService = Depends(get_memory_service),
) -> ProposalReviewResponse:
    """Apply an explicit decision; only approval can write Career Memory."""

    return memory.review(session, request)


@router.get("/memory", response_model=CareerMemoryResponse)
def get_career_memory(
    session: Session = Depends(get_db),
    memory: CareerMemoryService = Depends(get_memory_service),
) -> CareerMemoryResponse:
    """Return current canonical entities for the Sprint 4 demo user."""

    return memory.get_memory(session, DEMO_USER_ID)

"""Multi-Source Listening Engine endpoints."""

import uuid
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.knowledge import get_reasoning_pipeline
from app.db.session import get_db
from app.schemas.knowledge import DEMO_USER_ID
from app.schemas.listening import (
    EvidenceCluster,
    EvidenceObject,
    ListeningProposalRequest,
    ListeningProposalResponse,
    ListeningSourceSummary,
    SourceIngestionResponse,
    SourceSubmission,
)
from app.services.listening import ListeningEngine, ListeningReasoningBridge
from app.services.listening_repository import ListeningRepository
from app.services.llm import ReasoningProviderError
from app.services.pipeline import KnowledgeReasoningPipeline
from app.services.proposals import ReasoningValidationError

router = APIRouter(prefix="/listening", tags=["listening"])


@lru_cache
def get_listening_engine() -> ListeningEngine:
    return ListeningEngine()


def get_listening_repository() -> ListeningRepository:
    return ListeningRepository()


def get_listening_bridge(
    pipeline: KnowledgeReasoningPipeline = Depends(get_reasoning_pipeline),
) -> ListeningReasoningBridge:
    return ListeningReasoningBridge(pipeline)


@router.post("/sources", response_model=SourceIngestionResponse)
def submit_source(
    request: SourceSubmission,
    session: Session = Depends(get_db),
    engine: ListeningEngine = Depends(get_listening_engine),
    repository: ListeningRepository = Depends(get_listening_repository),
) -> SourceIngestionResponse:
    """Normalize, listen to, fuse, and durably stage one user source."""

    source, evidence, clusters = engine.listen(request, DEMO_USER_ID)
    summary = repository.persist_ingestion(session, source, evidence, clusters)
    return SourceIngestionResponse(source=summary, evidence=evidence, clusters=clusters)


@router.get("/sources", response_model=list[ListeningSourceSummary])
def list_sources(
    session: Session = Depends(get_db),
    repository: ListeningRepository = Depends(get_listening_repository),
) -> list[ListeningSourceSummary]:
    """List staged sources for the current tenant without returning raw text."""

    return repository.list_sources(session)


@router.get("/evidence", response_model=list[EvidenceObject])
def list_evidence(
    source_id: uuid.UUID | None = Query(default=None),
    session: Session = Depends(get_db),
    repository: ListeningRepository = Depends(get_listening_repository),
) -> list[EvidenceObject]:
    """List standardized observations, optionally scoped to one source."""

    return repository.list_evidence(
        session, source_ids=[source_id] if source_id is not None else None
    )


@router.get("/clusters", response_model=list[EvidenceCluster])
def list_clusters(
    source_id: uuid.UUID | None = Query(default=None),
    session: Session = Depends(get_db),
    engine: ListeningEngine = Depends(get_listening_engine),
    repository: ListeningRepository = Depends(get_listening_repository),
) -> list[EvidenceCluster]:
    """Return the current fusion view while retaining every evidence item."""

    evidence = repository.list_evidence(
        session, source_ids=[source_id] if source_id is not None else None
    )
    return engine.fuse(evidence)


@router.post("/proposals", response_model=ListeningProposalResponse)
async def create_listening_proposals(
    request: ListeningProposalRequest,
    session: Session = Depends(get_db),
    engine: ListeningEngine = Depends(get_listening_engine),
    repository: ListeningRepository = Depends(get_listening_repository),
    bridge: ListeningReasoningBridge = Depends(get_listening_bridge),
) -> ListeningProposalResponse:
    """Fuse selected evidence and hand it to the existing reasoning engine."""

    evidence = repository.list_evidence(session, source_ids=request.source_ids or None)
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No listening evidence was found for the selected sources.",
        )
    clusters = engine.fuse(evidence)
    repository.persist_clusters(session, DEMO_USER_ID, clusters)
    try:
        response = await bridge.generate(clusters, request.existing_memory)
    except ReasoningValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except ReasoningProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The semantic reasoning provider could not return valid output.",
        ) from exc
    repository.persist_proposal_links(
        session, DEMO_USER_ID, response.proposals, clusters
    )
    return response

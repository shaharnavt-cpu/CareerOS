"""Multi-Source Listening Engine endpoints."""

import uuid
from functools import lru_cache

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.knowledge import get_reasoning_pipeline
from app.db.session import SessionLocal, get_db
from app.schemas.knowledge import DEMO_USER_ID
from app.schemas.listening import (
    EvidenceCluster,
    EvidenceObject,
    ListeningJobResponse,
    ListeningProposalRequest,
    ListeningProposalResponse,
    ListeningSourceSummary,
    ListeningUploadResponse,
    SourceIngestionResponse,
    SourceSubmission,
)
from app.services.document_adapters import (
    MAX_DOCUMENT_BYTES,
    MAX_UPLOAD_FILES,
    RawDocument,
)
from app.services.listening import ListeningEngine, ListeningReasoningBridge
from app.services.listening_queue import (
    ListeningJob,
    ListeningQueue,
    UniversalListeningProcessor,
)
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


@lru_cache
def get_listening_queue() -> ListeningQueue:
    """Return the process-local FIFO worker used for document attachments."""

    return ListeningQueue(UniversalListeningProcessor(SessionLocal))


def _job_response(job: ListeningJob) -> ListeningJobResponse:
    return ListeningJobResponse(
        id=job.id,
        filename=job.document.filename,
        media_type=job.document.media_type,
        stage=job.stage.value,
        progress=job.progress,
        message=job.message,
        attempt=job.attempt,
        source_id=job.source_id,
        source_type=job.source_type,
        document_type=job.document_type,
        detection_confidence=job.detection_confidence,
        evidence_count=job.evidence_count,
        error_code=job.error_code,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def get_listening_bridge(
    pipeline: KnowledgeReasoningPipeline = Depends(get_reasoning_pipeline),
) -> ListeningReasoningBridge:
    return ListeningReasoningBridge(pipeline)


@router.post(
    "/uploads",
    response_model=ListeningUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_sources(
    files: list[UploadFile] = File(...),
    listening_queue: ListeningQueue = Depends(get_listening_queue),
) -> ListeningUploadResponse:
    """Queue multiple professional artifacts and return immediately."""

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attach at least one document for CareerOS to listen to.",
        )
    if len(files) > MAX_UPLOAD_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Attach up to {MAX_UPLOAD_FILES} files at a time.",
        )

    jobs = []
    for upload in files:
        filename = upload.filename or "untitled"
        content = await upload.read(MAX_DOCUMENT_BYTES + 1)
        jobs.append(
            listening_queue.enqueue(
                RawDocument(
                    filename=filename,
                    content=content,
                    media_type=upload.content_type,
                )
            )
        )
        await upload.close()
    return ListeningUploadResponse(jobs=[_job_response(job) for job in jobs])


@router.get("/jobs", response_model=list[ListeningJobResponse])
def list_listening_jobs(
    listening_queue: ListeningQueue = Depends(get_listening_queue),
) -> list[ListeningJobResponse]:
    """List upload queue state for source management and progress recovery."""

    return [_job_response(job) for job in listening_queue.list()]


@router.get("/jobs/{job_id}", response_model=ListeningJobResponse)
def get_listening_job(
    job_id: uuid.UUID,
    listening_queue: ListeningQueue = Depends(get_listening_queue),
) -> ListeningJobResponse:
    """Poll one queued source without exposing its raw content."""

    try:
        return _job_response(listening_queue.get(job_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That listening job is no longer available.",
        ) from exc


@router.post("/jobs/{job_id}/retry", response_model=ListeningJobResponse)
def retry_listening_job(
    job_id: uuid.UUID,
    listening_queue: ListeningQueue = Depends(get_listening_queue),
) -> ListeningJobResponse:
    """Retry a failed in-process listening job with the original bytes."""

    try:
        return _job_response(listening_queue.retry(job_id))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That listening job is no longer available.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed listening jobs can be retried.",
        ) from exc


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

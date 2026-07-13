"""Proof Artifact Builder endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.proof_artifacts import (
    ProofArtifactCreateRequest,
    ProofArtifactRegenerateRequest,
    ProofArtifactUpdateRequest,
    ProofArtifactVersionUpdateRequest,
    ProofArtifactView,
    ProofMemoryOption,
)
from app.services.proof_artifacts import (
    ProofArtifactNotFoundError,
    ProofArtifactService,
    ProofArtifactValidationError,
)

router = APIRouter(prefix="/proof-artifacts", tags=["proof-artifacts"])


def get_proof_artifact_service() -> ProofArtifactService:
    return ProofArtifactService()


@router.get("/eligible-memories", response_model=list[ProofMemoryOption])
def list_eligible_memories(
    session: Session = Depends(get_db),
    service: ProofArtifactService = Depends(get_proof_artifact_service),
) -> list[ProofMemoryOption]:
    return service.list_eligible_memories(session)


@router.post(
    "",
    response_model=ProofArtifactView,
    status_code=status.HTTP_201_CREATED,
)
def create_proof_artifact(
    request: ProofArtifactCreateRequest,
    session: Session = Depends(get_db),
    service: ProofArtifactService = Depends(get_proof_artifact_service),
) -> ProofArtifactView:
    return _call(service.create, session, request)


@router.get("", response_model=list[ProofArtifactView])
def list_proof_artifacts(
    session: Session = Depends(get_db),
    service: ProofArtifactService = Depends(get_proof_artifact_service),
) -> list[ProofArtifactView]:
    return service.list(session)


@router.get("/{artifact_id}", response_model=ProofArtifactView)
def get_proof_artifact(
    artifact_id: uuid.UUID,
    session: Session = Depends(get_db),
    service: ProofArtifactService = Depends(get_proof_artifact_service),
) -> ProofArtifactView:
    return _call(service.get, session, artifact_id)


@router.post("/{artifact_id}/regenerate", response_model=ProofArtifactView)
def regenerate_proof_artifact(
    artifact_id: uuid.UUID,
    request: ProofArtifactRegenerateRequest,
    session: Session = Depends(get_db),
    service: ProofArtifactService = Depends(get_proof_artifact_service),
) -> ProofArtifactView:
    return _call(service.regenerate, session, artifact_id, request)


@router.patch("/{artifact_id}", response_model=ProofArtifactView)
def update_proof_artifact(
    artifact_id: uuid.UUID,
    request: ProofArtifactUpdateRequest,
    session: Session = Depends(get_db),
    service: ProofArtifactService = Depends(get_proof_artifact_service),
) -> ProofArtifactView:
    return _call(service.update, session, artifact_id, request)


@router.patch(
    "/{artifact_id}/versions/{version_id}",
    response_model=ProofArtifactView,
)
def update_proof_artifact_version(
    artifact_id: uuid.UUID,
    version_id: uuid.UUID,
    request: ProofArtifactVersionUpdateRequest,
    session: Session = Depends(get_db),
    service: ProofArtifactService = Depends(get_proof_artifact_service),
) -> ProofArtifactView:
    return _call(service.update_version, session, artifact_id, version_id, request)


def _call(function, *args):
    try:
        return function(*args)
    except ProofArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ProofArtifactValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

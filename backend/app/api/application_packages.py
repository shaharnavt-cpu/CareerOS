"""Application Package Builder endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.application_packages import (
    ApplicationPackageCreateRequest,
    ApplicationPackageGenerateRequest,
    ApplicationPackageListItem,
    ApplicationPackageMemoryOption,
    ApplicationPackageOutputsUpdateRequest,
    ApplicationPackageUpdateRequest,
    ApplicationPackageView,
)
from app.services.application_packages import (
    ApplicationPackageNotFoundError,
    ApplicationPackageService,
    ApplicationPackageValidationError,
)

router = APIRouter(prefix="/application-packages", tags=["application-packages"])


def get_application_package_service() -> ApplicationPackageService:
    return ApplicationPackageService()


@router.get("/eligible-memories", response_model=list[ApplicationPackageMemoryOption])
def list_eligible_memories(
    target_role: str | None = Query(default=None, max_length=500),
    session: Session = Depends(get_db),
    service: ApplicationPackageService = Depends(get_application_package_service),
) -> list[ApplicationPackageMemoryOption]:
    return service.list_eligible_memories(session, target_role)


@router.post(
    "",
    response_model=ApplicationPackageView,
    status_code=status.HTTP_201_CREATED,
)
def create_application_package(
    request: ApplicationPackageCreateRequest,
    session: Session = Depends(get_db),
    service: ApplicationPackageService = Depends(get_application_package_service),
) -> ApplicationPackageView:
    return _call(service.create, session, request)


@router.get("", response_model=list[ApplicationPackageListItem])
def list_application_packages(
    include_archived: bool = Query(default=False),
    session: Session = Depends(get_db),
    service: ApplicationPackageService = Depends(get_application_package_service),
) -> list[ApplicationPackageListItem]:
    return service.list(session, include_archived=include_archived)


@router.get("/{package_id}", response_model=ApplicationPackageView)
def get_application_package(
    package_id: uuid.UUID,
    session: Session = Depends(get_db),
    service: ApplicationPackageService = Depends(get_application_package_service),
) -> ApplicationPackageView:
    return _call(service.get, session, package_id)


@router.post("/{package_id}/generate", response_model=ApplicationPackageView)
def generate_application_package(
    package_id: uuid.UUID,
    request: ApplicationPackageGenerateRequest | None = None,
    session: Session = Depends(get_db),
    service: ApplicationPackageService = Depends(get_application_package_service),
) -> ApplicationPackageView:
    return _call(service.generate, session, package_id, request)


@router.post("/{package_id}/regenerate", response_model=ApplicationPackageView)
def regenerate_application_package(
    package_id: uuid.UUID,
    request: ApplicationPackageGenerateRequest | None = None,
    session: Session = Depends(get_db),
    service: ApplicationPackageService = Depends(get_application_package_service),
) -> ApplicationPackageView:
    return _call(service.regenerate, session, package_id, request)


@router.patch("/{package_id}", response_model=ApplicationPackageView)
def update_application_package(
    package_id: uuid.UUID,
    request: ApplicationPackageUpdateRequest,
    session: Session = Depends(get_db),
    service: ApplicationPackageService = Depends(get_application_package_service),
) -> ApplicationPackageView:
    return _call(service.update, session, package_id, request)


@router.patch("/{package_id}/outputs", response_model=ApplicationPackageView)
def update_application_package_outputs(
    package_id: uuid.UUID,
    request: ApplicationPackageOutputsUpdateRequest,
    session: Session = Depends(get_db),
    service: ApplicationPackageService = Depends(get_application_package_service),
) -> ApplicationPackageView:
    return _call(service.update_outputs, session, package_id, request)


def _call(function, *args):
    try:
        return function(*args)
    except ApplicationPackageNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ApplicationPackageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

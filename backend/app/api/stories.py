"""Career Story Intelligence endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.knowledge import DEMO_USER_ID
from app.schemas.stories import (
    StoryCreateRequest,
    StoryDiscoveryResponse,
    StoryMergeRequest,
    StoryRenameRequest,
    StorySplitRequest,
    StoryUpdateRequest,
    StoryView,
)
from app.services.story_approval import StoryApprovalService
from app.services.story_discovery import StoryDiscoveryService
from app.services.story_operations import StoryOperationsService
from app.services.story_repository import (
    StoryNotFoundError,
    StoryRepository,
    StoryValidationError,
)

router = APIRouter(prefix="/stories", tags=["stories"])


def get_story_repository() -> StoryRepository:
    return StoryRepository()


def get_story_discovery(
    repository: StoryRepository = Depends(get_story_repository),
) -> StoryDiscoveryService:
    return StoryDiscoveryService(repository=repository)


def get_story_approval(
    repository: StoryRepository = Depends(get_story_repository),
) -> StoryApprovalService:
    return StoryApprovalService(repository=repository)


def get_story_operations(
    repository: StoryRepository = Depends(get_story_repository),
) -> StoryOperationsService:
    return StoryOperationsService(repository=repository)


@router.get("", response_model=list[StoryView])
def list_stories(
    include_archived: bool = Query(default=False),
    session: Session = Depends(get_db),
    repository: StoryRepository = Depends(get_story_repository),
) -> list[StoryView]:
    records = repository.list_records(
        session, DEMO_USER_ID, include_archived=include_archived
    )
    return [repository.to_view(session, story) for story in records]


@router.post("", response_model=StoryView, status_code=status.HTTP_201_CREATED)
def create_story(
    request: StoryCreateRequest,
    session: Session = Depends(get_db),
    operations: StoryOperationsService = Depends(get_story_operations),
) -> StoryView:
    return _call(operations.create, session, DEMO_USER_ID, request)


@router.post("/discover", response_model=StoryDiscoveryResponse)
def discover_stories(
    session: Session = Depends(get_db),
    discovery: StoryDiscoveryService = Depends(get_story_discovery),
) -> StoryDiscoveryResponse:
    return _call(discovery.discover, session, DEMO_USER_ID)


@router.post("/merge", response_model=StoryView, status_code=status.HTTP_201_CREATED)
def merge_stories(
    request: StoryMergeRequest,
    session: Session = Depends(get_db),
    operations: StoryOperationsService = Depends(get_story_operations),
) -> StoryView:
    return _call(operations.merge, session, DEMO_USER_ID, request)


@router.get("/{story_id}", response_model=StoryView)
def get_story(
    story_id: uuid.UUID,
    session: Session = Depends(get_db),
    repository: StoryRepository = Depends(get_story_repository),
) -> StoryView:
    try:
        return repository.to_view(
            session, repository.get_record(session, DEMO_USER_ID, story_id)
        )
    except StoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch("/{story_id}", response_model=StoryView)
def update_story(
    story_id: uuid.UUID,
    request: StoryUpdateRequest,
    session: Session = Depends(get_db),
    operations: StoryOperationsService = Depends(get_story_operations),
) -> StoryView:
    return _call(operations.update, session, DEMO_USER_ID, story_id, request)


@router.post("/{story_id}/rename", response_model=StoryView)
def rename_story(
    story_id: uuid.UUID,
    request: StoryRenameRequest,
    session: Session = Depends(get_db),
    operations: StoryOperationsService = Depends(get_story_operations),
) -> StoryView:
    return _call(operations.rename, session, DEMO_USER_ID, story_id, request)


@router.post("/{story_id}/approve", response_model=StoryView)
def approve_story(
    story_id: uuid.UUID,
    session: Session = Depends(get_db),
    approval: StoryApprovalService = Depends(get_story_approval),
) -> StoryView:
    return _call(approval.approve, session, DEMO_USER_ID, story_id)


@router.post("/{story_id}/reject", response_model=StoryView)
def reject_story(
    story_id: uuid.UUID,
    session: Session = Depends(get_db),
    approval: StoryApprovalService = Depends(get_story_approval),
) -> StoryView:
    return _call(approval.reject, session, DEMO_USER_ID, story_id)


@router.post("/{story_id}/archive", response_model=StoryView)
def archive_story(
    story_id: uuid.UUID,
    session: Session = Depends(get_db),
    approval: StoryApprovalService = Depends(get_story_approval),
) -> StoryView:
    return _call(approval.archive, session, DEMO_USER_ID, story_id)


@router.post("/{story_id}/split", response_model=StoryView)
def split_story(
    story_id: uuid.UUID,
    request: StorySplitRequest,
    session: Session = Depends(get_db),
    operations: StoryOperationsService = Depends(get_story_operations),
) -> StoryView:
    return _call(operations.split, session, DEMO_USER_ID, story_id, request)


def _call(function, *args):
    try:
        return function(*args)
    except StoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except StoryValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

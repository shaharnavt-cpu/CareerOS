"""Service health endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Report whether the API process is running."""

    return {"status": "ok"}

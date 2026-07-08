"""Service and database health endpoint."""

import asyncio

from fastapi import APIRouter, Query

from app.db.session import engine
from app.services.database_health import get_database_health

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    developer: bool = Query(default=False),
    refresh: bool = Query(default=False),
) -> dict[str, object]:
    """Report API and PostgreSQL health with an actionable degraded state."""

    monitor = get_database_health()
    await asyncio.to_thread(monitor.check, engine, force=refresh)
    database = monitor.snapshot(developer=developer)
    return {
        "status": "ok" if database["status"] == "available" else "degraded",
        "api": "available",
        "database": database,
    }

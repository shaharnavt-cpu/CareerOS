"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import engine
from app.services.database_health import classify_database_failure, get_database_health

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Check critical dependencies without preventing degraded startup."""

    await asyncio.to_thread(get_database_health().check, engine, force=True)
    yield


app = FastAPI(
    title="CareerOS API",
    description="Backend foundation for CareerOS.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")


@app.exception_handler(OperationalError)
async def database_error_handler(_: Request, error: OperationalError) -> JSONResponse:
    """Return a structured database outage instead of leaking driver errors."""

    failure = classify_database_failure(error)
    get_database_health().mark_failure(failure)
    return JSONResponse(
        status_code=503,
        content={
            "error": {
                "code": failure.code,
                "message": failure.friendly_message,
            }
        },
    )

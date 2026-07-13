"""Top-level API router."""

from fastapi import APIRouter

from app.api.applications import router as applications_router
from app.api.diagnosis import router as diagnosis_router
from app.api.health import router as health_router
from app.api.knowledge import router as knowledge_router
from app.api.listening import router as listening_router
from app.api.proof_artifacts import router as proof_artifacts_router
from app.api.stories import router as stories_router

api_router = APIRouter()
api_router.include_router(applications_router)
api_router.include_router(diagnosis_router)
api_router.include_router(health_router)
api_router.include_router(knowledge_router)
api_router.include_router(listening_router)
api_router.include_router(proof_artifacts_router)
api_router.include_router(stories_router)

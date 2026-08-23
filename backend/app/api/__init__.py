from fastapi import APIRouter

from app.api.actions import router as actions_router
from app.api.evidence import router as evidence_router
from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.scores import router as scores_router
from app.api.uploads import router as uploads_router
from app.api.venues import router as venues_router
from app.api.workflows import router as workflows_router

router = APIRouter()
router.include_router(health_router)
router.include_router(venues_router)
router.include_router(incidents_router)
router.include_router(scores_router)
router.include_router(actions_router)
router.include_router(evidence_router)
router.include_router(uploads_router)
router.include_router(workflows_router)

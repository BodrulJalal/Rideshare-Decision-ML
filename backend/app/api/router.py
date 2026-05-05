from fastapi import APIRouter

from app.api.endpoints.copilot import router as copilot_router
from app.api.endpoints.health import router as health_router
from app.api.endpoints.relocation import router as relocation_router


router = APIRouter()
router.include_router(copilot_router)
router.include_router(health_router)
router.include_router(relocation_router)

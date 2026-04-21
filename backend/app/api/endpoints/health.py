from fastapi import APIRouter

from app.schemas import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok")

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_services
from app.core.container import AppServices
from app.schemas import TripEvaluationRequest, TripEvaluationResponse


router = APIRouter(tags=["trip-evaluation"])


@router.get("/api/trip-pickup-zones", response_model=list[str])
def list_trip_pickup_zones(services: AppServices = Depends(get_services)):
    return services.fare_service.available_pickup_zones()


@router.get("/api/resolve-trip-zone", response_model=str)
def resolve_trip_zone(latitude: float, longitude: float, services: AppServices = Depends(get_services)):
    try:
        return services.traffic_service.resolve_current_zone(None, None, latitude, longitude).name
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/trip-types", response_model=list[str])
def list_trip_types(services: AppServices = Depends(get_services)):
    return services.fare_service.available_trip_types()


@router.post("/api/evaluate-trip", response_model=TripEvaluationResponse)
def evaluate_trip(payload: TripEvaluationRequest, services: AppServices = Depends(get_services)):
    try:
        return TripEvaluationResponse(**services.fare_service.evaluate_offer(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

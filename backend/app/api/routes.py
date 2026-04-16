from fastapi import APIRouter, HTTPException

from app.data.trip_dataset import get_zones
from app.ml.model_manager import ModelManager
from app.models.schemas import (
    GeoJsonFeatureCollection,
    HealthResponse,
    RelocationZoneOption,
    TripEvaluationRequest,
    TripEvaluationResponse,
    ZoneRecommendationRequest,
    ZoneRecommendationResponse,
)
from app.services.fare_predictor import FarePredictionService
from app.services.recommender import ZoneRecommendationService
from app.services.traffic import TrafficService


router = APIRouter()
model_manager = ModelManager()
traffic_service = TrafficService()
zone_service = ZoneRecommendationService(model_manager, traffic_service)
fare_service = FarePredictionService(model_manager)


@router.get("/api/health", response_model=HealthResponse)
def health_check():
    return HealthResponse(status="ok")


@router.get("/api/zones", response_model=list[str])
def list_zones():
    return [zone.name for zone in get_zones()]


@router.get("/api/relocation-zones", response_model=list[RelocationZoneOption])
def list_relocation_zones():
    return zone_service.available_relocation_zones()


@router.get("/api/relocation-zones-geojson", response_model=GeoJsonFeatureCollection)
def relocation_zones_geojson():
    try:
        return GeoJsonFeatureCollection(**zone_service.relocation_geojson())
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/recommend-zone", response_model=ZoneRecommendationResponse)
def recommend_zone(payload: ZoneRecommendationRequest):
    try:
        return ZoneRecommendationResponse(**zone_service.recommend(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/evaluate-trip", response_model=TripEvaluationResponse)
def evaluate_trip(payload: TripEvaluationRequest):
    try:
        return TripEvaluationResponse(**fare_service.evaluate_offer(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_services
from app.core.container import AppServices
from app.data.trip_dataset import get_zones
from app.schemas import (
    GeoJsonFeatureCollection,
    RelocationZoneOption,
    ZoneRecommendationRequest,
    ZoneRecommendationResponse,
)


router = APIRouter(tags=["relocation"])


@router.get("/api/zones", response_model=list[str])
def list_zones():
    return [zone.name for zone in get_zones()]


@router.get("/api/relocation-zones", response_model=list[RelocationZoneOption])
def list_relocation_zones(services: AppServices = Depends(get_services)):
    return services.zone_service.available_relocation_zones()


@router.get("/api/relocation-zones-geojson", response_model=GeoJsonFeatureCollection)
def relocation_zones_geojson(services: AppServices = Depends(get_services)):
    try:
        return GeoJsonFeatureCollection(**services.zone_service.relocation_geojson())
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/recommend-zone", response_model=ZoneRecommendationResponse)
def recommend_zone(payload: ZoneRecommendationRequest, services: AppServices = Depends(get_services)):
    try:
        return ZoneRecommendationResponse(**services.zone_service.recommend(**payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

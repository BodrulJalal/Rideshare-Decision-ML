from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class ZoneRecommendationRequest(BaseModel):
    current_zone: str | None = Field(default=None)
    address: str | None = Field(default=None)
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    hour: int | None = Field(default=None, ge=0, le=23)
    latitude: float | None = Field(default=None)
    longitude: float | None = Field(default=None)


class RelocationZoneOption(BaseModel):
    id: int
    name: str


class GeoJsonFeatureProperties(BaseModel):
    LocationID: int
    zone: str
    borough: str | None = None
    service_zone: str | None = None


class GeoJsonGeometry(BaseModel):
    type: str
    coordinates: list


class GeoJsonFeature(BaseModel):
    type: str
    properties: GeoJsonFeatureProperties
    geometry: GeoJsonGeometry


class GeoJsonFeatureCollection(BaseModel):
    type: str
    features: list[GeoJsonFeature]


class ZoneCandidate(BaseModel):
    zone: str
    travel_minutes: float
    demand_index: float
    predicted_hourly_earnings: float
    net_score: float


class ZoneRecommendationResponse(BaseModel):
    current_zone: str
    recommended_zone: str
    travel_minutes: float
    estimated_demand: float
    predicted_hourly_earnings: float
    confidence_gap: float
    driver_message: str
    top_alternatives: list[ZoneCandidate]


class TripEvaluationRequest(BaseModel):
    pickup_zone: str
    trip_type: str
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    hour: int | None = Field(default=None, ge=0, le=23)
    trip_minutes: float = Field(gt=0)


class TripDestinationCandidate(BaseModel):
    zone: str
    probability: float


class TripEvaluationResponse(BaseModel):
    pickup_zone: str
    trip_type: str
    trip_minutes: float
    predicted_dropoff_zone: str
    prediction_confidence: float
    top_dropoff_zones: list[TripDestinationCandidate]
    driver_message: str

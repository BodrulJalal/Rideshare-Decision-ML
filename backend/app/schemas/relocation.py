from __future__ import annotations

from pydantic import BaseModel, Field


class ZoneRecommendationRequest(BaseModel):
  current_zone: str | None = Field(default=None)
  address: str | None = Field(default=None)
  day_of_week: int | None = Field(default=None, ge=0, le=6)
  hour: int | None = Field(default=None, ge=0, le=23)
  latitude: float | None = Field(default=None)
  longitude: float | None = Field(default=None)


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

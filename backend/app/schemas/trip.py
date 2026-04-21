from __future__ import annotations

from pydantic import BaseModel, Field


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

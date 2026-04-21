from __future__ import annotations

from pydantic import BaseModel


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

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.ml.model_manager import ModelManager
from app.services.recommender import ZoneRecommendationService
from app.services.traffic import TrafficService


@dataclass(frozen=True)
class AppServices:
    model_manager: ModelManager
    traffic_service: TrafficService
    zone_service: ZoneRecommendationService


@lru_cache(maxsize=1)
def get_app_services() -> AppServices:
    model_manager = ModelManager()
    traffic_service = TrafficService()

    return AppServices(
        model_manager=model_manager,
        traffic_service=traffic_service,
        zone_service=ZoneRecommendationService(model_manager, traffic_service),
    )

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.ml.model_manager import ModelManager
from app.services.copilot import CopilotService
from app.services.recommender import ZoneRecommendationService
from app.services.traffic import TrafficService


@dataclass(frozen=True)
class AppServices:
    model_manager: ModelManager
    traffic_service: TrafficService
    zone_service: ZoneRecommendationService
    copilot_service: CopilotService


@lru_cache(maxsize=1)
def get_app_services() -> AppServices:
    model_manager = ModelManager()
    traffic_service = TrafficService()

    zone_service = ZoneRecommendationService(model_manager, traffic_service)
    return AppServices(
        model_manager=model_manager,
        traffic_service=traffic_service,
        zone_service=zone_service,
        copilot_service=CopilotService(zone_service),
    )

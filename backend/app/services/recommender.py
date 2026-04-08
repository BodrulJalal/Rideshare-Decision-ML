from __future__ import annotations

from app.data.trip_dataset import get_zones


class ZoneRecommendationService:
    def __init__(self, model_manager, traffic_service):
        self.model_manager = model_manager
        self.traffic_service = traffic_service

    def recommend(
        self,
        current_zone: str | None = None,
        address: str | None = None,
        day_of_week: int | None = None,
        hour: int | None = None,
        latitude=None,
        longitude=None,
    ):
        origin = self.traffic_service.resolve_current_zone(current_zone, address, latitude, longitude)
        day_of_week, hour = self.traffic_service.time_context(day_of_week, hour)
        zones = get_zones()

        candidates = []
        for zone in zones:
            travel_minutes = self.traffic_service.estimate_travel_minutes(origin, zone, hour)
            demand_index = self.traffic_service.estimate_demand(zone, hour)
            predicted_hourly = self.model_manager.zone_model.predict(
                [[zone.name, day_of_week, hour, demand_index, travel_minutes]]
            )[0]
            net_score = predicted_hourly - travel_minutes * 0.55

            candidates.append(
                {
                    "zone": zone.name,
                    "travel_minutes": round(float(travel_minutes), 1),
                    "demand_index": round(float(demand_index), 1),
                    "predicted_hourly_earnings": round(float(predicted_hourly), 2),
                    "net_score": round(float(net_score), 2),
                }
            )

        ranked = sorted(candidates, key=lambda item: item["net_score"], reverse=True)
        best = ranked[0]
        second_best = ranked[1]
        advantage = round(best["net_score"] - second_best["net_score"], 2)

        return {
            "current_zone": origin.name,
            "recommended_zone": best["zone"],
            "travel_minutes": best["travel_minutes"],
            "estimated_demand": best["demand_index"],
            "predicted_hourly_earnings": best["predicted_hourly_earnings"],
            "confidence_gap": advantage,
            "driver_message": (
                f"Head toward {best['zone']}. It projects about ${best['predicted_hourly_earnings']}/hr "
                f"with a {best['travel_minutes']}-minute repositioning drive."
            ),
            "top_alternatives": ranked[:3],
        }

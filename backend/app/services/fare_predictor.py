from __future__ import annotations

from datetime import datetime

from app.data.trip_dataset import get_zone_lookup, get_zones


class FarePredictionService:
    def __init__(self, model_manager):
        self.model_manager = model_manager

    def evaluate_offer(self, pickup_zone: str, trip_minutes, rider_rating, day_of_week: int | None = None, hour: int | None = None):
        zone_lookup = get_zone_lookup()
        zones = get_zones()
        if pickup_zone.lower() not in zone_lookup:
            raise ValueError(f"Unknown pickup zone. Choose one of: {', '.join(zone.name for zone in zones)}.")

        trip_minutes = float(trip_minutes)
        rider_rating = float(rider_rating)
        current = datetime.now()
        resolved_day = current.weekday() if day_of_week is None else int(day_of_week)
        resolved_hour = current.hour if hour is None else int(hour)
        probabilities = self.model_manager.trip_model.predict_proba(
            [[pickup_zone, resolved_day, resolved_hour, trip_minutes]]
        )[0]
        base_probability = float(probabilities[1])
        rating_adjustment = max(-0.1, min(0.1, (rider_rating - 4.75) * 0.3))
        weekend_adjustment = 0.04 if resolved_day in {4, 5} and resolved_hour >= 18 else 0.0
        high_fare_probability = min(0.99, max(0.01, base_probability + rating_adjustment + weekend_adjustment))

        recommendation = "Accept" if high_fare_probability >= 0.62 else "Be selective"
        expected_tip = max(0, round((rider_rating - 4.5) * 8 + trip_minutes * 0.12, 2))

        return {
            "pickup_zone": pickup_zone,
            "trip_minutes": round(trip_minutes, 1),
            "rider_rating": round(rider_rating, 2),
            "high_fare_probability": round(high_fare_probability, 3),
            "likely_high_fare": high_fare_probability >= 0.5,
            "expected_tip_signal": expected_tip,
            "driver_message": (
                f"{recommendation}: this trip has a {high_fare_probability * 100:.1f}% chance "
                "of landing in the high-fare tier including tip."
            ),
        }

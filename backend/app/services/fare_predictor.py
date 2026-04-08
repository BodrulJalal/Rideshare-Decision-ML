from __future__ import annotations

from app.data.sample_data import ZONE_LOOKUP, ZONES


class FarePredictionService:
    def __init__(self, model_manager):
        self.model_manager = model_manager

    def evaluate_offer(self, pickup_zone: str, trip_minutes, rider_rating):
        if pickup_zone.lower() not in ZONE_LOOKUP:
            raise ValueError(f"Unknown pickup zone. Choose one of: {', '.join(zone.name for zone in ZONES)}.")

        trip_minutes = float(trip_minutes)
        rider_rating = float(rider_rating)
        probabilities = self.model_manager.trip_model.predict_proba(
            [[pickup_zone, trip_minutes, rider_rating]]
        )[0]
        high_fare_probability = float(probabilities[1])

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

from __future__ import annotations

from datetime import datetime

import pandas as pd

from app.data.trip_dataset import get_zone_lookup, get_zones


class FarePredictionService:
    def __init__(self, model_manager):
        self.model_manager = model_manager

    def available_pickup_zones(self) -> list[str]:
        trip_artifact = self.model_manager.trip_artifact
        if trip_artifact is not None:
            return list(trip_artifact.label_encoders["pickup_zone"].classes_)
        return [zone.name for zone in get_zones()]

    def available_trip_types(self) -> list[str]:
        trip_artifact = self.model_manager.trip_artifact
        if trip_artifact is not None:
            return list(trip_artifact.label_encoders["trip_type"].classes_)
        return ["UberX", "Comfort", "Electric", "Share"]

    def evaluate_offer(self, pickup_zone: str, trip_type: str, trip_minutes, day_of_week: int | None = None, hour: int | None = None):
        current = datetime.now()
        resolved_day = current.weekday() if day_of_week is None else int(day_of_week)
        resolved_hour = current.hour if hour is None else int(hour)

        trip_minutes = float(trip_minutes)
        trip_artifact = self.model_manager.trip_artifact
        if trip_artifact is None:
            zone_lookup = get_zone_lookup()
            zones = get_zones()
            if pickup_zone.lower() not in zone_lookup:
                raise ValueError(f"Unknown pickup zone. Choose one of: {', '.join(zone.name for zone in zones)}.")
            raise ValueError("Saved dropoff prediction model is not available.")

        encoders = trip_artifact.label_encoders
        if pickup_zone not in encoders["pickup_zone"].classes_:
            raise ValueError(f"Unknown pickup zone. Choose one of: {', '.join(self.available_pickup_zones())}.")
        if trip_type not in encoders["trip_type"].classes_:
            raise ValueError(f"Unknown ride type. Choose one of: {', '.join(self.available_trip_types())}.")

        model_input = pd.DataFrame(
            [[
                int(encoders["trip_type"].transform([trip_type])[0]),
                int(resolved_day),
                int(resolved_hour),
                float(trip_minutes),
                int(encoders["pickup_zone"].transform([pickup_zone])[0]),
            ]],
            columns=["Trip_Type_Encoded", "Day_of_Week_Num", "Hour_Bucket", "Duration_Minutes", "Pickup_Zone_Encoded"],
        )
        predicted_label = int(trip_artifact.model.predict(model_input)[0])
        predicted_zone = str(encoders["dropoff_zone"].inverse_transform([predicted_label])[0])
        probabilities = trip_artifact.model.predict_proba(model_input)[0]
        top_indices = probabilities.argsort()[-3:][::-1]
        top_dropoff_zones = [
            {
                "zone": str(encoders["dropoff_zone"].inverse_transform([int(index)])[0]),
                "probability": round(float(probabilities[int(index)]), 3),
            }
            for index in top_indices
        ]
        confidence = round(float(probabilities[predicted_label]), 3)

        return {
            "pickup_zone": pickup_zone,
            "trip_type": trip_type,
            "trip_minutes": round(trip_minutes, 1),
            "predicted_dropoff_zone": predicted_zone,
            "prediction_confidence": confidence,
            "top_dropoff_zones": top_dropoff_zones,
            "driver_message": (
                f"This trip is most likely to end in {predicted_zone}, based on ride type, pickup area, day, time, and trip length."
            ),
        }

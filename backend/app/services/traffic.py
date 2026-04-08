from __future__ import annotations

from math import cos, radians, sqrt

from app.data.sample_data import ZONE_LOOKUP, ZONES


class TrafficService:
    def resolve_current_zone(self, current_zone: str | None, latitude, longitude):
        if current_zone:
            zone = ZONE_LOOKUP.get(current_zone.lower())
            if zone:
                return zone
            raise ValueError(f"Unknown zone '{current_zone}'. Choose one of: {', '.join(z.name for z in ZONES)}.")

        if latitude is None or longitude is None:
            raise ValueError("Provide either a current zone or latitude/longitude coordinates.")

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError) as exc:
            raise ValueError("Latitude and longitude must be valid numbers.") from exc

        return min(
            ZONES,
            key=lambda zone: self._distance_miles(latitude, longitude, zone.latitude, zone.longitude),
        )

    def estimate_travel_minutes(self, origin, destination, hour: int):
        distance = self._distance_miles(origin.latitude, origin.longitude, destination.latitude, destination.longitude)
        peak_multiplier = 1.25 if hour in {7, 8, 9, 16, 17, 18, 19} else 0.95
        downtown_penalty = 1.1 if "Downtown" in {origin.name, destination.name} else 1.0
        return round(max(4, distance * 3.8 * peak_multiplier * downtown_penalty), 1)

    def estimate_demand(self, zone, hour: int):
        peak_boost = 14 if hour in {7, 8, 9, 16, 17, 18, 19, 22} else 0
        airport_boost = 10 if zone.name == "Airport" and hour in {5, 6, 7, 20, 21, 22} else 0
        event_boost = 17 if zone.name == "Stadium District" and hour in {17, 18, 19, 20, 21} else 0
        nightlife_boost = 8 if zone.name == "Downtown" and hour in {21, 22, 23, 0} else 0
        return round(zone.base_demand + peak_boost + airport_boost + event_boost + nightlife_boost, 1)

    def _distance_miles(self, lat1, lon1, lat2, lon2):
        lat_scale = 69.0
        lon_scale = 69.172 * cos(radians((lat1 + lat2) / 2))
        return sqrt(((lat2 - lat1) * lat_scale) ** 2 + ((lon2 - lon1) * lon_scale) ** 2)

    # Replace estimate_travel_minutes with a live Mapbox, Google Maps, or HERE call
    # to use route-based ETA instead of the built-in mock estimator.

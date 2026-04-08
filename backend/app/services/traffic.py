from __future__ import annotations

from datetime import datetime
from math import cos, radians, sqrt

from app.data.trip_dataset import get_zone_lookup, get_zones, infer_zone_from_text


class TrafficService:
    def resolve_current_zone(self, current_zone: str | None, address: str | None, latitude, longitude):
        zone_lookup = get_zone_lookup()
        zones = get_zones()
        if current_zone:
            zone = zone_lookup.get(current_zone.lower())
            if zone:
                return zone
            raise ValueError(f"Unknown zone '{current_zone}'. Choose one of: {', '.join(z.name for z in zones)}.")

        if address:
            inferred_zone = infer_zone_from_text(address)
            if inferred_zone and inferred_zone.lower() in zone_lookup:
                return zone_lookup[inferred_zone.lower()]
            raise ValueError(
                "Could not map that address to a known zone yet. Try including the borough or use a listed zone/coordinates."
            )

        if latitude is None or longitude is None:
            raise ValueError("Provide a zone, an address, or latitude/longitude coordinates.")

        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError) as exc:
            raise ValueError("Latitude and longitude must be valid numbers.") from exc

        return min(
            zones,
            key=lambda zone: self._distance_miles(latitude, longitude, zone.latitude, zone.longitude),
        )

    def estimate_travel_minutes(self, origin, destination, hour: int):
        distance = self._distance_miles(origin.latitude, origin.longitude, destination.latitude, destination.longitude)
        peak_multiplier = 1.25 if hour in {7, 8, 9, 16, 17, 18, 19} else 0.95
        core_manhattan_zones = {"New York", "New York City", "Manhattan"}
        core_penalty = 1.1 if origin.name in core_manhattan_zones or destination.name in core_manhattan_zones else 1.0
        return round(max(4, distance * 3.8 * peak_multiplier * core_penalty), 1)

    def estimate_demand(self, zone, hour: int):
        peak_boost = 14 if hour in {7, 8, 9, 16, 17, 18, 19, 22} else 0
        airport_adjacent = {"Flushing", "College Point", "East Elmhurst", "Corona"}
        nightlife_core = {"New York", "New York City", "Manhattan", "Long Island City", "Astoria", "Brooklyn"}
        airport_boost = 10 if zone.name in airport_adjacent and hour in {5, 6, 7, 20, 21, 22} else 0
        event_boost = 6 if zone.name in {"Bronx", "Flushing", "Brooklyn"} and hour in {17, 18, 19, 20, 21} else 0
        nightlife_boost = 8 if zone.name in nightlife_core and hour in {21, 22, 23, 0} else 0
        return round(zone.base_demand + peak_boost + airport_boost + event_boost + nightlife_boost, 1)

    def time_context(self, day_of_week: int | None, hour: int | None):
        current = datetime.now()
        resolved_day = current.weekday() if day_of_week is None else int(day_of_week)
        resolved_hour = current.hour if hour is None else int(hour)
        return resolved_day, resolved_hour

    def _distance_miles(self, lat1, lon1, lat2, lon2):
        lat_scale = 69.0
        lon_scale = 69.172 * cos(radians((lat1 + lat2) / 2))
        return sqrt(((lat2 - lat1) * lat_scale) ** 2 + ((lon2 - lon1) * lon_scale) ** 2)

    # Replace estimate_travel_minutes with a live Mapbox, Google Maps, or HERE call
    # to use route-based ETA instead of the built-in mock estimator.

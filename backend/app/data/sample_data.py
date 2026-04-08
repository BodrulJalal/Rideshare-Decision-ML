from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Zone:
    name: str
    latitude: float
    longitude: float
    base_demand: float
    base_fare: float
    driver_competition: float


ZONES = [
    Zone("Downtown", 40.7128, -74.0060, 92, 34, 0.82),
    Zone("Airport", 40.6413, -73.7781, 87, 42, 0.67),
    Zone("Midtown", 40.7549, -73.9840, 79, 31, 0.73),
    Zone("Stadium District", 40.8296, -73.9262, 68, 29, 0.58),
    Zone("University", 40.7295, -73.9965, 63, 24, 0.51),
    Zone("Waterfront", 40.7001, -74.0122, 58, 27, 0.49),
]

ZONE_LOOKUP = {zone.name.lower(): zone for zone in ZONES}


def build_zone_recommendation_dataset(sample_size: int = 1400, seed: int = 7):
    rng = np.random.default_rng(seed)
    rows = []
    targets = []

    for _ in range(sample_size):
        zone = ZONES[rng.integers(0, len(ZONES))]
        hour = int(rng.integers(0, 24))
        is_peak = 1 if hour in {7, 8, 9, 16, 17, 18, 19, 22} else 0
        event_boost = 1 if zone.name == "Stadium District" and hour in {17, 18, 19, 20, 21} else 0
        airport_boost = 1 if zone.name == "Airport" and hour in {5, 6, 7, 20, 21, 22} else 0
        nightlife_boost = 1 if zone.name == "Downtown" and hour in {21, 22, 23, 0} else 0

        demand_index = (
            zone.base_demand
            + is_peak * 12
            + event_boost * 16
            + airport_boost * 11
            + nightlife_boost * 9
            + rng.normal(0, 6)
        )
        demand_index = max(10, demand_index)

        travel_minutes = max(4, rng.normal(13 + (1 - zone.driver_competition) * 9, 5))
        expected_hourly_earnings = (
            zone.base_fare * 1.35
            + demand_index * 0.48
            - travel_minutes * 0.72
            - zone.driver_competition * 11
            + rng.normal(0, 6)
        )

        rows.append(
            {
                "zone": zone.name,
                "hour": hour,
                "demand_index": round(float(demand_index), 2),
                "travel_minutes": round(float(travel_minutes), 2),
            }
        )
        targets.append(round(float(expected_hourly_earnings), 2))

    return rows, np.array(targets)


def build_trip_offer_dataset(sample_size: int = 1600, seed: int = 13):
    rng = np.random.default_rng(seed)
    rows = []
    labels = []

    for _ in range(sample_size):
        zone = ZONES[rng.integers(0, len(ZONES))]
        trip_minutes = max(5, rng.normal(24, 10))
        rider_rating = float(np.clip(rng.normal(4.76, 0.2), 4.1, 5.0))
        peak_multiplier = 1.18 if rng.random() > 0.6 else 0.94
        gross_fare = (
            zone.base_fare * 0.45
            + trip_minutes * 1.55
            + rider_rating * 4.1
            + zone.base_demand * 0.09
        ) * peak_multiplier + rng.normal(0, 5)
        tipped_fare = gross_fare + max(0, (rider_rating - 4.55) * 14 + rng.normal(1.5, 2))
        high_fare = 1 if tipped_fare >= 58 else 0

        rows.append(
            {
                "pickup_zone": zone.name,
                "trip_minutes": round(float(trip_minutes), 2),
                "rider_rating": round(float(rider_rating), 2),
            }
        )
        labels.append(high_fare)

    return rows, np.array(labels)

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from statistics import mean

import numpy as np

from app.data.sample_data import (
    ZONES as SAMPLE_ZONES,
    ZONE_LOOKUP as SAMPLE_ZONE_LOOKUP,
    build_trip_offer_dataset as build_sample_trip_offer_dataset,
    build_zone_recommendation_dataset as build_sample_zone_recommendation_dataset,
)


@dataclass(frozen=True)
class Zone:
    name: str
    latitude: float
    longitude: float
    base_demand: float
    base_fare: float
    driver_competition: float


ZONE_CENTROIDS = {
    "New York": (40.7831, -73.9712),
    "New York City": (40.7580, -73.9855),
    "Manhattan": (40.7831, -73.9712),
    "Brooklyn": (40.6782, -73.9442),
    "Flushing": (40.7654, -73.8174),
    "College Point": (40.7876, -73.8459),
    "Corona": (40.7465, -73.8590),
    "Queens": (40.7282, -73.7949),
    "Ridgewood": (40.7004, -73.9033),
    "Forest Hills": (40.7181, -73.8448),
    "Fresh Meadows": (40.7340, -73.7826),
    "East Elmhurst": (40.7617, -73.8665),
    "Elmhurst": (40.7365, -73.8779),
    "Richmond Hill": (40.6998, -73.8310),
    "Howard Beach": (40.6573, -73.8390),
    "South Richmond Hill": (40.6893, -73.8224),
    "South Ozone Park": (40.6804, -73.8080),
    "Kew Gardens": (40.7143, -73.8301),
    "Sunnyside": (40.7433, -73.9196),
    "Astoria": (40.7644, -73.9235),
    "Long Island City": (40.7447, -73.9485),
    "Bronx": (40.8448, -73.8648),
    "Mt Vernon": (40.9126, -73.8371),
    "Yonkers": (40.9312, -73.8988),
}

ZONE_ALIASES = {
    "new york": "New York",
    "new york city": "New York City",
    "manhattan": "Manhattan",
    "brooklyn": "Brooklyn",
    "bronx": "Bronx",
    "flushing": "Flushing",
    "college point": "College Point",
    "corona": "Corona",
    "queens": "Queens",
    "ridgewood": "Ridgewood",
    "forest hills": "Forest Hills",
    "fresh meadows": "Fresh Meadows",
    "east elmhurst": "East Elmhurst",
    "elmhurst": "Elmhurst",
    "richmond hill": "Richmond Hill",
    "howard beach": "Howard Beach",
    "south richmond hill": "South Richmond Hill",
    "south ozone park": "South Ozone Park",
    "kew gardens": "Kew Gardens",
    "sunnyside": "Sunnyside",
    "astoria": "Astoria",
    "long island city": "Long Island City",
    "yonkers": "Yonkers",
    "mt vernon": "Mt Vernon",
}


def _dataset_directory() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "trips"


def _dataset_path() -> Path | None:
    exact_match = _dataset_directory() / "Uber Rides - Cleaned.csv"
    if exact_match.exists():
        return exact_match

    csv_files = sorted(_dataset_directory().glob("*.csv"))
    return csv_files[0] if csv_files else None


def _to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_hour(value: str) -> int:
    value = (value or "").strip()
    if not value:
        return 0

    parsed = None
    for fmt in ("%I:%M %p", "%H:%M"):
        try:
            parsed = datetime.strptime(value, fmt)
            break
        except ValueError:
            continue

    return parsed.hour if parsed else 0


def _parse_day_of_week(value: str) -> int:
    value = (value or "").strip()
    if not value:
        return 0

    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).weekday()
        except ValueError:
            continue

    return 0


def normalize_zone_name(location: str) -> str:
    parts = [part.strip() for part in (location or "").split(",") if part.strip()]
    area = parts[-3].lower() if len(parts) >= 3 else (location or "").strip().lower()
    return ZONE_ALIASES.get(area, area.title() if area else "Unknown")


def infer_zone_from_text(text: str) -> str | None:
    normalized_text = (text or "").strip().lower()
    if not normalized_text:
        return None

    for alias, zone_name in sorted(ZONE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in normalized_text:
            return zone_name

    return None


def _trip_type_multiplier(trip_type: str) -> float:
    normalized = (trip_type or "").strip().lower()
    return {
        "share": 0.9,
        "uberx": 1.0,
        "uberx priority": 1.08,
        "comfort": 1.24,
        "electric": 1.05,
    }.get(normalized, 1.0)


def _estimated_trip_value(distance_miles: float, trip_minutes: float, surge_amount: float, tip_amount: float, trip_type: str) -> float:
    baseline = 2.75 + distance_miles * 1.85 + trip_minutes * 0.42 + surge_amount + tip_amount
    return round(baseline * _trip_type_multiplier(trip_type), 2)


@lru_cache(maxsize=1)
def load_trip_rows() -> tuple[dict[str, object], ...]:
    dataset_path = _dataset_path()
    if dataset_path is None:
        return tuple()

    rows: list[dict[str, object]] = []
    with dataset_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for raw_row in reader:
            trip_minutes = max(1.0, _to_float(raw_row.get("duration_sec")) / 60.0)
            distance_miles = max(0.1, _to_float(raw_row.get("distance_miles")))
            tip_amount = max(0.0, _to_float(raw_row.get("tip_amount")))
            surge_amount = max(0.0, _to_float(raw_row.get("surge_amount")))
            pickup_wait_min = max(0.0, _to_float(raw_row.get("pickup_wait_min")))
            zone_name = normalize_zone_name(str(raw_row.get("pickup_location", "")))

            rows.append(
                {
                    "pickup_zone": zone_name,
                    "dropoff_zone": normalize_zone_name(str(raw_row.get("dropoff_location", ""))),
                    "day_of_week": _parse_day_of_week(str(raw_row.get("trip_date", ""))),
                    "hour": _parse_hour(str(raw_row.get("trip_time", ""))),
                    "trip_minutes": round(trip_minutes, 2),
                    "distance_miles": round(distance_miles, 2),
                    "tip_amount": round(tip_amount, 2),
                    "surge_amount": round(surge_amount, 2),
                    "pickup_wait_min": round(pickup_wait_min, 2),
                    "trip_type": str(raw_row.get("trip_type", "")).strip() or "UberX",
                    "estimated_value": _estimated_trip_value(
                        distance_miles=distance_miles,
                        trip_minutes=trip_minutes,
                        surge_amount=surge_amount,
                        tip_amount=tip_amount,
                        trip_type=str(raw_row.get("trip_type", "")),
                    ),
                }
            )

    return tuple(rows)


@lru_cache(maxsize=1)
def get_zones() -> tuple[Zone, ...]:
    records = load_trip_rows()
    if not records:
        return tuple(
            Zone(
                name=zone.name,
                latitude=zone.latitude,
                longitude=zone.longitude,
                base_demand=zone.base_demand,
                base_fare=zone.base_fare,
                driver_competition=zone.driver_competition,
            )
            for zone in SAMPLE_ZONES
        )

    pickup_counts = Counter(str(record["pickup_zone"]) for record in records)
    dropoff_counts = Counter(str(record["dropoff_zone"]) for record in records)
    trip_counts = pickup_counts + dropoff_counts
    zone_values: defaultdict[str, list[float]] = defaultdict(list)
    for record in records:
        zone_values[str(record["pickup_zone"])].append(float(record["estimated_value"]))
        zone_values[str(record["dropoff_zone"])].append(float(record["estimated_value"]))

    max_trip_count = max(trip_counts.values())
    zones: list[Zone] = []
    for zone_name, trip_count in sorted(trip_counts.items(), key=lambda item: item[1], reverse=True):
        latitude, longitude = ZONE_CENTROIDS.get(zone_name, (40.7580, -73.9855))
        avg_value = mean(zone_values[zone_name])
        demand_ratio = trip_count / max_trip_count
        zones.append(
            Zone(
                name=zone_name,
                latitude=latitude,
                longitude=longitude,
                base_demand=round(45 + demand_ratio * 50, 1),
                base_fare=round(avg_value, 2),
                driver_competition=round(min(0.9, 0.35 + demand_ratio * 0.45), 2),
            )
        )

    return tuple(zones)


@lru_cache(maxsize=1)
def get_zone_lookup() -> dict[str, Zone]:
    zones = get_zones()
    if not zones:
        return SAMPLE_ZONE_LOOKUP
    return {zone.name.lower(): zone for zone in zones}


def build_zone_recommendation_dataset():
    records = load_trip_rows()
    if len(records) < 20:
        rows, targets = build_sample_zone_recommendation_dataset()
        enriched_rows = [
            {**row, "day_of_week": index % 7}
            for index, row in enumerate(rows)
        ]
        return enriched_rows, targets

    rng = np.random.default_rng(42)
    zone_time_counts = Counter(
        (str(record["pickup_zone"]), int(record["day_of_week"]), int(record["hour"]))
        for record in records
    )
    peak_pickups = max(zone_time_counts.values())

    rows: list[dict[str, object]] = []
    targets: list[float] = []

    for record in records:
        zone_name = str(record["pickup_zone"])
        day_of_week = int(record["day_of_week"])
        hour = int(record["hour"])
        demand_index = (
            35
            + 65 * (zone_time_counts[(zone_name, day_of_week, hour)] / peak_pickups)
            + float(record["surge_amount"]) * 8
        )
        travel_minutes = max(4.0, float(record["pickup_wait_min"]) + float(record["trip_minutes"]) * 0.28)
        gross_hourly = float(record["estimated_value"]) / max(float(record["trip_minutes"]) / 60.0, 0.35)
        weekend_bonus = 4.0 if day_of_week in {4, 5} else 0.0
        attractiveness = gross_hourly + demand_index * 0.18 - travel_minutes * 0.7 + weekend_bonus

        for _ in range(5):
            rows.append(
                {
                    "zone": zone_name,
                    "day_of_week": day_of_week,
                    "hour": hour,
                    "demand_index": round(float(demand_index + rng.normal(0, 3.2)), 2),
                    "travel_minutes": round(float(max(4.0, travel_minutes + rng.normal(0, 1.1))), 2),
                }
            )
            targets.append(round(float(attractiveness + rng.normal(0, 2.5)), 2))

    return rows, np.array(targets)


def build_trip_offer_dataset():
    records = load_trip_rows()
    if len(records) < 20:
        rows, labels = build_sample_trip_offer_dataset()
        enriched_rows = [
            {**row, "day_of_week": index % 7, "hour": (8 + index) % 24}
            for index, row in enumerate(rows)
        ]
        return enriched_rows, labels

    values = np.array([float(record["estimated_value"]) for record in records])
    high_value_cutoff = float(np.quantile(values, 0.65))
    rng = np.random.default_rng(7)

    rows: list[dict[str, object]] = []
    labels: list[int] = []
    for record in records:
        trip_minutes = float(record["trip_minutes"])
        estimated_value = float(record["estimated_value"])
        day_of_week = int(record["day_of_week"])
        hour = int(record["hour"])
        for _ in range(6):
            rows.append(
                {
                    "pickup_zone": str(record["pickup_zone"]),
                    "day_of_week": day_of_week,
                    "hour": hour,
                    "trip_minutes": round(float(max(1.0, trip_minutes + rng.normal(0, 1.4))), 2),
                }
            )
            labels.append(1 if estimated_value >= high_value_cutoff else 0)

    return rows, np.array(labels)

from __future__ import annotations

from collections.abc import Iterable
import math
from pathlib import Path

import numpy as np
import pandas as pd

from app.data.trip_dataset import get_zones


DAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

W_T1 = 0.60
W_T2 = 0.25
W_T3 = 0.15
JIT_ALPHA = 0.5
JIT_GAMMA = 0.9
JIT_EPSILON = 0.1
JIT_EPOCHS = 500


class ZoneRecommendationService:
    def __init__(self, model_manager, traffic_service):
        self.model_manager = model_manager
        self.traffic_service = traffic_service

    def available_relocation_zones(self) -> list[str]:
        artifact = self.model_manager.relocation_artifact
        if artifact is None:
            return [{"id": index + 1, "name": zone.name} for index, zone in enumerate(get_zones())]

        taxi_zones = artifact.taxi_zones.copy()
        taxi_zones = taxi_zones.dropna(subset=["LocationID", "Zone"])
        taxi_zones = taxi_zones.sort_values(["Zone", "LocationID"])
        return [
            {"id": int(row["LocationID"]), "name": str(row["Zone"])}
            for _, row in taxi_zones.iterrows()
        ]

    def relocation_geojson(self) -> dict:
        try:
            import shapefile
        except ModuleNotFoundError as exc:
            raise ValueError("The shapefile dependency is not installed. Install backend requirements first.") from exc

        shp_path = Path(__file__).resolve().parents[3] / "Model Building" / "content" / "taxi_zones" / "taxi_zones.shp"
        if not shp_path.exists():
            raise ValueError("Taxi zone shapefile was not found in Model Building/content/taxi_zones.")

        reader = shapefile.Reader(str(shp_path))
        field_names = [field[0] for field in reader.fields[1:]]
        features = []

        for shape_record in reader.iterShapeRecords():
            record = dict(zip(field_names, shape_record.record))
            geometry = self._shape_to_geojson_geometry(shape_record.shape)
            if geometry is None:
                continue

            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "LocationID": int(record["LocationID"]),
                        "zone": str(record["zone"]),
                        "borough": str(record["borough"]) if record.get("borough") is not None else None,
                        "service_zone": str(record["service_zone"]) if record.get("service_zone") is not None else None,
                    },
                    "geometry": geometry,
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
        }

    def recommend(
        self,
        current_zone: str | None = None,
        address: str | None = None,
        day_of_week: int | None = None,
        hour: int | None = None,
        latitude=None,
        longitude=None,
    ):
        artifact = self.model_manager.relocation_artifact
        if artifact is not None:
            return self._recommend_from_artifact(
                artifact=artifact,
                current_zone=current_zone,
                address=address,
                day_of_week=day_of_week,
                hour=hour,
                latitude=latitude,
                longitude=longitude,
            )

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

    def _recommend_from_artifact(
        self,
        artifact,
        current_zone: str | None = None,
        address: str | None = None,
        day_of_week: int | None = None,
        hour: int | None = None,
        latitude=None,
        longitude=None,
    ):
        day_of_week, hour = self.traffic_service.time_context(day_of_week, hour)
        day_name = DAY_NAMES[day_of_week]
        origin = self._resolve_artifact_origin(artifact, current_zone, address, latitude, longitude)
        origin_location_id = int(origin["LocationID"])
        current_env_data = artifact.travel_matrix[
            (artifact.travel_matrix["pickup_day_of_week"] == day_name)
            & (artifact.travel_matrix["pickup_hour"] == hour)
        ]
        origin_travel = current_env_data[current_env_data["PULocationID"] == origin_location_id]
        current_pay_data = artifact.pay_stats[
            (artifact.pay_stats["pickup_day_of_week"] == day_name)
            & (artifact.pay_stats["pickup_hour"] == hour)
        ]

        if current_pay_data.empty:
            raise ValueError(
                f"No historical relocation pay data exists in the saved model for {day_name} at {hour}:00."
            )
        if origin_travel.empty:
            raise ValueError(
                f"No historical relocation routes exist in the saved model from {origin['Zone']} for {day_name} at {hour}:00."
            )

        candidate_location_ids = self._candidate_destination_ids(
            artifact=artifact,
            current_pay_data=current_pay_data,
            origin_travel=origin_travel,
        )
        if not candidate_location_ids:
            raise ValueError(
                f"No exact relocation candidates exist in the saved model from {origin['Zone']} for {day_name} at {hour}:00."
            )

        t1_scores: dict[int, float] = {}
        travel_lookup: dict[int, float] = {}
        demand_lookup: dict[int, float] = {}
        pay_lookup: dict[int, float] = {}

        for destination_location_id in candidate_location_ids:
            predicted_pay_per_minute = self._predict_pay_per_minute(
                artifact=artifact,
                location_id=destination_location_id,
                day_of_week=day_of_week,
                hour=hour,
            )
            travel_minutes = self._lookup_exact_travel_minutes(
                origin_travel=origin_travel,
                destination_location_id=destination_location_id,
            )
            demand_index = self._lookup_exact_demand(
                current_pay_data=current_pay_data,
                location_id=destination_location_id,
            )

            pay_lookup[destination_location_id] = predicted_pay_per_minute
            travel_lookup[destination_location_id] = travel_minutes
            demand_lookup[destination_location_id] = demand_index
            t1_scores[destination_location_id] = (predicted_pay_per_minute * 30.0) - (travel_minutes * 0.5)

        t1_norm = self._normalize_scores(t1_scores)
        t2_best_zone = self._get_optimal_zone_jit(
            artifact=artifact,
            current_day=day_name,
            current_hour=hour,
            current_loc=origin_location_id,
            alpha=JIT_ALPHA,
            gamma=JIT_GAMMA,
            epsilon=JIT_EPSILON,
            epochs=JIT_EPOCHS,
        )
        t3_norm = self._bandit_scores(
            artifact=artifact,
            destination_ids=list(t1_scores.keys()),
        )

        ensemble_scores: dict[int, float] = {}
        for location_id in t1_scores:
            score_1 = t1_norm.get(location_id, 0.0)
            score_2 = 1.0 if location_id == t2_best_zone else 0.0
            score_3 = t3_norm.get(location_id, 0.0)
            ensemble_scores[location_id] = (W_T1 * score_1) + (W_T2 * score_2) + (W_T3 * score_3)

        ranked_pairs = sorted(ensemble_scores.items(), key=lambda item: item[1], reverse=True)
        top_n = min(3, len(ranked_pairs))
        top_pairs = ranked_pairs[:top_n]
        recommendation_id = top_pairs[0][0]

        candidates = []
        for location_id, score in ranked_pairs[:3]:
            zone_name = self._zone_name_from_location_id(artifact, location_id)
            predicted_hourly = pay_lookup[location_id] * 60.0
            candidates.append(
                {
                    "zone": zone_name,
                    "travel_minutes": round(float(travel_lookup[location_id]), 1),
                    "demand_index": round(float(demand_lookup[location_id]), 1),
                    "predicted_hourly_earnings": round(float(predicted_hourly), 2),
                    "net_score": round(float(score), 3),
                }
            )

        best = next(candidate for candidate in candidates if candidate["zone"] == self._zone_name_from_location_id(artifact, recommendation_id))
        top_score = top_pairs[0][1]
        second_best_score = top_pairs[1][1] if len(top_pairs) > 1 else top_pairs[0][1]
        advantage = round(float(top_score - second_best_score), 3)

        return {
            "current_zone": str(origin["Zone"]),
            "recommended_zone": best["zone"],
            "travel_minutes": best["travel_minutes"],
            "estimated_demand": best["demand_index"],
            "predicted_hourly_earnings": best["predicted_hourly_earnings"],
            "confidence_gap": advantage,
            "driver_message": (
                f"Head toward {best['zone']}. The ensemble of relocation models ranked this zone strongest for the current setup, "
                f"so we chose it as the best zone to reposition to right now."
            ),
            "top_alternatives": candidates,
        }

    def _artifact_candidates(self, artifact) -> Iterable:
        taxi_zones = artifact.taxi_zones.copy()
        taxi_zones = taxi_zones.dropna(subset=["LocationID", "Zone"])
        taxi_zones = taxi_zones[taxi_zones["service_zone"].astype(str).str.lower() != "nan"]
        return taxi_zones.to_dict("records")

    def _resolve_artifact_origin(self, artifact, current_zone, address, latitude, longitude):
        taxi_zones = artifact.taxi_zones.copy()
        taxi_zones["zone_key"] = taxi_zones["Zone"].astype(str).str.strip().str.lower()

        if current_zone:
            raw_value = current_zone.strip()
            if raw_value.isdigit():
                exact_match = taxi_zones[taxi_zones["LocationID"] == int(raw_value)]
                if not exact_match.empty:
                    return exact_match.iloc[0]
                raise ValueError("Unknown relocation zone ID. Choose a zone from the relocation list.")

            normalized = raw_value.lower()
            exact_match = taxi_zones[taxi_zones["zone_key"] == normalized]
            if not exact_match.empty:
                return exact_match.iloc[0]
            raise ValueError("Unknown relocation zone. Choose a zone from the relocation list.")

        if address:
            normalized_address = address.strip().lower()
            matches = taxi_zones[taxi_zones["zone_key"].apply(lambda value: value in normalized_address)]
            if not matches.empty:
                longest = matches.assign(name_length=matches["zone_key"].str.len()).sort_values("name_length", ascending=False)
                return longest.iloc[0]
            raise ValueError("Could not map that address to a TLC taxi zone yet. Try selecting a relocation zone directly.")

        if latitude is not None and longitude is not None:
            try:
                latitude = float(latitude)
                longitude = float(longitude)
            except (TypeError, ValueError) as exc:
                raise ValueError("Latitude and longitude must be valid numbers.") from exc

            taxi_zones = taxi_zones.dropna(subset=["LocationID", "Zone"])
            distance_series = taxi_zones.apply(
                lambda row: self.traffic_service._distance_miles(
                    latitude,
                    longitude,
                    self._zone_latitude(str(row["Zone"])),
                    self._zone_longitude(str(row["Zone"])),
                ),
                axis=1,
            )
            return taxi_zones.loc[distance_series.idxmin()]

        raise ValueError("Provide a relocation zone or an address.")

    def _lookup_exact_travel_minutes(self, origin_travel, destination_location_id: int) -> float:
        travel_row = origin_travel[origin_travel["DOLocationID"] == destination_location_id]
        if travel_row.empty:
            raise ValueError("Missing exact travel route in saved relocation model.")
        return float(travel_row["avg_travel_minutes"].iloc[0])

    def _lookup_exact_demand(self, current_pay_data, location_id: int) -> float:
        matched = current_pay_data[current_pay_data["PULocationID"] == location_id]
        if matched.empty:
            raise ValueError("Missing exact demand row in saved relocation model.")
        return float(matched["ride_demand"].mean())

    def _predict_pay_per_minute(self, artifact, location_id: int, day_of_week: int, hour: int) -> float:
        feature_row = {column: 0 for column in artifact.feature_cols}
        feature_row["PULocationID"] = location_id
        feature_row["pickup_hour"] = hour

        for column in artifact.feature_cols:
            if not column.startswith("pickup_day_of_week_"):
                continue
            day_name = column.removeprefix("pickup_day_of_week_")
            feature_row[column] = 1 if day_name == DAY_NAMES[day_of_week] else 0

        model_input = pd.DataFrame([[feature_row[column] for column in artifact.feature_cols]], columns=artifact.feature_cols)
        return float(artifact.rf_model.predict(model_input)[0])

    def _candidate_destination_ids(self, artifact, current_pay_data, origin_travel) -> list[int]:
        pay_ids = {int(value) for value in current_pay_data["PULocationID"].dropna().unique()}
        route_ids = {int(value) for value in origin_travel["DOLocationID"].dropna().unique()}
        bandit_ids = {int(location_id) for location_id in artifact.loc_to_idx.keys()}
        return sorted(pay_ids & route_ids & bandit_ids)

    def _normalize_scores(self, scores: dict[int, float]) -> dict[int, float]:
        if not scores:
            return {}
        min_score = min(scores.values())
        max_score = max(scores.values())
        return {
            key: (value - min_score) / (max_score - min_score + 1e-9)
            for key, value in scores.items()
        }

    def _get_optimal_zone_jit(self, artifact, current_day: str, current_hour: int, current_loc: int, alpha: float, gamma: float, epsilon: float, epochs: int):
        env_data = artifact.travel_matrix[
            (artifact.travel_matrix["pickup_day_of_week"] == current_day)
            & (artifact.travel_matrix["pickup_hour"] == current_hour)
        ]
        pay = artifact.pay_stats[
            (artifact.pay_stats["pickup_day_of_week"] == current_day)
            & (artifact.pay_stats["pickup_hour"] == current_hour)
        ]
        if env_data.empty or pay.empty:
            return None

        locs = list(set(env_data["PULocationID"]).union(set(env_data["DOLocationID"])))
        loc_to_idx = {loc: idx for idx, loc in enumerate(locs)}
        idx_to_loc = {idx: loc for idx, loc in enumerate(locs)}
        if current_loc not in loc_to_idx:
            return None

        q_table = np.zeros((len(locs), len(locs)))
        rng = np.random.default_rng(42)

        def get_reward(start: int, end: int) -> float:
            t_row = env_data[(env_data["PULocationID"] == start) & (env_data["DOLocationID"] == end)]
            if t_row.empty:
                return -1e9
            t_time = float(t_row["avg_travel_minutes"].iloc[0])
            p_row = pay[pay["PULocationID"] == end]
            if p_row.empty:
                return -1e9
            p_rate = float(p_row["avg_pay_per_minute"].iloc[0])
            return (p_rate * 30.0) - (t_time * 0.5)

        for _ in range(epochs):
            s_idx = int(rng.integers(0, len(locs)))
            s_loc = idx_to_loc[s_idx]
            if float(rng.random()) < epsilon:
                a_idx = int(rng.integers(0, len(locs)))
            else:
                a_idx = int(np.argmax(q_table[s_idx]))
            a_loc = idx_to_loc[a_idx]
            reward = get_reward(s_loc, a_loc)
            q_table[s_idx, a_idx] = (1 - alpha) * q_table[s_idx, a_idx] + alpha * (reward + gamma * np.max(q_table[a_idx]))

        current_idx = loc_to_idx[current_loc]
        best_action_idx = int(np.argmax(q_table[current_idx]))
        return int(idx_to_loc[best_action_idx])

    def _bandit_scores(self, artifact, destination_ids: list[int]) -> dict[int, float]:
        bandit = artifact.bandit
        if bandit is None:
            return {}
        raw_scores: dict[int, float] = {}
        for destination_id in destination_ids:
            if destination_id in artifact.loc_to_idx:
                idx = artifact.loc_to_idx[destination_id]
                exploration_term = float(bandit.c) * math.sqrt(math.log(float(bandit.total_steps) + 1.0) / (float(bandit.action_counts[idx]) + 1e-9))
                raw_scores[destination_id] = float(bandit.q_values[idx]) + exploration_term
        return self._normalize_scores(raw_scores)

    def _zone_name_from_location_id(self, artifact, location_id: int) -> str:
        matched = artifact.taxi_zones[artifact.taxi_zones["LocationID"] == location_id]
        if not matched.empty:
            return str(matched["Zone"].iloc[0])
        return str(location_id)

    def _shape_to_geojson_geometry(self, shape) -> dict | None:
        if not shape.points:
            return None

        parts = list(shape.parts) + [len(shape.points)]
        rings = []
        for index in range(len(parts) - 1):
            ring_points = shape.points[parts[index]:parts[index + 1]]
            ring = [[float(x), float(y)] for x, y in ring_points]
            if ring and ring[0] != ring[-1]:
                ring.append(ring[0])
            if len(ring) >= 4:
                rings.append(ring)

        if not rings:
            return None

        polygons: list[list[list[list[float]]]] = []
        current_polygon: list[list[list[float]]] = []
        for ring in rings:
            if self._signed_area(ring) < 0 or not current_polygon:
                if current_polygon:
                    polygons.append(current_polygon)
                current_polygon = [ring]
            else:
                current_polygon.append(ring)

        if current_polygon:
            polygons.append(current_polygon)

        if len(polygons) == 1:
            return {"type": "Polygon", "coordinates": polygons[0]}
        return {"type": "MultiPolygon", "coordinates": polygons}

    def _signed_area(self, ring: list[list[float]]) -> float:
        area = 0.0
        for index in range(len(ring) - 1):
            x1, y1 = ring[index]
            x2, y2 = ring[index + 1]
            area += (x1 * y2) - (x2 * y1)
        return area / 2.0

    def _zone_latitude(self, zone_name: str) -> float:
        fallback_zone = next((zone for zone in get_zones() if zone.name.lower() == zone_name.lower()), None)
        return fallback_zone.latitude if fallback_zone else 40.7580

    def _zone_longitude(self, zone_name: str) -> float:
        fallback_zone = next((zone for zone in get_zones() if zone.name.lower() == zone_name.lower()), None)
        return fallback_zone.longitude if fallback_zone else -73.9855

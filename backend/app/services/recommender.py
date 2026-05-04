from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from app.data.trip_dataset import get_zones


class ZoneRecommendationService:
    def __init__(self, model_manager, traffic_service):
        self.model_manager = model_manager
        self.traffic_service = traffic_service

    def available_relocation_zones(self) -> list[dict[str, int | str]]:
        zone_lookup = self._zone_lookup_table()
        if zone_lookup is None:
            return [{"id": index + 1, "name": zone.name} for index, zone in enumerate(get_zones())]

        zone_lookup = zone_lookup.dropna(subset=["LocationID", "Zone"])
        zone_lookup = zone_lookup.sort_values(["Zone", "LocationID"])
        return [
            {"id": int(row["LocationID"]), "name": str(row["Zone"])}
            for _, row in zone_lookup.iterrows()
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

        if self._zone_lookup_table() is not None:
            zone_name = self._lookup_zone_name(current_zone)
            if zone_name is not None:
                raise ValueError(
                    f"The step-3 relocation model is not loaded right now, so TLC taxi zone '{current_zone}' ({zone_name}) "
                    "cannot be scored yet. Reinstall backend requirements and restart the backend so the relocation model can load."
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
        origin = self._resolve_artifact_origin(artifact, current_zone, address, latitude, longitude)
        origin_location_id = int(origin["LocationID"])

        context_df = artifact.training_table[
            (artifact.training_table["PULocationID"] == origin_location_id)
            & (artifact.training_table["hour_bucket"] == hour)
            & (artifact.training_table["day_of_week_numeric"] == day_of_week)
        ].copy()
        if context_df.empty:
            raise ValueError(
                f"No exact relocation candidates exist in the saved step-3 model from {origin['Zone']} for day {day_of_week} at {hour}:00."
            )

        ranked_candidates = self._rank_artifact_candidates(
            artifact=artifact,
            context_df=context_df,
            origin_location_id=origin_location_id,
            day_of_week=day_of_week,
            hour=hour,
        )
        if ranked_candidates.empty:
            raise ValueError(
                f"No exact relocation candidates exist in the saved step-3 model from {origin['Zone']} for day {day_of_week} at {hour}:00."
            )

        best = ranked_candidates.iloc[0]
        second_best_score = float(ranked_candidates.iloc[1]["predicted_net_gain"]) if len(ranked_candidates) > 1 else float(best["predicted_net_gain"])
        confidence_gap = round(float(best["predicted_net_gain"]) - second_best_score, 3)

        candidates = []
        for _, row in ranked_candidates.head(3).iterrows():
            candidates.append(
                {
                    "zone": str(row["DO_Zone"]),
                    "travel_minutes": round(float(row["travel_minutes"]), 1),
                    "demand_index": round(float(row["demand_index"]), 1),
                    "predicted_hourly_earnings": round(float(row["potential_market_earnings"]), 2),
                    "net_score": round(float(row["predicted_net_gain"]), 3),
                    "explanation": self._candidate_explanation(artifact, row, is_recommended=False),
                }
            )

        return {
            "current_zone": str(origin["Zone"]),
            "recommended_zone": str(best["DO_Zone"]),
            "travel_minutes": round(float(best["travel_minutes"]), 1),
            "estimated_demand": round(float(best["demand_index"]), 1),
            "predicted_hourly_earnings": round(float(best["potential_market_earnings"]), 2),
            "confidence_gap": confidence_gap,
            "driver_message": self._candidate_explanation(artifact, best, is_recommended=True),
            "top_alternatives": candidates,
        }

    def _rank_artifact_candidates(
        self,
        artifact,
        context_df: pd.DataFrame,
        origin_location_id: int,
        day_of_week: int,
        hour: int,
    ) -> pd.DataFrame:
        unique_pairs = context_df[["PULocationID", "DOLocationID", "average_PU_to_DO_time"]].drop_duplicates()
        closest_candidates = unique_pairs.sort_values("average_PU_to_DO_time").head(9)

        candidate_rows: list[dict[str, float | int]] = []
        seen_destinations: set[int] = set()

        for _, row in closest_candidates.iterrows():
            destination_id = int(row["DOLocationID"])
            if destination_id in seen_destinations:
                continue
            candidate_rows.append(
                {
                    "PULocationID": origin_location_id,
                    "DOLocationID": destination_id,
                    "hour_bucket": hour,
                    "day_of_week_numeric": day_of_week,
                    "average_PU_to_DO_time": float(row["average_PU_to_DO_time"]),
                }
            )
            seen_destinations.add(destination_id)

        if origin_location_id not in seen_destinations:
            candidate_rows.append(
                {
                    "PULocationID": origin_location_id,
                    "DOLocationID": origin_location_id,
                    "hour_bucket": hour,
                    "day_of_week_numeric": day_of_week,
                    "average_PU_to_DO_time": 0.0,
                }
            )

        if not candidate_rows:
            return pd.DataFrame()

        candidates_df = pd.DataFrame(candidate_rows)
        candidates_df["predicted_net_gain"] = artifact.model.predict(candidates_df[artifact.feature_cols])

        destination_stats = artifact.training_table[
            (artifact.training_table["hour_bucket"] == hour)
            & (artifact.training_table["day_of_week_numeric"] == day_of_week)
        ].groupby("DOLocationID").agg(
            avg_hourly_earnings=("DO_avg_market_total_earnings_per_hour", "mean"),
            demand_index=("DO_trip_density_per_hour", "mean"),
        ).reset_index()

        zone_names = artifact.zone_lookup[["LocationID", "Zone"]].drop_duplicates()

        ranked = candidates_df.merge(
            destination_stats,
            on="DOLocationID",
            how="left",
        ).merge(
            zone_names,
            left_on="DOLocationID",
            right_on="LocationID",
            how="left",
        )

        ranked["travel_minutes"] = ranked["average_PU_to_DO_time"] / 60.0
        ranked["potential_market_earnings"] = ranked["avg_hourly_earnings"] * (
            1.0 - (ranked["average_PU_to_DO_time"] / 3600.0)
        )
        ranked["potential_market_earnings"] = ranked["potential_market_earnings"].fillna(0.0).clip(lower=0.0)
        ranked["demand_index"] = ranked["demand_index"].fillna(0.0)
        ranked["DO_Zone"] = ranked["Zone"].fillna(ranked["DOLocationID"].astype(str))

        return ranked.sort_values("predicted_net_gain", ascending=False).reset_index(drop=True)

    def _candidate_explanation(self, artifact, row: pd.Series, is_recommended: bool) -> str:
        zone_name = str(row["DO_Zone"])
        net_gain = float(row["predicted_net_gain"])
        travel_minutes = float(row["travel_minutes"])
        earnings = float(row["potential_market_earnings"])
        direction_phrase = "increases" if net_gain >= 0 else "decreases"
        change_amount = abs(net_gain)
        change_noun = "increase" if net_gain >= 0 else "change"
        option_phrase = "a strong relocation option" if net_gain >= 0 else "the next best option"

        return (
            f"{zone_name} is {option_phrase}. It requires about {travel_minutes:.1f} minutes of travel time, "
            f"and moving there {direction_phrase} your exposure to available ride earnings by ${change_amount:.2f} per hour compared "
            f"to staying in your current zone.\n"
            f"This {change_noun} reflects overall market activity across all drivers, not individual driver earnings.\n"
            f"After accounting for the {travel_minutes:.1f} minutes spent relocating, you would have the remaining portion "
            f"of the hour to benefit from that higher-demand area. This results in an adjusted earning exposure of "
            f"approximately ${earnings:.2f} for the rest of the hour, reflecting the reduced time available after travel."
        )

    def _artifact_candidates(self, artifact) -> Iterable:
        zone_lookup = artifact.zone_lookup.copy()
        zone_lookup = zone_lookup.dropna(subset=["LocationID", "Zone"])
        return zone_lookup.to_dict("records")

    def _zone_lookup_table(self) -> pd.DataFrame | None:
        if self.model_manager.taxi_zone_lookup is not None:
            return self.model_manager.taxi_zone_lookup.copy()
        artifact = self.model_manager.relocation_artifact
        if artifact is not None:
            return artifact.zone_lookup.copy()
        return None

    def _resolve_artifact_origin(self, artifact, current_zone, address, latitude, longitude):
        zone_lookup = artifact.zone_lookup.copy()
        zone_lookup["zone_key"] = zone_lookup["Zone"].astype(str).str.strip().str.lower()

        if current_zone:
            raw_value = current_zone.strip()
            if raw_value.isdigit():
                exact_match = zone_lookup[zone_lookup["LocationID"] == int(raw_value)]
                if not exact_match.empty:
                    return exact_match.iloc[0]
                raise ValueError("Unknown relocation zone ID. Choose a zone from the relocation list.")

            normalized = raw_value.lower()
            exact_match = zone_lookup[zone_lookup["zone_key"] == normalized]
            if not exact_match.empty:
                return exact_match.iloc[0]
            raise ValueError("Unknown relocation zone. Choose a zone from the relocation list.")

        if address:
            normalized_address = address.strip().lower()
            matches = zone_lookup[zone_lookup["zone_key"].apply(lambda value: value in normalized_address)]
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

            zone_lookup = zone_lookup.dropna(subset=["LocationID", "Zone"])
            distance_series = zone_lookup.apply(
                lambda row: self.traffic_service._distance_miles(
                    latitude,
                    longitude,
                    self._zone_latitude(str(row["Zone"])),
                    self._zone_longitude(str(row["Zone"])),
                ),
                axis=1,
            )
            return zone_lookup.loc[distance_series.idxmin()]

        raise ValueError("Provide a relocation zone or an address.")

    def _lookup_zone_name(self, current_zone: str | None) -> str | None:
        if not current_zone:
            return None

        zone_lookup = self._zone_lookup_table()
        if zone_lookup is None:
            return None

        zone_lookup = zone_lookup.copy()
        zone_lookup["zone_key"] = zone_lookup["Zone"].astype(str).str.strip().str.lower()
        raw_value = current_zone.strip()

        if raw_value.isdigit():
            matched = zone_lookup[zone_lookup["LocationID"] == int(raw_value)]
            if not matched.empty:
                return str(matched.iloc[0]["Zone"])
            return None

        matched = zone_lookup[zone_lookup["zone_key"] == raw_value.lower()]
        if not matched.empty:
            return str(matched.iloc[0]["Zone"])
        return None

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

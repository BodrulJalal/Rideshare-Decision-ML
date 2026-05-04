from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import sys

import joblib
import pandas as pd

from app.ml.training import train_zone_model


logger = logging.getLogger(__name__)


class RelocationRecommender:
    """Compatibility shim for deserializing the saved relocation recommender artifact."""


@dataclass
class RelocationArtifact:
    model: object
    training_table: pd.DataFrame
    zone_lookup: pd.DataFrame
    feature_cols: list[str]
    feature_importance_map: dict[str, float]
    sorted_important_features: list[str]


@dataclass
class ModelBundle:
    zone_model: object
    taxi_zone_lookup: pd.DataFrame | None
    relocation_artifact: RelocationArtifact | None


class ModelManager:
    def __init__(self):
        self.bundle = ModelBundle(
            zone_model=train_zone_model(),
            taxi_zone_lookup=self._load_taxi_zone_lookup(),
            relocation_artifact=self._load_relocation_artifact(),
        )

    def _load_taxi_zone_lookup(self) -> pd.DataFrame | None:
        repo_root = Path(__file__).resolve().parents[3]
        candidate_paths = (
            repo_root / "Model Building" / "Capstone Files" / "Step 3" / "taxi_zone_lookup.csv",
        )

        for path in candidate_paths:
            if not path.exists():
                continue
            try:
                zone_lookup = pd.read_csv(path)
            except ValueError as exc:
                logger.warning("Taxi zone lookup could not be loaded from %s: %s", path, exc)
                continue
            if {"LocationID", "Zone"}.issubset(zone_lookup.columns):
                return zone_lookup

        return None

    def _load_relocation_artifact(self) -> RelocationArtifact | None:
        repo_root = Path(__file__).resolve().parents[3]
        artifact_dir = repo_root / "Model Building" / "Capstone Files" / "Step 3"
        artifact_path = artifact_dir / "relocation_model_with_recommender.pkl"
        training_path = artifact_dir / "uber_trips_training.parquet"

        required_paths = (artifact_path, training_path)
        if not all(path.exists() for path in required_paths):
            return None

        try:
            setattr(sys.modules["__main__"], "RelocationRecommender", RelocationRecommender)
            loaded_recommender = joblib.load(artifact_path)
            training_table = pd.read_parquet(training_path)
        except (AttributeError, ImportError, ModuleNotFoundError, ValueError) as exc:
            logger.warning("Relocation artifact could not be loaded; falling back to non-artifact path: %s", exc)
            return None

        zone_lookup = self.bundle.taxi_zone_lookup if hasattr(self, "bundle") else self._load_taxi_zone_lookup()
        if zone_lookup is None:
            return None

        feature_cols = list(getattr(loaded_recommender, "features", []))
        loaded_model = getattr(loaded_recommender, "model", None)
        zone_lookup_from_artifact = getattr(loaded_recommender, "zone_lookup_df", None)
        feature_importance_map = dict(getattr(loaded_recommender, "feature_importance_map", {}))
        sorted_important_features = list(getattr(loaded_recommender, "sorted_important_features", feature_cols))

        if zone_lookup_from_artifact is not None and {"LocationID", "Zone"}.issubset(zone_lookup_from_artifact.columns):
            zone_lookup = zone_lookup_from_artifact

        if loaded_model is None:
            return None
        if not set(feature_cols).issubset(training_table.columns):
            return None
        if not {"LocationID", "Zone"}.issubset(zone_lookup.columns):
            return None

        return RelocationArtifact(
            model=loaded_model,
            training_table=training_table,
            zone_lookup=zone_lookup,
            feature_cols=feature_cols,
            feature_importance_map=feature_importance_map,
            sorted_important_features=sorted_important_features,
        )

    @property
    def zone_model(self):
        return self.bundle.zone_model

    @property
    def taxi_zone_lookup(self) -> pd.DataFrame | None:
        return self.bundle.taxi_zone_lookup

    @property
    def relocation_artifact(self) -> RelocationArtifact | None:
        return self.bundle.relocation_artifact

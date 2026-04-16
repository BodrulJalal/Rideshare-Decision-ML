from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import joblib

from app.ml.training import train_trip_model, train_zone_model


class TunableUCBBandit:
    """Compatibility shim for deserializing the saved relocation artifact."""


@dataclass
class RelocationArtifact:
    rf_model: object
    bandit: object
    travel_matrix: object
    pay_stats: object
    taxi_zones: object
    feature_cols: list[str]
    loc_to_idx: dict
    idx_to_loc: dict


@dataclass
class ModelBundle:
    zone_model: object
    trip_model: object
    relocation_artifact: RelocationArtifact | None


class ModelManager:
    def __init__(self):
        self.bundle = ModelBundle(
            zone_model=train_zone_model(),
            trip_model=train_trip_model(),
            relocation_artifact=self._load_relocation_artifact(),
        )

    def _load_relocation_artifact(self) -> RelocationArtifact | None:
        artifact_path = Path(__file__).resolve().parents[2] / "uber_relocation_ensemble_model_finalv1.joblib"
        if not artifact_path.exists():
            return None

        setattr(sys.modules["__main__"], "TunableUCBBandit", TunableUCBBandit)
        loaded = joblib.load(artifact_path)
        if not isinstance(loaded, dict):
            return None

        required_keys = {
            "rf_model",
            "bandit",
            "travel_matrix",
            "pay_stats",
            "taxi_zones",
            "feature_cols",
            "loc_to_idx",
            "idx_to_loc",
        }
        if not required_keys.issubset(loaded):
            return None

        return RelocationArtifact(
            rf_model=loaded["rf_model"],
            bandit=loaded["bandit"],
            travel_matrix=loaded["travel_matrix"],
            pay_stats=loaded["pay_stats"],
            taxi_zones=loaded["taxi_zones"],
            feature_cols=list(loaded["feature_cols"]),
            loc_to_idx=dict(loaded["loc_to_idx"]),
            idx_to_loc=dict(loaded["idx_to_loc"]),
        )

    @property
    def zone_model(self):
        return self.bundle.zone_model

    @property
    def trip_model(self):
        return self.bundle.trip_model

    @property
    def relocation_artifact(self) -> RelocationArtifact | None:
        return self.bundle.relocation_artifact

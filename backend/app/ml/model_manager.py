from __future__ import annotations

from dataclasses import dataclass

from app.ml.training import train_trip_model, train_zone_model


@dataclass
class ModelBundle:
    zone_model: object
    trip_model: object


class ModelManager:
    def __init__(self):
        self.bundle = ModelBundle(
            zone_model=train_zone_model(),
            trip_model=train_trip_model(),
        )

    @property
    def zone_model(self):
        return self.bundle.zone_model

    @property
    def trip_model(self):
        return self.bundle.trip_model

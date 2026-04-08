from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.data.sample_data import build_trip_offer_dataset, build_zone_recommendation_dataset


def train_zone_model():
    records, targets = build_zone_recommendation_dataset()
    feature_rows = [
        [record["zone"], record["hour"], record["demand_index"], record["travel_minutes"]]
        for record in records
    ]

    preprocessor = ColumnTransformer(
        transformers=[("zone", OneHotEncoder(handle_unknown="ignore"), [0])],
        remainder="passthrough",
    )
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", RandomForestRegressor(n_estimators=220, random_state=42)),
        ]
    )
    model.fit(feature_rows, targets)
    return model


def train_trip_model():
    records, labels = build_trip_offer_dataset()
    feature_rows = [
        [record["pickup_zone"], record["trip_minutes"], record["rider_rating"]]
        for record in records
    ]

    preprocessor = ColumnTransformer(
        transformers=[("pickup_zone", OneHotEncoder(handle_unknown="ignore"), [0])],
        remainder="passthrough",
    )
    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", RandomForestClassifier(n_estimators=240, random_state=42)),
        ]
    )
    model.fit(feature_rows, labels)
    return model

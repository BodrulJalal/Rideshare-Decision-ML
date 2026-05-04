CREATE TABLE IF NOT EXISTS dim_zone (
    zone_id BIGSERIAL PRIMARY KEY,
    tlc_location_id INTEGER UNIQUE,
    zone_name TEXT NOT NULL,
    borough TEXT,
    service_zone TEXT,
    centroid_lat NUMERIC(9, 6),
    centroid_lng NUMERIC(9, 6)
);

CREATE TABLE IF NOT EXISTS fact_trip_offer (
    trip_offer_id BIGSERIAL PRIMARY KEY,
    trip_date DATE NOT NULL,
    day_of_week_num SMALLINT NOT NULL,
    pickup_hour SMALLINT NOT NULL,
    trip_minutes NUMERIC(10, 2) NOT NULL,
    trip_miles NUMERIC(10, 2),
    driver_pay NUMERIC(10, 2),
    tip_amount NUMERIC(10, 2),
    surge_amount NUMERIC(10, 2),
    pickup_wait_min NUMERIC(10, 2),
    pickup_zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    dropoff_zone_id BIGINT REFERENCES dim_zone(zone_id),
    source_system TEXT,
    source_file TEXT
);

CREATE TABLE IF NOT EXISTS agg_zone_hourly_metrics (
    zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    pickup_day_of_week TEXT NOT NULL,
    pickup_hour SMALLINT NOT NULL,
    avg_pay_per_minute NUMERIC(10, 4),
    ride_demand INTEGER,
    avg_trip_miles NUMERIC(10, 2),
    PRIMARY KEY (zone_id, pickup_day_of_week, pickup_hour)
);

CREATE TABLE IF NOT EXISTS agg_route_hourly_metrics (
    origin_zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    destination_zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    pickup_day_of_week TEXT NOT NULL,
    pickup_hour SMALLINT NOT NULL,
    avg_travel_minutes NUMERIC(10, 2),
    avg_trip_miles NUMERIC(10, 2),
    trip_count INTEGER,
    PRIMARY KEY (origin_zone_id, destination_zone_id, pickup_day_of_week, pickup_hour)
);

CREATE TABLE IF NOT EXISTS ml_model_registry (
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    training_source TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    PRIMARY KEY (model_name, model_version)
);

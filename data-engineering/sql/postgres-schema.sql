CREATE TABLE IF NOT EXISTS dim_zone (
    zone_id BIGSERIAL PRIMARY KEY,
    tlc_location_id INTEGER NOT NULL UNIQUE,
    zone_name TEXT NOT NULL,
    borough TEXT,
    service_zone TEXT,
    centroid_lat NUMERIC(9, 6),
    centroid_lng NUMERIC(9, 6)
);

CREATE TABLE IF NOT EXISTS dim_source_file (
    source_file_id BIGSERIAL PRIMARY KEY,
    file_name TEXT NOT NULL,
    source_stage TEXT NOT NULL,
    source_month TEXT,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (file_name, source_stage)
);

CREATE TABLE IF NOT EXISTS fact_uber_trip_clean (
    trip_id BIGSERIAL PRIMARY KEY,
    pickup_datetime TIMESTAMP NOT NULL,
    dropoff_datetime TIMESTAMP NOT NULL,
    pickup_zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    dropoff_zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    trip_minutes NUMERIC(10, 2) NOT NULL,
    trip_miles NUMERIC(10, 2),
    driver_pay NUMERIC(10, 2),
    base_passenger_fare NUMERIC(10, 2),
    tips NUMERIC(10, 2),
    hvfhs_license_num TEXT,
    dispatching_base_num TEXT,
    source_file_id BIGINT REFERENCES dim_source_file(source_file_id),
    CHECK (dropoff_datetime >= pickup_datetime),
    CHECK (trip_minutes >= 0),
    CHECK (trip_miles IS NULL OR trip_miles >= 0)
);

CREATE TABLE IF NOT EXISTS fact_uber_trip_processed (
    trip_id BIGSERIAL PRIMARY KEY,
    pickup_datetime TIMESTAMP NOT NULL,
    dropoff_datetime TIMESTAMP NOT NULL,
    pickup_zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    dropoff_zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    day_of_week_numeric SMALLINT NOT NULL CHECK (day_of_week_numeric BETWEEN 0 AND 6),
    hour_bucket SMALLINT NOT NULL CHECK (hour_bucket BETWEEN 0 AND 23),
    trip_minutes NUMERIC(10, 2) NOT NULL CHECK (trip_minutes >= 0),
    trip_miles NUMERIC(10, 2) CHECK (trip_miles IS NULL OR trip_miles >= 0),
    driver_pay NUMERIC(10, 2),
    source_file_id BIGINT REFERENCES dim_source_file(source_file_id),
    split_group TEXT CHECK (split_group IS NULL OR split_group IN ('train', 'test', 'validation'))
);

CREATE TABLE IF NOT EXISTS agg_zone_hourly_earnings (
    zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    day_of_week_numeric SMALLINT NOT NULL CHECK (day_of_week_numeric BETWEEN 0 AND 6),
    hour_bucket SMALLINT NOT NULL CHECK (hour_bucket BETWEEN 0 AND 23),
    avg_driver_pay NUMERIC(10, 2),
    avg_trip_minutes NUMERIC(10, 2),
    avg_pay_per_minute NUMERIC(10, 4),
    trip_count INTEGER NOT NULL DEFAULT 0 CHECK (trip_count >= 0),
    PRIMARY KEY (zone_id, day_of_week_numeric, hour_bucket)
);

CREATE TABLE IF NOT EXISTS agg_route_hourly_travel (
    origin_zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    destination_zone_id BIGINT NOT NULL REFERENCES dim_zone(zone_id),
    day_of_week_numeric SMALLINT NOT NULL CHECK (day_of_week_numeric BETWEEN 0 AND 6),
    hour_bucket SMALLINT NOT NULL CHECK (hour_bucket BETWEEN 0 AND 23),
    average_pu_to_do_time NUMERIC(10, 2),
    avg_trip_miles NUMERIC(10, 2),
    trip_count INTEGER NOT NULL DEFAULT 0 CHECK (trip_count >= 0),
    PRIMARY KEY (origin_zone_id, destination_zone_id, day_of_week_numeric, hour_bucket)
);

CREATE TABLE IF NOT EXISTS ml_relocation_training_set (
    training_row_id BIGSERIAL PRIMARY KEY,
    pickup_location_id INTEGER NOT NULL,
    dropoff_location_id INTEGER NOT NULL,
    hour_bucket SMALLINT NOT NULL CHECK (hour_bucket BETWEEN 0 AND 23),
    day_of_week_numeric SMALLINT NOT NULL CHECK (day_of_week_numeric BETWEEN 0 AND 6),
    average_pu_to_do_time NUMERIC(10, 2) NOT NULL,
    net_gain NUMERIC(12, 4),
    feature_version TEXT NOT NULL DEFAULT 'step_3',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml_relocation_test_set (
    test_row_id BIGSERIAL PRIMARY KEY,
    pickup_location_id INTEGER NOT NULL,
    dropoff_location_id INTEGER NOT NULL,
    hour_bucket SMALLINT NOT NULL CHECK (hour_bucket BETWEEN 0 AND 23),
    day_of_week_numeric SMALLINT NOT NULL CHECK (day_of_week_numeric BETWEEN 0 AND 6),
    average_pu_to_do_time NUMERIC(10, 2) NOT NULL,
    net_gain NUMERIC(12, 4),
    feature_version TEXT NOT NULL DEFAULT 'step_3',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml_model_registry (
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    artifact_path TEXT NOT NULL,
    training_table TEXT,
    test_table TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    PRIMARY KEY (model_name, model_version)
);

CREATE INDEX IF NOT EXISTS idx_fact_clean_pickup_time
    ON fact_uber_trip_clean (pickup_zone_id, pickup_datetime);

CREATE INDEX IF NOT EXISTS idx_fact_clean_dropoff_zone
    ON fact_uber_trip_clean (dropoff_zone_id);

CREATE INDEX IF NOT EXISTS idx_fact_processed_zone_hour
    ON fact_uber_trip_processed (pickup_zone_id, day_of_week_numeric, hour_bucket);

CREATE INDEX IF NOT EXISTS idx_fact_processed_route_hour
    ON fact_uber_trip_processed (pickup_zone_id, dropoff_zone_id, day_of_week_numeric, hour_bucket);

CREATE INDEX IF NOT EXISTS idx_training_features
    ON ml_relocation_training_set (pickup_location_id, day_of_week_numeric, hour_bucket);

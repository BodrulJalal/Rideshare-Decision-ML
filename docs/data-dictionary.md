# Data Dictionary

This document explains the target PostgreSQL/RDS schema for Driver Earnings Navigator. The current app reads local CSV, Parquet, shapefile, and model artifacts, while this schema describes how the same workflow can be moved into a production database design.

The schema mirrors the notebook pipeline:

- Step 1: raw TLC/HVFHV ingestion and Uber-only cleaning.
- Step 2: processed trip records and reusable aggregates.
- Step 3: relocation feature tables, model training, and artifact registration.

## Entity Overview

| Entity | Purpose |
|---|---|
| `dim_zone` | Stores TLC taxi-zone lookup information used by trips, aggregates, and map/recommendation logic. |
| `dim_source_file` | Tracks source files and notebook-era exports for lineage and replay. |
| `fact_uber_trip_clean` | Stores cleaned Uber trip records after filtering and zone enrichment. |
| `fact_uber_trip_processed` | Stores standardized trip records with model-ready time and split fields. |
| `agg_zone_hourly_earnings` | Stores zone/day/hour earning opportunity metrics. |
| `agg_route_hourly_travel` | Stores origin/destination/day/hour travel-time metrics. |
| `ml_relocation_training_set` | Stores final relocation-model training rows. |
| `ml_relocation_test_set` | Stores final relocation-model test rows. |
| `ml_model_registry` | Tracks trained model artifacts, versions, and deployment notes. |

## Relationship Summary

- `dim_zone` connects to trip facts through pickup and dropoff zone foreign keys.
- `dim_source_file` connects source files to cleaned and processed trip records.
- `agg_zone_hourly_earnings` summarizes opportunity by zone, day, and hour.
- `agg_route_hourly_travel` summarizes travel time between zone pairs by day and hour.
- `ml_relocation_training_set` and `ml_relocation_test_set` preserve the final Step 3 model features.
- `ml_model_registry` records which artifact was trained from which feature tables.

## How The Current Model Maps To This Schema

The current working app does not query PostgreSQL directly. It loads:

- `relocation_model_with_recommender.pkl`
- `uber_trips_training.parquet`
- `taxi_zone_lookup.csv`

The important idea is that the production schema is a scalable replacement for the notebook-created Parquet files and saved model artifacts. The model already works because the notebooks created a final training table. In production, the database pipeline would create and refresh those same kinds of tables automatically.

The current Step 3 training table has 3,185,960 rows and these columns:

| Current Step 3 Column | Meaning | Production Schema Mapping |
|---|---|---|
| `PULocationID` | Current/origin pickup zone used by the model. | `pickup_location_id` in `ml_relocation_training_set`; also maps back to `dim_zone.tlc_location_id`. |
| `DOLocationID` | Candidate destination/dropoff zone used by the model. | `dropoff_location_id` in `ml_relocation_training_set`; also maps back to `dim_zone.tlc_location_id`. |
| `hour_bucket` | Hour-of-day feature. | `hour_bucket` in processed facts, aggregates, and ML feature tables. |
| `day_of_week_numeric` | Day-of-week feature. | `day_of_week_numeric` in processed facts, aggregates, and ML feature tables. |
| `average_PU_to_DO_time` | Average travel time between pickup and dropoff zones. | `average_pu_to_do_time` in `agg_route_hourly_travel` and ML feature tables. |
| `PU_avg_market_total_earnings_per_hour` | Historical earning opportunity for the pickup zone/time. | Derived from `agg_zone_hourly_earnings` for the pickup zone. |
| `DO_avg_market_total_earnings_per_hour` | Historical earning opportunity for the candidate destination zone/time. | Derived from `agg_zone_hourly_earnings` for the destination zone. |
| `PU_trip_density_per_hour` | Historical trip density for the pickup zone/time. | Derived from zone/hour aggregate trip counts. |
| `DO_trip_density_per_hour` | Historical trip density for the destination zone/time. | Derived from zone/hour aggregate trip counts. |
| `PU_zone_opportunity_score` | Engineered opportunity score for the pickup zone. | Derived feature built from zone/hour aggregates. |
| `DO_zone_opportunity_score` | Engineered opportunity score for the destination zone. | Derived feature built from zone/hour aggregates. |
| `travel_penalty` | Cost or penalty of relocating between zones. | Derived from route/hour travel metrics. |
| `net_gain` | Target value representing the estimated benefit of relocating. | Stored in `ml_relocation_training_set` and `ml_relocation_test_set`. |

The saved LightGBM relocation model currently uses these five direct model input features:

- `PULocationID`
- `DOLocationID`
- `hour_bucket`
- `day_of_week_numeric`
- `average_PU_to_DO_time`

The other Step 3 columns still matter because they help create the training target, compare destination zones, and explain the result. For example, the backend uses destination hourly earnings and destination trip density to display adjusted earning exposure and demand context after the model ranks candidates.

In simpler terms:

1. Raw Uber trips become cleaned trip facts.
2. Cleaned trips become processed facts with day/hour/zone fields.
3. Processed facts become zone-hour and route-hour aggregates.
4. Aggregates become the Step 3 ML training and test tables.
5. The model is trained from those ML tables and registered in `ml_model_registry`.
6. The app loads the approved model version and uses the feature tables or exported artifacts to score relocation candidates.

## `dim_zone`

| Column | Type | Description | Constraint |
|---|---|---|---|
| `zone_id` | `BIGSERIAL` | Internal database key for a zone. | Primary key |
| `tlc_location_id` | `INTEGER` | Official TLC LocationID. | Not null, unique |
| `zone_name` | `TEXT` | TLC zone name. | Not null |
| `borough` | `TEXT` | NYC borough for the zone. | Nullable |
| `service_zone` | `TEXT` | TLC service-zone classification. | Nullable |
| `centroid_lat` | `NUMERIC(9, 6)` | Approximate zone centroid latitude. | Nullable |
| `centroid_lng` | `NUMERIC(9, 6)` | Approximate zone centroid longitude. | Nullable |

## `dim_source_file`

| Column | Type | Description | Constraint |
|---|---|---|---|
| `source_file_id` | `BIGSERIAL` | Internal source-file key. | Primary key |
| `file_name` | `TEXT` | Source file or export name. | Not null |
| `source_stage` | `TEXT` | Pipeline stage, such as raw, clean, processed, training, or test. | Not null |
| `source_month` | `TEXT` | Month represented by the source file when applicable. | Nullable |
| `loaded_at` | `TIMESTAMP` | Time the source was registered. | Defaults to current timestamp |

Unique constraint: `file_name`, `source_stage`.

## `fact_uber_trip_clean`

This table represents the Step 1 output: Uber-only trip records after raw HVFHV ingestion, filtering, and taxi-zone enrichment.

| Column | Type | Description | Constraint |
|---|---|---|---|
| `trip_id` | `BIGSERIAL` | Internal cleaned-trip key. | Primary key |
| `pickup_datetime` | `TIMESTAMP` | Pickup timestamp. | Not null |
| `dropoff_datetime` | `TIMESTAMP` | Dropoff timestamp. | Not null; must be after pickup |
| `pickup_zone_id` | `BIGINT` | Pickup zone. | References `dim_zone(zone_id)` |
| `dropoff_zone_id` | `BIGINT` | Dropoff zone. | References `dim_zone(zone_id)` |
| `trip_minutes` | `NUMERIC(10, 2)` | Trip duration in minutes. | Not null, non-negative |
| `trip_miles` | `NUMERIC(10, 2)` | Trip distance in miles. | Nullable, non-negative |
| `driver_pay` | `NUMERIC(10, 2)` | Driver pay for the trip. | Nullable |
| `base_passenger_fare` | `NUMERIC(10, 2)` | Base passenger fare if available. | Nullable |
| `tips` | `NUMERIC(10, 2)` | Tip amount. | Nullable |
| `hvfhs_license_num` | `TEXT` | HVFHV provider license number. | Nullable |
| `dispatching_base_num` | `TEXT` | Dispatching base number. | Nullable |
| `source_file_id` | `BIGINT` | Source lineage key. | References `dim_source_file(source_file_id)` |

## `fact_uber_trip_processed`

This table represents the Step 2 output: standardized trip records used to build reusable aggregates and model features.

| Column | Type | Description | Constraint |
|---|---|---|---|
| `trip_id` | `BIGSERIAL` | Internal processed-trip key. | Primary key |
| `pickup_datetime` | `TIMESTAMP` | Pickup timestamp. | Not null |
| `dropoff_datetime` | `TIMESTAMP` | Dropoff timestamp. | Not null |
| `pickup_zone_id` | `BIGINT` | Pickup zone. | References `dim_zone(zone_id)` |
| `dropoff_zone_id` | `BIGINT` | Dropoff zone. | References `dim_zone(zone_id)` |
| `day_of_week_numeric` | `SMALLINT` | Numeric day of week used by the model. | 0-6 |
| `hour_bucket` | `SMALLINT` | Hour of day used by the model. | 0-23 |
| `trip_minutes` | `NUMERIC(10, 2)` | Trip duration in minutes. | Non-negative |
| `trip_miles` | `NUMERIC(10, 2)` | Trip distance in miles. | Nullable, non-negative |
| `driver_pay` | `NUMERIC(10, 2)` | Driver pay for the trip. | Nullable |
| `source_file_id` | `BIGINT` | Source lineage key. | References `dim_source_file(source_file_id)` |
| `split_group` | `TEXT` | Optional deterministic split label. | `train`, `test`, `validation`, or null |

## `agg_zone_hourly_earnings`

This aggregate supports fast recommendation lookups by avoiding repeated recalculation of zone-level earnings patterns.

| Column | Type | Description | Constraint |
|---|---|---|---|
| `zone_id` | `BIGINT` | Zone being summarized. | References `dim_zone(zone_id)` |
| `day_of_week_numeric` | `SMALLINT` | Numeric day of week. | Primary key component, 0-6 |
| `hour_bucket` | `SMALLINT` | Hour of day. | Primary key component, 0-23 |
| `avg_driver_pay` | `NUMERIC(10, 2)` | Average driver pay for trips in that zone/time. | Nullable |
| `avg_trip_minutes` | `NUMERIC(10, 2)` | Average trip length in minutes. | Nullable |
| `avg_pay_per_minute` | `NUMERIC(10, 4)` | Average pay per minute. | Nullable |
| `trip_count` | `INTEGER` | Number of trips used in the aggregate. | Non-negative |

Primary key: `zone_id`, `day_of_week_numeric`, `hour_bucket`.

## `agg_route_hourly_travel`

This aggregate supports relocation scoring by estimating travel behavior between pickup and destination zones.

| Column | Type | Description | Constraint |
|---|---|---|---|
| `origin_zone_id` | `BIGINT` | Origin/pickup zone. | References `dim_zone(zone_id)` |
| `destination_zone_id` | `BIGINT` | Destination/dropoff zone. | References `dim_zone(zone_id)` |
| `day_of_week_numeric` | `SMALLINT` | Numeric day of week. | Primary key component, 0-6 |
| `hour_bucket` | `SMALLINT` | Hour of day. | Primary key component, 0-23 |
| `average_pu_to_do_time` | `NUMERIC(10, 2)` | Average pickup-to-dropoff time in seconds or model-standardized units. | Nullable |
| `avg_trip_miles` | `NUMERIC(10, 2)` | Average route distance. | Nullable |
| `trip_count` | `INTEGER` | Number of trips used in the aggregate. | Non-negative |

Primary key: `origin_zone_id`, `destination_zone_id`, `day_of_week_numeric`, `hour_bucket`.

## ML Feature Tables

`ml_relocation_training_set` and `ml_relocation_test_set` store the final Step 3 feature rows used by the relocation model.

| Column | Type | Description | Constraint |
|---|---|---|---|
| `training_row_id` / `test_row_id` | `BIGSERIAL` | Internal row key. | Primary key |
| `pickup_location_id` | `INTEGER` | TLC pickup LocationID, equivalent to `PULocationID` in the notebook. | Not null |
| `dropoff_location_id` | `INTEGER` | TLC dropoff LocationID, equivalent to `DOLocationID` in the notebook. | Not null |
| `hour_bucket` | `SMALLINT` | Hour feature. | 0-23 |
| `day_of_week_numeric` | `SMALLINT` | Day feature. | 0-6 |
| `average_pu_to_do_time` | `NUMERIC(10, 2)` | Travel-time feature used by the model. | Not null |
| `net_gain` | `NUMERIC(12, 4)` | Target or evaluation value for relocation gain. | Nullable |
| `feature_version` | `TEXT` | Feature pipeline version label. | Defaults to `step_3` |
| `created_at` | `TIMESTAMP` | Row creation timestamp. | Defaults to current timestamp |

## `ml_model_registry`

| Column | Type | Description | Constraint |
|---|---|---|---|
| `model_name` | `TEXT` | Name of the model. | Primary key component |
| `model_version` | `TEXT` | Version identifier. | Primary key component |
| `artifact_path` | `TEXT` | Storage path for the trained model artifact. | Not null |
| `training_table` | `TEXT` | Training table or export used. | Nullable |
| `test_table` | `TEXT` | Test table or export used. | Nullable |
| `created_at` | `TIMESTAMP` | Time the model version was registered. | Defaults to current timestamp |
| `notes` | `TEXT` | Deployment or evaluation notes. | Nullable |

## Normalization And Design Choices

- Taxi zones are stored once in `dim_zone` and referenced by foreign keys.
- Source file metadata is separated into `dim_source_file` so lineage is not duplicated across every fact row.
- Clean and processed fact tables are separated to preserve the notebook pipeline stages.
- Aggregates are intentionally denormalized because recommendation queries need fast zone/hour and route/hour summaries.
- ML feature tables preserve the exact Step 3 feature shape used by the relocation model.

## Index Strategy

The schema uses primary keys and foreign keys for important lookup paths. Additional indexes support the most common production queries:

- `idx_fact_clean_pickup_time` supports filtering cleaned trips by pickup zone and time.
- `idx_fact_clean_dropoff_zone` supports route and destination analysis.
- `idx_fact_processed_zone_hour` supports zone/day/hour aggregate jobs.
- `idx_fact_processed_route_hour` supports route/day/hour aggregate jobs.
- `idx_training_features` supports model-training and inference lookups by origin zone, day, and hour.

## Query Optimization

- Recommendation-time lookups should read from aggregate tables instead of scanning trip-level facts.
- Refresh jobs can rebuild aggregates after each monthly ingestion.
- Model-serving endpoints should use `ml_model_registry` to load the approved artifact version.
- Fact tables can be partitioned by month in a larger deployment if monthly TLC files become too large for standard indexes alone.
- Aggregate refreshes could maintain rolling averages so the app can update earning, demand, and travel-time patterns without retraining from scratch every time.

## Growth Considerations

- Trip-level fact tables can grow quickly as new monthly TLC files are added.
- Aggregate tables reduce repeated computation by precomputing zone/hour and route/hour features.
- Raw monthly files should be retained in object storage so the pipeline can be replayed if feature logic changes.
- Model versions should be registered rather than overwritten so the app can roll back to a known working artifact.
- Historical feature tables should be versioned so future model changes can be compared against the deployed model.
- New monthly TLC/Uber data could be added on a scheduled interval, such as monthly or whatever refresh cadence is chosen.
- Zone/hour and route/hour metrics could be updated as rolling averages so the system can reflect changing patterns over time.
- Keeping historical aggregate snapshots would make it possible to analyze trends such as holidays, seasonal changes, school schedules, event traffic, or other recurring demand shifts.

## Future Feature Expansion

The current model focuses on historical trip patterns, pickup/dropoff zones, day, hour, and travel time. A future scalable version could add more real-time or context-aware features if reliable data sources are available.

Potential future features:

- Uber or rideshare demand signals, such as active request volume.
- Driver supply signals, such as drivers online or driver locations by zone.
- Weather conditions, including rain, snow, temperature, or severe weather alerts.
- Events, such as concerts, sports games, conferences, or major venue activity.
- Holidays and school calendars.
- Airport delay or arrival/departure context.
- Road closures, traffic disruptions, or construction.

These features would likely require new dimension or aggregate tables. For example, weather could be stored by zone/time or city/time, events could be stored by venue/time with nearby zones, and driver supply could be stored as zone/hour snapshots. The model feature tables would then combine these new signals with the existing zone/hour and route/hour aggregates.

## Backup And Recovery

Recommended RDS backup strategy:

- Enable automated daily backups.
- Enable point-in-time recovery for production.
- Take manual snapshots before schema migrations or major data refreshes.
- Store model artifacts separately from the database, with paths tracked in `ml_model_registry`.
- Keep source file lineage so tables can be rebuilt from raw inputs if needed.
- Retain raw source files in object storage so failed or incorrect transformations can be replayed.

## Current Implementation Mapping

- Current backend artifact loading maps to `ml_model_registry` plus the Step 3 feature tables.
- Current taxi-zone CSV and shapefile assets map to `dim_zone` and map-serving data.
- Current notebook Step 1 maps to `fact_uber_trip_clean`.
- Current notebook Step 2 maps to `fact_uber_trip_processed` plus aggregate tables.
- Current notebook Step 3 maps to `ml_relocation_training_set`, `ml_relocation_test_set`, and `ml_model_registry`.

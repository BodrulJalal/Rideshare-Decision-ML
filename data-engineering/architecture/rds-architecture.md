# RDS Architecture

## Goal

Move the project from file-based local training inputs to a database-backed layout that can support:

- repeatable ingestion from TLC/HVFHV and cleaned Uber ride exports,
- feature aggregation for relocation scoring,
- trip-level storage for destination prediction,
- model artifact tracking for backend deployments.

## Proposed data flow

```mermaid
flowchart LR
    A[Raw TLC HVFHV parquet files] --> B[Bronze staging tables]
    C[Cleaned Uber ride CSV files] --> B
    D[Zone lookup CSV + shapefiles] --> E[Zone dimensions]
    B --> F[Silver normalized trip tables]
    E --> F
    F --> G[Gold hourly zone metrics]
    F --> H[Gold route travel metrics]
    G --> I[Relocation model training]
    H --> I
    F --> J[Dropoff classifier training]
    I --> K[Model registry]
    J --> K
    G --> L[FastAPI relocation service]
    H --> L
    K --> L
```

## Recommended PostgreSQL entities

### Dimensions

- `dim_zone`
  TLC location metadata, boroughs, service zones, and optional centroid coordinates.
- `dim_trip_type`
  Canonical trip type values used by the trip model.

### Facts

- `fact_trip_offer`
  Trip-level records from cleaned Uber exports or normalized HVFHV records.
- `agg_zone_hourly_metrics`
  Zone-by-hour aggregates used to estimate demand and pay-per-minute.
- `agg_route_hourly_metrics`
  Origin/destination/hour aggregates used for relocation travel-time lookups.

### ML operations

- `ml_model_registry`
  Tracks artifact path, source dataset, version, and deployment notes.

## ER diagram

```mermaid
erDiagram
    dim_zone ||--o{ fact_trip_offer : pickup_zone_id
    dim_zone ||--o{ fact_trip_offer : dropoff_zone_id
    dim_zone ||--o{ agg_zone_hourly_metrics : zone_id
    dim_zone ||--o{ agg_route_hourly_metrics : origin_zone_id
    dim_zone ||--o{ agg_route_hourly_metrics : destination_zone_id
    dim_trip_type ||--o{ fact_trip_offer : trip_type_id

    dim_zone {
        bigint zone_id PK
        int tlc_location_id
        text zone_name
        text borough
        text service_zone
        numeric centroid_lat
        numeric centroid_lng
    }

    dim_trip_type {
        bigint trip_type_id PK
        text trip_type_name
    }

    fact_trip_offer {
        bigint trip_offer_id PK
        date trip_date
        smallint day_of_week_num
        smallint pickup_hour
        numeric trip_minutes
        numeric trip_miles
        numeric driver_pay
        numeric tip_amount
        numeric surge_amount
        numeric pickup_wait_min
        bigint pickup_zone_id FK
        bigint dropoff_zone_id FK
        bigint trip_type_id FK
        text source_system
        text source_file
    }

    agg_zone_hourly_metrics {
        bigint zone_id FK
        text pickup_day_of_week
        smallint pickup_hour
        numeric avg_pay_per_minute
        int ride_demand
        numeric avg_trip_miles
    }

    agg_route_hourly_metrics {
        bigint origin_zone_id FK
        bigint destination_zone_id FK
        text pickup_day_of_week
        smallint pickup_hour
        numeric avg_travel_minutes
        numeric avg_trip_miles
        int trip_count
    }

    ml_model_registry {
        text model_name PK
        text model_version PK
        text artifact_path
        text training_source
        timestamp created_at
        text notes
    }
```

## How this maps to the current codebase

- `backend/app/services/recommender.py`
  Uses the equivalent of `agg_zone_hourly_metrics`, `agg_route_hourly_metrics`, and `dim_zone`.
- `backend/app/services/fare_predictor.py`
  Uses trip-type and pickup-zone dimensions plus trip-duration features sourced from `fact_trip_offer`.
- `Model Building/Capstone.ipynb`
  Produces the relocation ensemble artifact from hourly zone and route features.

## Recommended deployment pattern

1. Land raw parquet and cleaned CSV files in object storage or staging.
2. Normalize them into `fact_trip_offer` plus `dim_zone` and `dim_trip_type`.
3. Refresh hourly aggregates into the gold tables.
4. Retrain models offline and write artifact metadata into `ml_model_registry`.
5. Deploy the backend with the selected artifact versions.

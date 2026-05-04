# Driver Earnings Navigator

Driver Earnings Navigator is a full-stack rideshare decision-support project for drivers. It gives drivers two practical tools:

- a relocation recommender that suggests the best taxi zone to move toward next,
- a trip evaluator that predicts the most likely dropoff zone for an offered ride.

The repository is now organized into dedicated `frontend`, `backend`, and `data-engineering` areas so the application is easier to understand, run, and deploy.

## System architecture

```mermaid
flowchart LR
    Driver[Driver] --> UI[React + Vite frontend]
    UI -->|REST /api/*| API[FastAPI backend]
    API --> Relocation[Relocation recommendation service]
    API --> Trip[Trip destination prediction service]
    Relocation --> RelocationArtifact[Step 3 LightGBM relocation artifact]
    Relocation --> ZoneShapes[TLC taxi zone shapefile]
    Trip --> TripArtifact[Saved dropoff classifier artifact]
    API --> LocalData[Local CSV training fallback]
    RelocationArtifact --> Notebook[Model Building/Capstone Files/Step 3]
```

## Repository structure

```text
Rideshare-Decision-ML/
  backend/
    app/
      api/
        endpoints/
        dependencies.py
        router.py
      core/
      data/
      ml/
      schemas/
      services/
      main.py
    Dockerfile
    README.md
    requirements.txt
  frontend/
    src/
      components/
      features/
      lib/
      App.jsx
      main.jsx
      styles.css
    Dockerfile
    nginx.conf
    README.md
    package.json
  data-engineering/
    architecture/
      rds-architecture.md
    sql/
      postgres-schema.sql
    README.md
  data/
    trips/
      Uber Rides - Cleaned.csv
  Model Building/
    Capstone.ipynb
    content/
      taxi_zone_lookup.csv
      taxi_zones/
  docker-compose.yml
```

## Machine learning models

### 1. Relocation recommender

The production relocation recommender now uses the exported step-3 LightGBM model in `Model Building/Capstone Files/Step 3/relocation_model.pkl`, with runtime candidate generation driven by the accompanying `uber_trips_training.parquet` and `taxi_zone_lookup.csv`.

```mermaid
flowchart TD
    Request[Current zone + day + hour] --> Candidates[Reachable destination zones]
    Candidates --> Nearby[Closest candidate destination zones from step-3 training data]
    Nearby --> LGBM[LightGBM regressor]
    LGBM --> Ranking[Predicted net gain ranking]
    Ranking --> Result[Recommended zone + top alternatives]
```

Notebook-backed details:

| Component | Model | Role | Source |
| --- | --- | --- | --- |
| Step 3 relocation ranker | `LGBMRegressor` | Predicts `net_gain` for nearby candidate destination zones | `Model Building/Capstone Files/Step 3/Capstone Data Pipeline Step 3 with EDA.ipynb` |

Important notebook findings:

- The relocation notebook is built around NYC TLC HVFHV data plus TLC taxi-zone lookup and shapefiles.
- The exported step-3 model is a LightGBM regressor trained on `PULocationID`, `DOLocationID`, `hour_bucket`, `day_of_week_numeric`, and `average_PU_to_DO_time`.
- The notebook evaluates candidate zones by predicted `net_gain`, then compares the recommendation against a stay-put baseline.
- The backend now mirrors that notebook workflow instead of combining multiple relocation tiers.

### 2. Trip dropoff predictor

The dropoff model is served from `backend/uber_dropoff_rf_model.joblib` with label encoders in `backend/uber_label_encoders.joblib`.

```mermaid
flowchart LR
    TripInput[Trip type + pickup zone + day + hour + duration] --> Encoding[Label encoding]
    Encoding --> RF[RandomForestClassifier]
    RF --> Output[Predicted dropoff zone + top 3 probabilities]
```

Artifact-backed details:

- Model type: `RandomForestClassifier`
- Parameters loaded from the saved artifact: `n_estimators=200`, `min_samples_split=10`, `random_state=42`, `max_depth=None`
- Feature columns: `Trip_Type_Encoded`, `Day_of_Week_Num`, `Hour_Bucket`, `Duration_Minutes`, `Pickup_Zone_Encoded`
- Encoder coverage in the deployed artifact: 9 trip types, 35 pickup zones, and 43 dropoff zones

Note:
The dropoff model description above comes from direct inspection of the saved production artifact that the backend loads at runtime.

### 3. Fallback training path

If the saved artifacts are missing, the backend can still start by training simplified models from:

- `data/trips/Uber Rides - Cleaned.csv`
- synthetic fallback data in `backend/app/data/sample_data.py`

That fallback path is implemented in:

- `backend/app/ml/training.py`
- `backend/app/data/trip_dataset.py`

## Data sources

- `Model Building/content/uber_sampled_data_jan_feb_2026.csv`
  Sampled TLC HVFHV data used in the relocation notebook workflow.
- `Model Building/content/taxi_zone_lookup.csv`
  Taxi-zone lookup table for translating `LocationID` values into borough/zone names.
- `Model Building/content/taxi_zones/*`
  Shapefile assets used by the backend to produce GeoJSON for the relocation map.
- `data/trips/Uber Rides - Cleaned.csv`
  Cleaned trip data used by the lightweight fallback pipeline.

## API surface

- `GET /api/health`
- `GET /api/zones`
- `GET /api/relocation-zones`
- `GET /api/relocation-zones-geojson`
- `POST /api/recommend-zone`
- `GET /api/trip-pickup-zones`
- `GET /api/trip-types`
- `GET /api/resolve-trip-zone`
- `POST /api/evaluate-trip`

## Local development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend runs on `http://127.0.0.1:8000`.

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

The frontend runs on `http://127.0.0.1:5173`.

## Docker deployment

This repo now includes Dockerfiles for both applications and a root `docker-compose.yml`.

```bash
docker compose up --build
```

Default ports:

- frontend: `http://localhost:5173`
- backend: `http://localhost:8000`

## Data engineering and RDS documentation

The new `data-engineering/` folder documents how to move the current local-file workflow into a PostgreSQL RDS-backed architecture:

- [data-engineering/README.md](data-engineering/README.md)
- [data-engineering/architecture/rds-architecture.md](data-engineering/architecture/rds-architecture.md)
- [data-engineering/sql/postgres-schema.sql](data-engineering/sql/postgres-schema.sql)

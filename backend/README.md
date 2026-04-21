# Backend

This folder contains the FastAPI application, saved model artifacts, and backend deployment files.

## Structure

```text
backend/
  app/
    api/
      endpoints/
      dependencies.py
      router.py
    core/
      config.py
      container.py
    data/
    ml/
    schemas/
    services/
    main.py
  uber_dropoff_rf_model.joblib
  uber_label_encoders.joblib
  uber_relocation_ensemble_model_finalv1.joblib
  requirements.txt
  Dockerfile
```

## Runtime responsibilities

- Expose the `/api/*` endpoints used by the frontend.
- Load the saved relocation ensemble artifact and dropoff classifier artifact.
- Fall back to simplified CSV-driven training logic when saved artifacts are unavailable.
- Serve taxi-zone GeoJSON derived from the TLC shapefile stored under `Model Building/content/taxi_zones`.

## Local commands

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

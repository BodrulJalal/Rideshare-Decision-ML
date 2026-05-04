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
  requirements.txt
  Dockerfile
```

## Runtime responsibilities

- Expose the `/api/*` endpoints used by the frontend.
- Load the saved step-3 relocation model artifact and dropoff classifier artifact.
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

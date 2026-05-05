# Backend

This folder contains the FastAPI relocation application, saved relocation artifacts, and backend deployment files.

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
- Load the saved step-3 relocation recommender artifact.
- Fall back to simplified CSV-driven relocation logic when the saved artifact is unavailable.
- Serve taxi-zone GeoJSON derived from the TLC shapefile stored under `Model Building/content/taxi_zones`.

## Local commands

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Environment

Set these in `backend/.env` or your shell before starting the API:

```text
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

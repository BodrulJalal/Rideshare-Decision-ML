# Driver Earnings Navigator

Driver Earnings Navigator is a web app for ride-hailing drivers with a separated frontend and backend:

- `backend/` contains a FastAPI service and all machine learning logic.
- `frontend/` contains a React + Vite website that calls the backend API.

The app includes two ML features:

- A zone recommendation model that suggests the best nearby zone to wait in using zone, time of day, demand, and travel time.
- A trip evaluation model that predicts whether an offered ride is likely to be a high-fare trip including tip.

## Stack

- Python 3.13
- FastAPI
- Uvicorn
- scikit-learn
- React
- Vite

## Project structure

```text
backend/
  requirements.txt
  app/
    main.py
    api/routes.py
    data/sample_data.py
    ml/training.py
    ml/model_manager.py
    models/schemas.py
    services/traffic.py
    services/recommender.py
    services/fare_predictor.py
frontend/
  package.json
  vite.config.js
  index.html
  src/
    main.jsx
    App.jsx
    styles.css
```

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will start on `http://127.0.0.1:8000`.

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open the Vite URL, usually `http://127.0.0.1:5173`, and keep the frontend's API base URL set to `http://127.0.0.1:8000`.

## API endpoints

### `GET /api/health`

Returns a simple health check response.

### `POST /api/recommend-zone`

Example payload:

```json
{
  "current_zone": "Downtown",
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

Response includes:

- Recommended zone
- Estimated travel minutes
- Predicted hourly earnings
- Top alternatives for quick comparison

### `POST /api/evaluate-trip`

Example payload:

```json
{
  "pickup_zone": "Airport",
  "trip_minutes": 27,
  "rider_rating": 4.92
}
```

Response includes:

- Probability of a high fare
- Tip signal
- A short accept-or-be-selective recommendation

## Real-time traffic integration

`backend/app/services/traffic.py` currently uses a mocked distance and congestion estimator. To upgrade it:

1. Replace `estimate_travel_minutes` with a Google Maps, Mapbox, or HERE routing API call.
2. Keep the same response shape so the recommender service continues working.
3. Optionally add live traffic snapshots or demand feeds from a database or cache.

## Notes

- The training data is synthetic placeholder data so the full app runs out of the box.
- Both ML models train at backend startup for a self-contained demo setup.

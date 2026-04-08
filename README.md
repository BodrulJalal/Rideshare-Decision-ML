# Driver Earnings Navigator

Driver Earnings Navigator is a web app for ride-hailing drivers with a separated frontend and backend:

- `backend/` contains a FastAPI service and all machine learning logic.
- `frontend/` contains a React + Vite website that calls the backend API.

The app includes two ML features:

- A zone recommendation model that suggests the best nearby zone to wait in using zone, time of day, demand, and travel time.
- A trip evaluation model that predicts whether an offered ride is likely to be a high-fare trip including tip.

By default, the backend now looks for a trip dataset CSV in `data/trips/` and trains the models from that file. If no CSV is present, it falls back to the synthetic demo data.

## Stack

- Python 3.13
- FastAPI
- Uvicorn
- scikit-learn
- React
- Vite

## Project structure

```text
data/
  trips/
    Uber Rides - Cleaned.csv
backend/
  requirements.txt
  app/
    main.py
    api/routes.py
    data/sample_data.py
    data/trip_dataset.py
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
copy .env.example .env
npm run dev
```

Then open the Vite URL, usually `http://127.0.0.1:5173`. The frontend reads the backend URL from `frontend/.env` via `VITE_API_BASE_URL`.

## API endpoints

### `GET /api/health`

Returns a simple health check response.

### `POST /api/recommend-zone`

Example payload:

```json
{
  "current_zone": "Brooklyn",
  "address": null,
  "day_of_week": 4,
  "hour": 18
}
```

Response includes:

- Recommended zone
- Estimated travel minutes
- Predicted hourly earnings
- Top alternatives for quick comparison

You can identify the current location by:

- Choosing a known zone from the dataset, such as `Brooklyn`, `Flushing`, or `Ridgewood`
- Entering an address that includes one of those location names, like `W 49th St, New York, NY` or `Myrtle Ave, Ridgewood, NY`
- Optionally enabling a shared custom day/time override in the UI; otherwise the current day and time are used automatically

### `POST /api/evaluate-trip`

Example payload:

```json
{
  "pickup_zone": "Brooklyn",
  "day_of_week": 5,
  "hour": 21,
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

- Both ML models train at backend startup.
- When `data/trips/*.csv` exists, the backend uses that real trip history to train.
- If the CSV is missing, the app falls back to synthetic placeholder data so the demo still runs out of the box.

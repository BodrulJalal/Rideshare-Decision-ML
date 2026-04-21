# Frontend

This folder contains the React + Vite client for the rideshare decision app.

## Structure

```text
frontend/
  src/
    components/
      map/
      sections/
    features/
      relocation/
      trip/
    lib/
      api.js
      constants.js
      geolocation.js
    App.jsx
    main.jsx
    styles.css
```

## Responsibilities

- Load zones, trip types, and taxi-zone GeoJSON from the backend.
- Let drivers request a relocation recommendation.
- Let drivers predict the most likely dropoff zone for a trip offer.
- Render the taxi-zone SVG map and highlight the current, recommended, and alternate zones.

## Local commands

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
npm run build
```

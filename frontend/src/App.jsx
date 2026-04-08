import { useState } from "react";

const ZONES = ["Downtown", "Airport", "Midtown", "Stadium District", "University", "Waterfront"];

const defaultZoneForm = {
  current_zone: "",
  latitude: "",
  longitude: "",
};

const defaultTripForm = {
  pickup_zone: "Downtown",
  trip_minutes: "",
  rider_rating: "",
};

function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState("http://127.0.0.1:8000");
  const [zoneForm, setZoneForm] = useState(defaultZoneForm);
  const [tripForm, setTripForm] = useState(defaultTripForm);
  const [zoneResult, setZoneResult] = useState(null);
  const [tripResult, setTripResult] = useState(null);
  const [zoneError, setZoneError] = useState("");
  const [tripError, setTripError] = useState("");
  const [zoneLoading, setZoneLoading] = useState(false);
  const [tripLoading, setTripLoading] = useState(false);

  async function postJson(path, payload) {
    const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Something went wrong.");
    }
    return data;
  }

  async function handleZoneSubmit(event) {
    event.preventDefault();
    setZoneLoading(true);
    setZoneError("");
    setZoneResult(null);

    try {
      const payload = {
        current_zone: zoneForm.current_zone || null,
        latitude: zoneForm.latitude ? Number(zoneForm.latitude) : null,
        longitude: zoneForm.longitude ? Number(zoneForm.longitude) : null,
      };
      const data = await postJson("/api/recommend-zone", payload);
      setZoneResult(data);
    } catch (error) {
      setZoneError(error.message);
    } finally {
      setZoneLoading(false);
    }
  }

  async function handleTripSubmit(event) {
    event.preventDefault();
    setTripLoading(true);
    setTripError("");
    setTripResult(null);

    try {
      const payload = {
        pickup_zone: tripForm.pickup_zone,
        trip_minutes: Number(tripForm.trip_minutes),
        rider_rating: Number(tripForm.rider_rating),
      };
      const data = await postJson("/api/evaluate-trip", payload);
      setTripResult(data);
    } catch (error) {
      setTripError(error.message);
    } finally {
      setTripLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Ride-Hailing Driver Toolkit</p>
          <h1>Pick better zones. Judge offers faster.</h1>
          <p className="hero-copy">
            A React frontend talks to a FastAPI backend to help drivers reposition toward stronger
            zones and quickly assess whether a ride offer is worth taking.
          </p>
        </div>
        <div className="hero-card">
          <p>Powered by two ML endpoints</p>
          <ul>
            <li>Best-zone recommendation using demand, time of day, and travel time</li>
            <li>High-fare likelihood scoring using pickup zone, trip duration, and rider rating</li>
            <li>Mock travel-time service that is ready for live maps API integration</li>
          </ul>
        </div>
      </section>

      <section className="api-config panel">
        <h2>Backend Connection</h2>
        <label>
          FastAPI base URL
          <input value={apiBaseUrl} onChange={(event) => setApiBaseUrl(event.target.value)} />
        </label>
        <p className="helper-text">Run the backend locally and keep this pointed at that server.</p>
      </section>

      <section className="app-grid">
        <article className="panel">
          <h2>Best Zone To Wait</h2>
          <form className="form-grid" onSubmit={handleZoneSubmit}>
            <label>
              Current zone
              <select
                value={zoneForm.current_zone}
                onChange={(event) => setZoneForm({ ...zoneForm, current_zone: event.target.value })}
              >
                <option value="">Auto-detect from coordinates</option>
                {ZONES.map((zone) => (
                  <option key={zone} value={zone}>
                    {zone}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Latitude
              <input
                type="number"
                step="0.0001"
                placeholder="40.7128"
                value={zoneForm.latitude}
                onChange={(event) => setZoneForm({ ...zoneForm, latitude: event.target.value })}
              />
            </label>
            <label>
              Longitude
              <input
                type="number"
                step="0.0001"
                placeholder="-74.0060"
                value={zoneForm.longitude}
                onChange={(event) => setZoneForm({ ...zoneForm, longitude: event.target.value })}
              />
            </label>
            <button type="submit">{zoneLoading ? "Scoring nearby zones..." : "Recommend zone"}</button>
          </form>
          <div className={`result-card ${!zoneResult && !zoneError ? "muted" : ""}`}>
            {zoneError && <p>{zoneError}</p>}
            {zoneResult && (
              <>
                <strong>{zoneResult.recommended_zone}</strong>
                <p>{zoneResult.driver_message}</p>
                <div className="pill">Confidence gap: {zoneResult.confidence_gap}</div>
                <p>Current zone: {zoneResult.current_zone}</p>
                <p>Top options right now:</p>
                <ul>
                  {zoneResult.top_alternatives.map((item) => (
                    <li key={item.zone}>
                      <strong>{item.zone}</strong>: ${item.predicted_hourly_earnings}/hr, {item.travel_minutes} min away,
                      demand {item.demand_index}
                    </li>
                  ))}
                </ul>
              </>
            )}
            {!zoneResult && !zoneError && (
              <p>Enter your current zone or coordinates to see where demand looks strongest.</p>
            )}
          </div>
        </article>

        <article className="panel">
          <h2>Evaluate Offered Trip</h2>
          <form className="form-grid" onSubmit={handleTripSubmit}>
            <label>
              Pickup zone
              <select
                value={tripForm.pickup_zone}
                onChange={(event) => setTripForm({ ...tripForm, pickup_zone: event.target.value })}
              >
                {ZONES.map((zone) => (
                  <option key={zone} value={zone}>
                    {zone}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Predicted trip time (minutes)
              <input
                type="number"
                step="1"
                min="1"
                placeholder="22"
                value={tripForm.trip_minutes}
                onChange={(event) => setTripForm({ ...tripForm, trip_minutes: event.target.value })}
              />
            </label>
            <label>
              Rider rating
              <input
                type="number"
                step="0.01"
                min="4"
                max="5"
                placeholder="4.89"
                value={tripForm.rider_rating}
                onChange={(event) => setTripForm({ ...tripForm, rider_rating: event.target.value })}
              />
            </label>
            <button type="submit">{tripLoading ? "Estimating fare quality..." : "Score trip"}</button>
          </form>
          <div className={`result-card ${!tripResult && !tripError ? "muted" : ""}`}>
            {tripError && <p>{tripError}</p>}
            {tripResult && (
              <>
                <strong>{tripResult.likely_high_fare ? "High-fare signal" : "Borderline offer"}</strong>
                <p>{tripResult.driver_message}</p>
                <div className="pill">
                  {(tripResult.high_fare_probability * 100).toFixed(1)}% high-fare probability
                </div>
                <p>Expected tip signal: ${tripResult.expected_tip_signal}</p>
                <p>
                  Inputs used: {tripResult.pickup_zone}, {tripResult.trip_minutes} min, rider rating{" "}
                  {tripResult.rider_rating}
                </p>
              </>
            )}
            {!tripResult && !tripError && (
              <p>Add the offer details to estimate whether the trip is likely to land in the high-fare tier.</p>
            )}
          </div>
        </article>
      </section>
    </main>
  );
}

export default App;

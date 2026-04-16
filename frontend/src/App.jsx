import { useEffect, useRef, useState } from "react";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const DAY_OPTIONS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const TIME_OPTIONS = Array.from({ length: 24 }, (_, hour) => ({
  value: String(hour),
  label: new Date(2024, 0, 1, hour).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
}));

const defaultZoneForm = {
  current_zone: "",
  locationLabel: "",
  latitude: null,
  longitude: null,
};

const defaultTripForm = {
  pickup_zone: "",
  trip_minutes: "",
  rider_rating: "",
};

function App() {
  const [tripZones, setTripZones] = useState([]);
  const [relocationZones, setRelocationZones] = useState([]);
  const [relocationGeoJson, setRelocationGeoJson] = useState(null);
  const [activeTool, setActiveTool] = useState("relocation");
  const [useCustomTime, setUseCustomTime] = useState(false);
  const [timeOverride, setTimeOverride] = useState({
    day_of_week: String((new Date().getDay() + 6) % 7),
    hour: String(new Date().getHours()),
  });
  const [zoneForm, setZoneForm] = useState(defaultZoneForm);
  const [tripForm, setTripForm] = useState(defaultTripForm);
  const [zoneResult, setZoneResult] = useState(null);
  const [tripResult, setTripResult] = useState(null);
  const [zoneError, setZoneError] = useState("");
  const [tripError, setTripError] = useState("");
  const [zoneLoading, setZoneLoading] = useState(false);
  const [tripLoading, setTripLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadZones() {
      try {
        const [tripResponse, relocationResponse, geoJsonResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/api/zones`),
          fetch(`${API_BASE_URL}/api/relocation-zones`),
          fetch(`${API_BASE_URL}/api/relocation-zones-geojson`),
        ]);
        const [tripData, relocationData, geoJsonData] = await Promise.all([
          tripResponse.json(),
          relocationResponse.json(),
          geoJsonResponse.json(),
        ]);
        if (!tripResponse.ok || !relocationResponse.ok || !geoJsonResponse.ok) {
          throw new Error("Unable to load zones.");
        }
        if (!cancelled && Array.isArray(tripData) && Array.isArray(relocationData)) {
          setTripZones(tripData);
          setRelocationZones(relocationData);
          setRelocationGeoJson(geoJsonData);
          setTripForm((current) => ({
            ...current,
            pickup_zone:
              current.pickup_zone && tripData.includes(current.pickup_zone) ? current.pickup_zone : (tripData[0] || ""),
          }));
          setZoneForm((current) => ({
            ...current,
            current_zone:
              current.current_zone && relocationData.some((zone) => String(zone.id) === current.current_zone)
                ? current.current_zone
                : "",
          }));
        }
      } catch (error) {
        if (!cancelled) {
          setTripZones([]);
          setRelocationZones([]);
          setRelocationGeoJson(null);
        }
      }
    }

    loadZones();
    return () => {
      cancelled = true;
    };
  }, []);

  async function postJson(path, payload) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
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

  async function requestZoneRecommendation(overrides = {}) {
    setZoneLoading(true);
    setZoneError("");
    setZoneResult(null);

    try {
      const payload = {
        current_zone: zoneForm.current_zone || null,
        address: null,
        day_of_week: useCustomTime ? Number(timeOverride.day_of_week) : null,
        hour: useCustomTime ? Number(timeOverride.hour) : null,
        latitude: zoneForm.current_zone ? null : zoneForm.latitude,
        longitude: zoneForm.current_zone ? null : zoneForm.longitude,
        ...overrides,
      };
      const data = await postJson("/api/recommend-zone", payload);
      setZoneResult(data);
    } catch (error) {
      setZoneError(error.message);
    } finally {
      setZoneLoading(false);
    }
  }

  async function handleZoneSubmit(event) {
    event.preventDefault();
    await requestZoneRecommendation();
  }

  function handleUseCurrentLocation() {
    setZoneError("");

    if (!navigator.geolocation) {
      setZoneError("Your browser does not support location access.");
      return;
    }

    setLocationLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setZoneForm((current) => ({
          ...current,
          current_zone: "",
          locationLabel: "Using current device location",
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        }));
        setLocationLoading(false);
      },
      (error) => {
        const message =
          error.code === error.PERMISSION_DENIED
            ? "Location access was denied."
            : "Unable to get your current location.";
        setZoneError(message);
        setLocationLoading(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      },
    );
  }

  async function handleTripSubmit(event) {
    event.preventDefault();
    setTripLoading(true);
    setTripError("");
    setTripResult(null);

    try {
      const payload = {
        pickup_zone: tripForm.pickup_zone,
        day_of_week: useCustomTime ? Number(timeOverride.day_of_week) : null,
        hour: useCustomTime ? Number(timeOverride.hour) : null,
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

  const relocationZoneLookup = Object.fromEntries(relocationZones.map((zone) => [zone.name, zone.id]));
  const selectedZoneId = Number(zoneForm.current_zone || 0);
  const resultCurrentZoneId = zoneResult?.current_zone ? relocationZoneLookup[zoneResult.current_zone] || 0 : 0;
  const currentZoneId = selectedZoneId || resultCurrentZoneId;
  const highlightedZoneIds = new Map();
  if (zoneResult?.recommended_zone && relocationZoneLookup[zoneResult.recommended_zone]) {
    const recommendedZoneId = relocationZoneLookup[zoneResult.recommended_zone];
    highlightedZoneIds.set(recommendedZoneId, "recommended");
  }
  zoneResult?.top_alternatives?.forEach((item) => {
    const zoneId = relocationZoneLookup[item.zone];
    if (zoneId && !highlightedZoneIds.has(zoneId)) {
      highlightedZoneIds.set(zoneId, "alternative");
    }
  });
  if (currentZoneId && !highlightedZoneIds.has(currentZoneId)) {
    highlightedZoneIds.set(currentZoneId, "current");
  }

  const activeDayIndex = useCustomTime ? Number(timeOverride.day_of_week) : ((new Date().getDay() + 6) % 7);
  const activeHourValue = useCustomTime ? String(timeOverride.hour) : String(new Date().getHours());
  const activeTimeLabel = TIME_OPTIONS.find((option) => option.value === activeHourValue)?.label || `${activeHourValue}:00`;

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
            <li>Relocation recommendations from your saved Uber zone model</li>
            <li>High-fare likelihood scoring using pickup zone, trip duration, and rider rating</li>
            <li>Travel time and demand signals blended into the relocation ranking response</li>
          </ul>
        </div>
      </section>

      <section className="panel time-panel">
        <div className="time-panel-header">
          <h2>Time Settings</h2>
          <label>
            <input
              type="checkbox"
              checked={useCustomTime}
              onChange={(event) => setUseCustomTime(event.target.checked)}
            />{" "}
            Use custom day and time for both tools
          </label>
        </div>
        {useCustomTime && (
          <div className="time-controls">
            <label>
              Day
              <select
                value={timeOverride.day_of_week}
                onChange={(event) => setTimeOverride({ ...timeOverride, day_of_week: event.target.value })}
              >
                {DAY_OPTIONS.map((day, index) => (
                  <option key={day} value={index}>
                    {day}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Time
              <select
                value={timeOverride.hour}
                onChange={(event) => setTimeOverride({ ...timeOverride, hour: event.target.value })}
              >
                {TIME_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </section>

      <section className="panel tool-switcher">
        <div className="section-header">
          <h2>Choose Tool</h2>
          <div className="segmented-control" aria-label="Model selector">
            <button
              type="button"
              className={activeTool === "relocation" ? "active" : ""}
              onClick={() => setActiveTool("relocation")}
            >
              Relocator
            </button>
            <button
              type="button"
              className={activeTool === "trip" ? "active" : ""}
              onClick={() => setActiveTool("trip")}
            >
              Trip Evaluator
            </button>
          </div>
        </div>
      </section>

      <section className={`app-grid ${activeTool === "trip" ? "single-tool" : ""}`}>
        {activeTool === "relocation" ? (
          <>
            <article className="panel">
              <h2>Best Zone To Wait</h2>
              <form className="form-grid" onSubmit={handleZoneSubmit}>
                <label>
                  Current zone
                  <select
                    value={zoneForm.current_zone}
                    onChange={(event) =>
                      setZoneForm({
                        ...zoneForm,
                        current_zone: event.target.value,
                        locationLabel: event.target.value ? "" : zoneForm.locationLabel,
                        latitude: event.target.value ? null : zoneForm.latitude,
                        longitude: event.target.value ? null : zoneForm.longitude,
                      })
                    }
                  >
                    <option value="">Use current location instead</option>
                    {relocationZones.map((zone) => (
                      <option key={zone.id} value={zone.id}>
                        {zone.name} ({zone.id})
                      </option>
                    ))}
                  </select>
                </label>
                <div className="location-picker">
                  <span className="location-label">Current location</span>
                  <button type="button" className="secondary-button" onClick={handleUseCurrentLocation} disabled={locationLoading}>
                    {locationLoading ? "Finding your location..." : "Use current location"}
                  </button>
                  {zoneForm.locationLabel && !zoneForm.current_zone && (
                    <p className="helper-text">{zoneForm.locationLabel}</p>
                  )}
                </div>
                <button type="submit">{zoneLoading ? "Scoring nearby zones..." : "Recommend zone"}</button>
              </form>
              <div className={`result-card ${!zoneResult && !zoneError ? "muted" : ""}`}>
                {zoneError && <p>{zoneError}</p>}
                {zoneResult && (
                  <>
                    <strong>{zoneResult.recommended_zone}</strong>
                    <p>{zoneResult.driver_message}</p>
                    <p>Current zone: {zoneResult.current_zone}</p>
                    <p>
                      Inputs used: {zoneResult.current_zone}, {DAY_OPTIONS[activeDayIndex]}, {activeTimeLabel}
                    </p>
                    <p>Top options right now:</p>
                    <ul>
                      {zoneResult.top_alternatives.map((item) => (
                        <li key={item.zone}>
                          <strong>{item.zone}</strong>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {!zoneResult && !zoneError && (
                  <p>Choose a zone or use your device location to see the best place to reposition.</p>
                )}
              </div>
            </article>

            <article className="panel map-panel">
              <h2>Zone Map</h2>
              {relocationGeoJson ? (
                <div className="map-card map-card-embedded">
                  <RelocationZoneMap
                    geoJson={relocationGeoJson}
                    highlightedZoneIds={highlightedZoneIds}
                    currentZoneId={currentZoneId}
                  />
                  <div className="map-legend">
                    <span><i className="legend-swatch current" /> Current</span>
                    <span><i className="legend-swatch recommended" /> Recommended</span>
                    <span><i className="legend-swatch alternative" /> Top alternatives</span>
                  </div>
                </div>
              ) : (
                <div className="result-card muted">
                  <p>Loading taxi zone map...</p>
                </div>
              )}
            </article>
          </>
        ) : (
          <article className="panel single-panel">
            <h2>Evaluate Offered Trip</h2>
            <form className="form-grid" onSubmit={handleTripSubmit}>
              <label>
                Pickup zone
                <select
                  value={tripForm.pickup_zone}
                  onChange={(event) => setTripForm({ ...tripForm, pickup_zone: event.target.value })}
                >
                  {tripZones.map((zone) => (
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
                  min="0"
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
        )}
      </section>
    </main>
  );
}

function RelocationZoneMap({ geoJson, highlightedZoneIds, currentZoneId }) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const svgRef = useRef(null);
  const dragRef = useRef(null);
  const features = Array.isArray(geoJson?.features) ? geoJson.features : [];
  const highlightedEntries = Array.from(highlightedZoneIds?.entries?.() || []);
  const highlightKey = highlightedEntries.map(([zoneId, tone]) => `${zoneId}:${tone}`).join("|");
  if (!features.length) {
    return <p className="helper-text">Taxi zone map unavailable.</p>;
  }

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const pathItems = [];
  const zoneBounds = new Map();
  const zoneCenters = new Map();

  for (const feature of features) {
    const locationId = feature.properties.LocationID;
    const geometryType = feature.geometry?.type;
    const coordinates = feature.geometry?.coordinates || [];
    const polygons = geometryType === "Polygon" ? [coordinates] : coordinates;
    const pathSegments = [];
    let zoneMinX = Infinity;
    let zoneMinY = Infinity;
    let zoneMaxX = -Infinity;
    let zoneMaxY = -Infinity;

    for (const polygon of polygons) {
      for (const ring of polygon) {
        if (!Array.isArray(ring) || !ring.length) {
          continue;
        }
        const commands = ring.map(([x, y], index) => {
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
          zoneMinX = Math.min(zoneMinX, x);
          zoneMinY = Math.min(zoneMinY, y);
          zoneMaxX = Math.max(zoneMaxX, x);
          zoneMaxY = Math.max(zoneMaxY, y);
          const command = index === 0 ? "M" : "L";
          return `${command} ${x} ${-y}`;
        });
        pathSegments.push(`${commands.join(" ")} Z`);
      }
    }

    pathItems.push({
      id: locationId,
      zone: feature.properties.zone,
      path: pathSegments.join(" "),
      tone: highlightedZoneIds.get(locationId) || "default",
    });

    if (zoneMinX !== Infinity) {
      zoneBounds.set(locationId, {
        minX: zoneMinX,
        minY: zoneMinY,
        maxX: zoneMaxX,
        maxY: zoneMaxY,
      });
      zoneCenters.set(locationId, {
        x: zoneMinX + (zoneMaxX - zoneMinX) / 2,
        y: -(zoneMinY + (zoneMaxY - zoneMinY) / 2),
      });
    }
  }

  const width = maxX - minX || 1;
  const height = maxY - minY || 1;
  const centerX = minX + width / 2;
  const centerY = (-maxY) + height / 2;
  const zoomedWidth = width / zoomLevel;
  const zoomedHeight = height / zoomLevel;
  const maxPanX = Math.max(0, (width - zoomedWidth) / 2);
  const maxPanY = Math.max(0, (height - zoomedHeight) / 2);
  const constrainedPanX = Math.max(-maxPanX, Math.min(maxPanX, panOffset.x));
  const constrainedPanY = Math.max(-maxPanY, Math.min(maxPanY, panOffset.y));
  const viewBox = `${centerX - zoomedWidth / 2 + constrainedPanX} ${centerY - zoomedHeight / 2 + constrainedPanY} ${zoomedWidth} ${zoomedHeight}`;
  const currentZoneCenter = currentZoneId ? zoneCenters.get(currentZoneId) : null;

  useEffect(() => {
    if (!highlightedEntries.length) {
      return;
    }

    let focusMinX = Infinity;
    let focusMinY = Infinity;
    let focusMaxX = -Infinity;
    let focusMaxY = -Infinity;

    for (const [zoneId] of highlightedEntries) {
      const bounds = zoneBounds.get(zoneId);
      if (!bounds) {
        continue;
      }
      focusMinX = Math.min(focusMinX, bounds.minX);
      focusMinY = Math.min(focusMinY, bounds.minY);
      focusMaxX = Math.max(focusMaxX, bounds.maxX);
      focusMaxY = Math.max(focusMaxY, bounds.maxY);
    }

    if (focusMinX === Infinity) {
      return;
    }

    const focusWidth = Math.max(0.01, focusMaxX - focusMinX);
    const focusHeight = Math.max(0.01, focusMaxY - focusMinY);
    const paddedWidth = Math.min(width, focusWidth * 1.75);
    const paddedHeight = Math.min(height, focusHeight * 1.75);
    const nextZoom = Math.max(1, Math.min(8, Math.min(width / paddedWidth, height / paddedHeight)));
    const targetCenterX = focusMinX + focusWidth / 2;
    const targetCenterY = (-focusMaxY + -focusMinY) / 2;

    setZoomLevel(nextZoom);
    setPanOffset({
      x: targetCenterX - centerX,
      y: targetCenterY - centerY,
    });
  }, [centerX, centerY, height, highlightKey, width]);

  function handleZoomIn() {
    setZoomLevel((value) => Math.min(8, value * 1.35));
  }

  function handleZoomOut() {
    setZoomLevel((value) => {
      const nextValue = Math.max(1, value / 1.35);
      if (nextValue === 1) {
        setPanOffset({ x: 0, y: 0 });
      }
      return nextValue;
    });
  }

  function handleResetView() {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  }

  function handlePointerDown(event) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) {
      return;
    }
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startPanX: constrainedPanX,
      startPanY: constrainedPanY,
      rectWidth: rect.width,
      rectHeight: rect.height,
    };
    if (zoomLevel > 1) {
      setIsDragging(true);
    }
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event) {
    if (!dragRef.current || dragRef.current.pointerId !== event.pointerId) {
      return;
    }
    if (zoomLevel <= 1) {
      return;
    }
    const deltaX = ((event.clientX - dragRef.current.startX) * zoomedWidth) / dragRef.current.rectWidth;
    const deltaY = ((event.clientY - dragRef.current.startY) * zoomedHeight) / dragRef.current.rectHeight;
    setPanOffset({
      x: dragRef.current.startPanX - deltaX,
      y: dragRef.current.startPanY - deltaY,
    });
  }

  function handlePointerUp(event) {
    if (dragRef.current && dragRef.current.pointerId === event.pointerId) {
      dragRef.current = null;
      setIsDragging(false);
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }

  function handleWheel(event) {
    event.preventDefault();
    event.stopPropagation();
    const direction = event.deltaY < 0 ? 1 : -1;
    setZoomLevel((value) => {
      const nextValue = direction > 0 ? Math.min(8, value * 1.2) : Math.max(1, value / 1.2);
      if (nextValue === 1) {
        setPanOffset({ x: 0, y: 0 });
      }
      return nextValue;
    });
  }

  return (
    <>
      <div className="map-toolbar">
        <div className="map-zoom-controls" aria-label="Map zoom controls">
          <button type="button" className="secondary-button map-tool-button" onClick={handleZoomOut}>
            -
          </button>
          <button type="button" className="secondary-button map-tool-button" onClick={handleZoomIn}>
            +
          </button>
          <button type="button" className="secondary-button map-tool-button" onClick={handleResetView}>
            Reset
          </button>
        </div>
        <p className="helper-text">Scroll to zoom and drag to pan.</p>
      </div>
      <svg
        ref={svgRef}
        className={`relocation-map ${isDragging ? "dragging" : ""}`}
        viewBox={viewBox}
        role="img"
        aria-label="NYC taxi zone map"
        onWheelCapture={handleWheel}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      >
        {pathItems.map((item) => (
          <path key={item.id} d={item.path} className={`zone-shape ${item.tone}`} data-zone-id={item.id}>
            <title>{`${item.zone} (${item.id})`}</title>
          </path>
        ))}
        {currentZoneCenter && (
          <g className="current-zone-star-layer">
            <circle
              cx={currentZoneCenter.x}
              cy={currentZoneCenter.y}
              r={Math.max(width, height) * 0.0135}
              className="current-zone-star-badge"
            />
            <path
              d={buildStarPath(currentZoneCenter.x, currentZoneCenter.y, Math.max(width, height) * 0.012)}
              className="current-zone-star-outline"
            />
            <path
              d={buildStarPath(currentZoneCenter.x, currentZoneCenter.y, Math.max(width, height) * 0.0105)}
              className="current-zone-star"
            >
              <title>Current zone marker</title>
            </path>
          </g>
        )}
      </svg>
    </>
  );
}

function buildStarPath(cx, cy, outerRadius) {
  const innerRadius = outerRadius * 0.45;
  const points = [];

  for (let index = 0; index < 10; index += 1) {
    const angle = (-Math.PI / 2) + (index * Math.PI) / 5;
    const radius = index % 2 === 0 ? outerRadius : innerRadius;
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;
    points.push(`${index === 0 ? "M" : "L"} ${x} ${y}`);
  }

  return `${points.join(" ")} Z`;
}

export default App;

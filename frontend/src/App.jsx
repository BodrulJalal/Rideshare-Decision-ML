import { useEffect, useState } from "react";

import HeroSection from "./components/sections/HeroSection";
import TimeSettingsPanel from "./components/sections/TimeSettingsPanel";
import ToolSwitcherPanel from "./components/sections/ToolSwitcherPanel";
import RelocationPlanner from "./features/relocation/RelocationPlanner";
import ZoneMapPanel from "./features/relocation/ZoneMapPanel";
import TripEvaluator from "./features/trip/TripEvaluator";
import { fetchJson, postJson } from "./lib/api";
import {
  DAY_OPTIONS,
  TIME_OPTIONS,
  TRIP_MINUTE_PRESETS,
  createDefaultTimeOverride,
  defaultTripForm,
  defaultZoneForm,
} from "./lib/constants";
import { getCurrentPosition, getGeolocationErrorMessage } from "./lib/geolocation";

function App() {
  const [tripZones, setTripZones] = useState([]);
  const [tripTypes, setTripTypes] = useState([]);
  const [relocationZones, setRelocationZones] = useState([]);
  const [relocationGeoJson, setRelocationGeoJson] = useState(null);
  const [activeTool, setActiveTool] = useState("relocation");
  const [useCustomTime, setUseCustomTime] = useState(false);
  const [timeOverride, setTimeOverride] = useState(createDefaultTimeOverride);
  const [zoneForm, setZoneForm] = useState(defaultZoneForm);
  const [tripForm, setTripForm] = useState(defaultTripForm);
  const [zoneResult, setZoneResult] = useState(null);
  const [tripResult, setTripResult] = useState(null);
  const [zoneError, setZoneError] = useState("");
  const [tripError, setTripError] = useState("");
  const [zoneLoading, setZoneLoading] = useState(false);
  const [tripLoading, setTripLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);
  const [tripLocationLoading, setTripLocationLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadAppData() {
      try {
        const [tripData, tripTypesData, relocationData, geoJsonData] = await Promise.all([
          fetchJson("/api/trip-pickup-zones"),
          fetchJson("/api/trip-types"),
          fetchJson("/api/relocation-zones"),
          fetchJson("/api/relocation-zones-geojson"),
        ]);

        if (!cancelled && Array.isArray(tripData) && Array.isArray(relocationData)) {
          setTripZones(tripData);
          setTripTypes(Array.isArray(tripTypesData) ? tripTypesData : []);
          setRelocationZones(relocationData);
          setRelocationGeoJson(geoJsonData);
          setTripForm((current) => ({
            ...current,
            pickup_zone:
              current.pickup_zone && tripData.includes(current.pickup_zone) ? current.pickup_zone : (tripData[0] || ""),
            trip_type:
              current.trip_type && tripTypesData.includes(current.trip_type) ? current.trip_type : (tripTypesData[0] || ""),
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
          setTripTypes([]);
          setRelocationZones([]);
          setRelocationGeoJson(null);
        }
      }
    }

    loadAppData();
    return () => {
      cancelled = true;
    };
  }, []);

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

  async function handleUseCurrentLocation() {
    setZoneError("");

    if (!navigator.geolocation) {
      setZoneError("Your browser does not support location access.");
      return;
    }

    setLocationLoading(true);
    try {
      const position = await getCurrentPosition();
      setZoneForm((current) => ({
        ...current,
        current_zone: "",
        locationLabel: "Using current device location",
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      }));
    } catch (error) {
      setZoneError(getGeolocationErrorMessage(error));
    } finally {
      setLocationLoading(false);
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
        trip_type: tripForm.trip_type,
        day_of_week: useCustomTime ? Number(timeOverride.day_of_week) : null,
        hour: useCustomTime ? Number(timeOverride.hour) : null,
        trip_minutes: Number(tripForm.trip_minutes),
      };
      const data = await postJson("/api/evaluate-trip", payload);
      setTripResult(data);
    } catch (error) {
      setTripError(error.message);
    } finally {
      setTripLoading(false);
    }
  }

  async function handleUseTripCurrentLocation() {
    setTripError("");

    if (!navigator.geolocation) {
      setTripError("Your browser does not support location access.");
      return;
    }

    setTripLocationLoading(true);
    try {
      const position = await getCurrentPosition();
      const params = new URLSearchParams({
        latitude: String(position.coords.latitude),
        longitude: String(position.coords.longitude),
      });
      const zone = await fetchJson(`/api/resolve-trip-zone?${params.toString()}`);
      setTripForm((current) => ({
        ...current,
        pickup_zone: zone,
      }));
    } catch (error) {
      setTripError(error.message || getGeolocationErrorMessage(error));
    } finally {
      setTripLocationLoading(false);
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
      <HeroSection />
      <TimeSettingsPanel
        dayOptions={DAY_OPTIONS}
        timeOptions={TIME_OPTIONS}
        timeOverride={timeOverride}
        useCustomTime={useCustomTime}
        onTimeOverrideChange={setTimeOverride}
        onUseCustomTimeChange={setUseCustomTime}
      />
      <ToolSwitcherPanel activeTool={activeTool} onToolChange={setActiveTool} />

      <section className={`app-grid ${activeTool === "trip" ? "single-tool" : ""}`}>
        {activeTool === "relocation" ? (
          <>
            <RelocationPlanner
              activeDayIndex={activeDayIndex}
              activeTimeLabel={activeTimeLabel}
              dayOptions={DAY_OPTIONS}
              locationLoading={locationLoading}
              onSubmit={handleZoneSubmit}
              onUseCurrentLocation={handleUseCurrentLocation}
              relocationZones={relocationZones}
              setZoneForm={setZoneForm}
              zoneError={zoneError}
              zoneForm={zoneForm}
              zoneLoading={zoneLoading}
              zoneResult={zoneResult}
            />
            <ZoneMapPanel
              currentZoneId={currentZoneId}
              highlightedZoneIds={highlightedZoneIds}
              relocationGeoJson={relocationGeoJson}
            />
          </>
        ) : (
          <TripEvaluator
            activeDayIndex={activeDayIndex}
            activeTimeLabel={activeTimeLabel}
            dayOptions={DAY_OPTIONS}
            onSubmit={handleTripSubmit}
            onUseCurrentLocation={handleUseTripCurrentLocation}
            setTripForm={setTripForm}
            tripError={tripError}
            tripForm={tripForm}
            tripLoading={tripLoading}
            tripLocationLoading={tripLocationLoading}
            tripMinutePresets={TRIP_MINUTE_PRESETS}
            tripResult={tripResult}
            tripTypes={tripTypes}
            tripZones={tripZones}
          />
        )}
      </section>
    </main>
  );
}

export default App;

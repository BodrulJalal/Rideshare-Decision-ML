import { useEffect, useState } from "react";

import HeroSection from "./components/sections/HeroSection";
import TimeSettingsPanel from "./components/sections/TimeSettingsPanel";
import RelocationPlanner from "./features/relocation/RelocationPlanner";
import ZoneMapPanel from "./features/relocation/ZoneMapPanel";
import { fetchJson, postJson } from "./lib/api";
import { DAY_OPTIONS, TIME_OPTIONS, createDefaultTimeOverride, defaultZoneForm } from "./lib/constants";
import { getCurrentPosition, getGeolocationErrorMessage } from "./lib/geolocation";

function App() {
  const [relocationZones, setRelocationZones] = useState([]);
  const [relocationGeoJson, setRelocationGeoJson] = useState(null);
  const [useCustomTime, setUseCustomTime] = useState(false);
  const [timeOverride, setTimeOverride] = useState(createDefaultTimeOverride);
  const [zoneForm, setZoneForm] = useState(defaultZoneForm);
  const [zoneResult, setZoneResult] = useState(null);
  const [zoneError, setZoneError] = useState("");
  const [zoneLoading, setZoneLoading] = useState(false);
  const [locationLoading, setLocationLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadAppData() {
      try {
        const [relocationData, geoJsonData] = await Promise.all([
          fetchJson("/api/relocation-zones"),
          fetchJson("/api/relocation-zones-geojson"),
        ]);

        if (!cancelled && Array.isArray(relocationData)) {
          setRelocationZones(relocationData);
          setRelocationGeoJson(geoJsonData);
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

      <section className="app-grid">
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
      </section>
    </main>
  );
}

export default App;

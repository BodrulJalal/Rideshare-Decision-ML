function RelocationPlanner({
  activeDayIndex,
  activeTimeLabel,
  dayOptions,
  locationLoading,
  onSubmit,
  onUseCurrentLocation,
  relocationZones,
  setZoneForm,
  zoneError,
  zoneForm,
  zoneLoading,
  zoneResult,
}) {
  return (
    <article className="panel">
      <h2>Best Zone To Wait</h2>
      <form className="form-grid" onSubmit={onSubmit}>
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
          <button
            type="button"
            className="secondary-button"
            onClick={onUseCurrentLocation}
            disabled={locationLoading}
          >
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
              Inputs used: {zoneResult.current_zone}, {dayOptions[activeDayIndex]}, {activeTimeLabel}
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
  );
}

export default RelocationPlanner;

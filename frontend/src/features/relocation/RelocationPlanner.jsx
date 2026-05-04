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
  function isStayPutOption(item) {
    return Number(item?.travel_minutes ?? 0) <= 0.05;
  }

  function displayNetIncrease(item) {
    if (isStayPutOption(item)) {
      return "$0.00";
    }
    const value = Number(item?.net_score ?? 0);
    const amount = Math.abs(value).toFixed(2);
    return value < 0 ? `-$${amount}` : `+$${amount}`;
  }

  function explanationLines(text, item) {
    if (isStayPutOption(item)) {
      return [
        `${item.zone} is your current zone, so staying here requires no travel time.`,
        "This reflects overall market activity across all drivers, not individual driver earnings.",
        `Your adjusted earning exposure for the rest of the hour remains approximately $${Number(item.predicted_hourly_earnings ?? 0).toFixed(2)}.`,
      ];
    }
    return text.split("\n");
  }

  function renderExplanation(text, item) {
    return explanationLines(text, item).map((line) => (
      <p key={line}>{line}</p>
    ));
  }

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
            <div>
              {renderExplanation(zoneResult.driver_message, {
                zone: zoneResult.recommended_zone,
                travel_minutes: zoneResult.travel_minutes,
                predicted_hourly_earnings: zoneResult.predicted_hourly_earnings,
              })}
            </div>
            <p>
              Travel time: <strong>{zoneResult.travel_minutes} minutes</strong>
            </p>
            <p>
              Net change after relocating: <strong>{displayNetIncrease(zoneResult.top_alternatives[0])}/hr</strong>
            </p>
            <p>
              Adjusted earning exposure: <strong>${zoneResult.predicted_hourly_earnings}</strong>
            </p>
            <p>Current zone: {zoneResult.current_zone}</p>
            <p>
              Inputs used: {zoneResult.current_zone}, {dayOptions[activeDayIndex]}, {activeTimeLabel}
            </p>
            <details className="see-more-dropdown">
              <summary>See more</summary>
              <div className="see-more-content">
                <p>Top options right now:</p>
                <ul>
                  {zoneResult.top_alternatives.map((item) => (
                    <li key={item.zone}>
                    <strong>{item.zone}</strong>
                    <p>
                      Travel time: <strong>{item.travel_minutes} minutes</strong>
                    </p>
                      <p>
                        Net change after relocating: <strong>{displayNetIncrease(item)}/hr</strong>
                      </p>
                    <p>
                      Adjusted earning exposure: <strong>${item.predicted_hourly_earnings}</strong>
                    </p>
                    <div>{renderExplanation(item.explanation, item)}</div>
                  </li>
                ))}
              </ul>
              </div>
            </details>
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

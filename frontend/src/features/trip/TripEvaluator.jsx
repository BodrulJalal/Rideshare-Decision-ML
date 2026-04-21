function TripEvaluator({
  activeDayIndex,
  activeTimeLabel,
  dayOptions,
  onSubmit,
  onUseCurrentLocation,
  setTripForm,
  tripError,
  tripForm,
  tripLoading,
  tripLocationLoading,
  tripMinutePresets,
  tripResult,
  tripTypes,
  tripZones,
}) {
  return (
    <article className="panel single-panel">
      <h2>Evaluate Offered Trip</h2>
      <form className="form-grid" onSubmit={onSubmit}>
        <div className="time-presets">
          <span className="time-presets-label">Ride type</span>
          <div className="time-preset-buttons">
            {tripTypes.map((tripType) => (
              <button
                key={tripType}
                type="button"
                className={`secondary-button time-preset-button ${tripForm.trip_type === tripType ? "active" : ""}`}
                onClick={() => setTripForm({ ...tripForm, trip_type: tripType })}
              >
                {tripType}
              </button>
            ))}
          </div>
        </div>
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
        <div className="location-picker">
          <span className="location-label">Pickup zone from current location</span>
          <button
            type="button"
            className="secondary-button"
            onClick={onUseCurrentLocation}
            disabled={tripLocationLoading}
          >
            {tripLocationLoading ? "Finding pickup zone..." : "Use current location"}
          </button>
        </div>
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
        <div className="time-presets">
          <span className="time-presets-label">Quick trip lengths</span>
          <div className="time-preset-buttons">
            {tripMinutePresets.map((minutes) => (
              <button
                key={minutes}
                type="button"
                className={`secondary-button time-preset-button ${tripForm.trip_minutes === minutes ? "active" : ""}`}
                onClick={() => setTripForm({ ...tripForm, trip_minutes: minutes })}
              >
                {minutes} min
              </button>
            ))}
          </div>
        </div>
        <button type="submit">{tripLoading ? "Predicting destination..." : "Predict dropoff zone"}</button>
      </form>
      <div className={`result-card ${!tripResult && !tripError ? "muted" : ""}`}>
        {tripError && <p>{tripError}</p>}
        {tripResult && (
          <>
            <strong>{tripResult.predicted_dropoff_zone}</strong>
            <p>{tripResult.driver_message}</p>
            <div className="pill">
              {(tripResult.prediction_confidence * 100).toFixed(1)}% confidence
            </div>
            <p>Most likely dropoff areas:</p>
            <ul>
              {tripResult.top_dropoff_zones.map((item) => (
                <li key={item.zone}>
                  <strong>{item.zone}</strong>: {(item.probability * 100).toFixed(1)}%
                </li>
              ))}
            </ul>
            <p>
              Inputs used: {tripResult.trip_type}, {tripResult.pickup_zone}, {tripResult.trip_minutes} min,{" "}
              {dayOptions[activeDayIndex]}, {activeTimeLabel}
            </p>
          </>
        )}
        {!tripResult && !tripError && (
          <p>Add the offer details to predict which area this ride is most likely to go to.</p>
        )}
      </div>
    </article>
  );
}

export default TripEvaluator;

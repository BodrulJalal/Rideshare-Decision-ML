function TimeSettingsPanel({
  dayOptions,
  timeOptions,
  timeOverride,
  useCustomTime,
  onTimeOverrideChange,
  onUseCustomTimeChange,
}) {
  return (
    <section className="panel time-panel">
      <div className="time-panel-header">
        <h2>Time Settings</h2>
        <label>
          <input
            type="checkbox"
            checked={useCustomTime}
            onChange={(event) => onUseCustomTimeChange(event.target.checked)}
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
              onChange={(event) =>
                onTimeOverrideChange({ ...timeOverride, day_of_week: event.target.value })
              }
            >
              {dayOptions.map((day, index) => (
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
              onChange={(event) => onTimeOverrideChange({ ...timeOverride, hour: event.target.value })}
            >
              {timeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
    </section>
  );
}

export default TimeSettingsPanel;

export const DAY_OPTIONS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export const TIME_OPTIONS = Array.from({ length: 24 }, (_, hour) => ({
  value: String(hour),
  label: new Date(2024, 0, 1, hour).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }),
}));

export const TRIP_MINUTE_PRESETS = ["5", "10", "15", "20", "30", "45", "60"];

export const defaultZoneForm = {
  current_zone: "",
  locationLabel: "",
  latitude: null,
  longitude: null,
};

export const defaultTripForm = {
  pickup_zone: "",
  trip_type: "",
  trip_minutes: "",
};

export function createDefaultTimeOverride() {
  return {
    day_of_week: String((new Date().getDay() + 6) % 7),
    hour: String(new Date().getHours()),
  };
}

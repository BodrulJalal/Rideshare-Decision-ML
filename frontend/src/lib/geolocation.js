const DEFAULT_LOCATION_OPTIONS = {
  enableHighAccuracy: true,
  timeout: 10000,
  maximumAge: 60000,
};

export function getCurrentPosition() {
  return new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, DEFAULT_LOCATION_OPTIONS);
  });
}

export function getGeolocationErrorMessage(error) {
  return error?.code === error?.PERMISSION_DENIED || error?.code === 1
    ? "Location access was denied."
    : "Unable to get your current location.";
}

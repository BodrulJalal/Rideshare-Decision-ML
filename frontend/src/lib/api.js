export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export function buildApiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

export async function fetchJson(path) {
  const response = await fetch(buildApiUrl(path));
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong.");
  }

  return data;
}

export async function postJson(path, payload) {
  const response = await fetch(buildApiUrl(path), {
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

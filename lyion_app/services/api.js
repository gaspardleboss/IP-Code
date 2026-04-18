// =============================================================================
// api.js — All backend API calls for the Ly-ion mobile app.
// Change BACKEND_URL to point to your deployed backend.
// =============================================================================

import { getToken } from "./auth";

// ---- Change this to your deployed backend URL ----
export const BACKEND_URL = "https://your-backend-url.com";

// ---------------------------------------------------------------------------
// Base fetch wrapper with JWT injection
// ---------------------------------------------------------------------------
async function apiFetch(path, options = {}) {
  const token = await getToken();
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers,
  });

  const json = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(json.error || `HTTP ${response.status}`);
  }
  return json;
}

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------

/**
 * Login with student number and password.
 * Returns { access_token, refresh_token, student }.
 */
export async function login(studentNumber, password) {
  return apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ student_number: studentNumber, password }),
  });
}

/**
 * Register the student's RFID card UID (obtained from locker tap).
 */
export async function registerCard(cardUid) {
  return apiFetch("/api/auth/register-card", {
    method: "POST",
    body: JSON.stringify({ card_uid: cardUid }),
  });
}

// ---------------------------------------------------------------------------
// Slots
// ---------------------------------------------------------------------------

/**
 * Fetch all 24 slot states for a given station.
 * Returns { station_id, slots: [...] }.
 */
export async function fetchSlots(stationId) {
  return apiFetch(`/api/slots/${stationId}`);
}

// ---------------------------------------------------------------------------
// Rental
// ---------------------------------------------------------------------------

/**
 * Request a rental from a station.
 * Returns { slot, session_id, battery_charge }.
 */
export async function requestRent(stationId) {
  return apiFetch("/api/rent", {
    method: "POST",
    body: JSON.stringify({ station_id: stationId }),
  });
}

/**
 * Return a battery by providing session or slot info.
 */
export async function returnBattery(stationId, slotId) {
  return apiFetch("/api/return", {
    method: "POST",
    body: JSON.stringify({ station_id: stationId, slot_id: slotId }),
  });
}

// ---------------------------------------------------------------------------
// Profile / history
// ---------------------------------------------------------------------------

export async function fetchProfile() {
  return apiFetch("/api/auth/profile");
}

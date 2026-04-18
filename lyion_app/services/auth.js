// =============================================================================
// auth.js — JWT storage, retrieval, and refresh logic.
// Uses expo-secure-store for encrypted token persistence.
// =============================================================================

import * as SecureStore from "expo-secure-store";
import { BACKEND_URL } from "./api";

const ACCESS_TOKEN_KEY  = "lyion_access_token";
const REFRESH_TOKEN_KEY = "lyion_refresh_token";
const STUDENT_KEY       = "lyion_student";

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

export async function saveTokens(accessToken, refreshToken) {
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY,  accessToken);
  await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
}

export async function getToken() {
  return await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
}

export async function clearTokens() {
  await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
  await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  await SecureStore.deleteItemAsync(STUDENT_KEY);
}

// ---------------------------------------------------------------------------
// Student profile cache
// ---------------------------------------------------------------------------

export async function saveStudent(student) {
  await SecureStore.setItemAsync(STUDENT_KEY, JSON.stringify(student));
}

export async function getStudent() {
  const raw = await SecureStore.getItemAsync(STUDENT_KEY);
  return raw ? JSON.parse(raw) : null;
}

// ---------------------------------------------------------------------------
// Token refresh
// ---------------------------------------------------------------------------

export async function refreshAccessToken() {
  const refreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  if (!refreshToken) return null;

  const response = await fetch(`${BACKEND_URL}/api/auth/refresh`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${refreshToken}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    await clearTokens();   // Refresh token expired — force re-login
    return null;
  }

  const { access_token } = await response.json();
  await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, access_token);
  return access_token;
}

// ---------------------------------------------------------------------------
// Auth state check
// ---------------------------------------------------------------------------

export async function isLoggedIn() {
  const token = await getToken();
  return !!token;
}

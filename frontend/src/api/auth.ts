import { API_BASE_URL } from "./client";

const ACCESS_KEY = "sabha_access";
const REFRESH_KEY = "sabha_refresh";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export async function signup(email: string, password: string) {
  const { access, refresh, is_staff } = await rawAuthRequest<{ access: string; refresh: string; is_staff: boolean }>(
    "/auth/signup/",
    { email, password }
  );
  setTokens(access, refresh);
  return { access, refresh, is_staff };
}

export async function login(email: string, password: string) {
  const { access, refresh, is_staff } = await rawAuthRequest<{ access: string; refresh: string; is_staff: boolean }>(
    "/auth/login/",
    { email, password }
  );
  setTokens(access, refresh);
  return { access, refresh, is_staff };
}

export async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return null;
  try {
    const { access, refresh: newRefresh } = await rawAuthRequest<{ access: string; refresh: string }>(
      "/auth/login/refresh/",
      { refresh }
    );
    setTokens(access, newRefresh);
    return access;
  } catch {
    clearTokens();
    return null;
  }
}

export async function logout() {
  clearTokens();
}

async function rawAuthRequest<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let parsed: unknown = null;
    try { parsed = await response.json(); } catch { /* no JSON body */ }
    const err: any = new Error(`Auth request failed with status ${response.status}`);
    err.status = response.status;
    err.body = parsed;
    throw err;
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

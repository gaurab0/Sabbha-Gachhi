import { API_BASE_URL, apiRequest } from "./client";

const ACCESS_KEY = "sabha_access";
const REFRESH_KEY = "sabha_refresh";

export interface AuthTokens {
  access: string;
  refresh: string;
  email: string;
  email_verified: boolean;
  phone_verified: boolean;
  is_staff: boolean;
}

export interface MeResponse {
  email: string;
  email_verified: boolean;
  email_verified_at: string | null;
  is_staff: boolean;
  has_pending_email: boolean;
  phone_verified: boolean;
  phone_verified_at: string | null;
  phone_masked: string | null;
  phone_country: string | null;
  verification_method: "link" | "otp";
}

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

export async function signup(email: string, password: string): Promise<AuthTokens> {
  const data = await rawAuthRequest<AuthTokens>("/auth/signup/", { email, password });
  setTokens(data.access, data.refresh);
  return data;
}

export async function login(email: string, password: string): Promise<AuthTokens> {
  const data = await rawAuthRequest<AuthTokens>("/auth/login/", { email, password });
  setTokens(data.access, data.refresh);
  return data;
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

/**
 * OTP: { code } ("otp" accepted too). Legacy link: { token }.
 * Requires auth — you can only verify your own address. OTP success returns
 * no tokens, so we refresh afterwards to pick up the fresh verified claim.
 */
export async function verifyEmail(
  payload: { token: string } | { code: string } | { otp: string }
) {
  const data = await apiRequest<{ detail: string; access?: string; refresh?: string }>(
    "/auth/verify-email/",
    { method: "POST", body: JSON.stringify(payload) }
  );
  if (data.access && data.refresh) {
    // Legacy link path still returns fresh tokens.
    setTokens(data.access, data.refresh);
  } else {
    await refreshAccessToken();
  }
  return data;
}

/**
 * Resend to your own address. 200 { detail, cooldown_seconds };
 * 429 { code, retry_after_seconds } surfaces via err.body.
 */
export async function resendVerification(channel: string = "email") {
  return apiRequest<{ detail: string; cooldown_seconds: number }>(
    "/auth/resend-verification/",
    { method: "POST", body: JSON.stringify({ channel }) }
  );
}

export async function fetchMe(): Promise<MeResponse> {
  return apiRequest<MeResponse>("/auth/me/");
}

export interface PhoneVerifyResult {
  message: string;
  phone_verified: boolean;
  phone_masked: string;
  phone_country: string | null;
  access: string;
  refresh: string;
}

/** Start phone verification. Server parses/normalizes; prefer E.164. */
export async function startPhoneVerification(payload: {
  e164?: string;
  country_code?: string;
  national_number?: string;
  channel?: "sms" | "whatsapp" | "voice";
}) {
  return apiRequest<{ message: string }>("/auth/phone/start/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyPhone(code: string) {
  const data = await rawAuthRequest<PhoneVerifyResult>("/auth/phone/verify/", { code });
  setTokens(data.access, data.refresh);
  return data;
}

export async function resendPhoneOtp(channel: "sms" | "whatsapp" | "voice" = "sms") {
  return apiRequest<{ message: string }>("/auth/phone/resend/", {
    method: "POST",
    body: JSON.stringify({ channel }),
  });
}

export async function changePhone(
  payload: { e164?: string; country_code?: string; national_number?: string },
  currentPassword: string
) {
  return apiRequest<{ message: string; pending_phone_masked: string }>(
    "/auth/phone/change/",
    {
      method: "POST",
      body: JSON.stringify({ ...payload, current_password: currentPassword }),
    }
  );
}

export async function changeEmail(newEmail: string, currentPassword: string) {
  return apiRequest<{ message: string; pending_email_masked: string }>(
    "/auth/email/change/",
    {
      method: "POST",
      body: JSON.stringify({ new_email: newEmail, current_password: currentPassword }),
    }
  );
}

export async function logout() {
  try {
    await apiRequest("/auth/logout/", { method: "POST" });
  } catch {
    // Server logout is best-effort; tokens are client-stored.
  }
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

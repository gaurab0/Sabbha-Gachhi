export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

/**
 * Absolute URL for a backend-hosted asset (e.g. an uploaded candidate photo).
 * Photo URLs are stored relative (`/media/...`); a bare `/media/...` in an
 * <img src> would resolve against the frontend origin, not the API, so we
 * prefix the API origin. Absolute http(s)/data URLs are returned untouched.
 */
export function resolveMediaUrl(url: string | null | undefined): string {
  if (!url) return "";
  if (/^(https?:|data:|blob:)/i.test(url)) return url;
  const origin = /^[a-z][a-z0-9+.-]*:\/\//i.test(API_BASE_URL)
    ? new URL(API_BASE_URL).origin
    : window.location.origin;
  return `${origin}${url.startsWith("/") ? "" : "/"}${url}`;
}

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    super(`API request failed with status ${status}`);
    this.status = status;
    this.body = body;
  }
}

let refreshing: Promise<string | null> | null = null;

function getStoredAccessToken(): string | null {
  try { return localStorage.getItem("sabha_access"); } catch { return null; }
}

async function refreshToken(): Promise<string | null> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    const refresh = localStorage.getItem("sabha_refresh");
    if (!refresh) return null;
    try {
      const response = await fetch(`${API_BASE_URL}/auth/login/refresh/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });
      if (!response.ok) {
        localStorage.removeItem("sabha_access");
        localStorage.removeItem("sabha_refresh");
        return null;
      }
      const data = await response.json() as { access: string; refresh: string };
      localStorage.setItem("sabha_access", data.access);
      localStorage.setItem("sabha_refresh", data.refresh);
      return data.access;
    } catch {
      localStorage.removeItem("sabha_access");
      localStorage.removeItem("sabha_refresh");
      return null;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const access = getStoredAccessToken();
  // FormData must set its own multipart boundary — never force JSON here, or
  // the browser/DRF will fail to parse the upload.
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers as Record<string, string> || {}),
    ...(access ? { Authorization: `Bearer ${access}` } : {}),
  };

  let response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    const newAccess = await refreshToken();
    if (newAccess) {
      const retryHeaders: Record<string, string> = {
        ...headers,
        Authorization: `Bearer ${newAccess}`,
      };
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: retryHeaders,
      });
    } else {
      window.location.href = "/login";
      throw new ApiError(401, null);
    }
  }

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // no JSON body, that's fine
    }
    // Unverified users hold valid JWTs but may not use protected routes.
    // Send them to the verify screen instead of failing silently.
    const code = (body as { code?: string } | null)?.code;
    if (response.status === 403 && (code === "email_not_verified" || code === "EMAIL_NOT_VERIFIED")) {
      if (!window.location.pathname.startsWith("/verify-email")) {
        window.location.href = "/verify-email";
      }
    }
    // Email check runs first server-side, so either code maps to its own page.
    if (response.status === 403 && (code === "phone_not_verified" || code === "PHONE_NOT_VERIFIED")) {
      if (!window.location.pathname.startsWith("/verify-phone")) {
        window.location.href = "/verify-phone";
      }
    }
    throw new ApiError(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

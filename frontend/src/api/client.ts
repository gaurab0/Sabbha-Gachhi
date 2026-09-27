export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

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
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
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
    throw new ApiError(response.status, body);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

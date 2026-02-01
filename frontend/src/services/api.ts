const API_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

export const LOGO_URL =
  "https://s3.ru1.storage.beget.cloud/00bd59427133-s3bot/photo_2025-01-16_19-20-18.jpg";

function getTelegramInitData(): string | undefined {
  return window.Telegram?.WebApp?.initData;
}

function getSessionToken(): string | null {
  return localStorage.getItem("birka_session_token");
}

function buildAuthHeaders(): Record<string, string> {
  const initData = getTelegramInitData();
  const sessionToken = getSessionToken();
  return {
    ...(sessionToken ? { "X-Session-Token": sessionToken } : {}),
    ...(initData && !sessionToken ? { "X-Telegram-Init-Data": initData } : {}),
  };
}

async function handleJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `API error: ${response.status}`;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") {
        message = data.detail;
      }
    } catch {
      // ignore parse errors
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
      ...(options?.headers ?? {}),
    },
    ...options,
  });
  return handleJsonResponse<T>(response);
}

async function apiForm<T>(path: string, formData: FormData, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      ...buildAuthHeaders(),
      ...(options?.headers ?? {}),
    },
    body: formData,
    method: "POST",
    ...options,
  });
  return handleJsonResponse<T>(response);
}

async function apiFile(path: string, options?: RequestInit): Promise<{ blob: Blob; filename: string | null }> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      ...buildAuthHeaders(),
      ...(options?.headers ?? {}),
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  const contentDisposition = response.headers.get("content-disposition");
  const match = contentDisposition?.match(/filename="?([^"]+)"?/);
  return { blob: await response.blob(), filename: match?.[1] ?? null };
}

export const apiClient = { api, apiForm, apiFile };

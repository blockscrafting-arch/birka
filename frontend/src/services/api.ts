const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

function getTelegramInitData(): string | undefined {
  return window.Telegram?.WebApp?.initData;
}

function getSessionToken(): string | null {
  return localStorage.getItem("birka_session_token");
}

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const initData = getTelegramInitData();
  const sessionToken = getSessionToken();
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(sessionToken ? { "X-Session-Token": sessionToken } : {}),
      ...(initData && !sessionToken ? { "X-Telegram-Init-Data": initData } : {}),
      ...(options?.headers ?? {}),
    },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const apiClient = { api };

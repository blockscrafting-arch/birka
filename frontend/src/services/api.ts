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

function handleUnauthorized(): void {
  localStorage.removeItem("birka_session_token");
  const message = "Сессия истекла. Откройте приложение заново.";
  if (typeof window !== "undefined" && window.Telegram?.WebApp?.showAlert) {
    window.Telegram.WebApp.showAlert(message);
  }
}

async function handleJsonResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) {
    handleUnauthorized();
  }
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
    if (response.status === 401) {
      handleUnauthorized();
    }
    let message = `API error: ${response.status}`;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") message = data.detail;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  const contentDisposition = response.headers.get("content-disposition");
  let filename: string | null = null;
  if (contentDisposition) {
    const matchStar = contentDisposition.match(/filename\*=(?:UTF-8'')?([^;]+)/i);
    if (matchStar?.[1]) {
      filename = decodeURIComponent(matchStar[1].trim().replace(/^"|"$/g, ""));
    } else {
      const match = contentDisposition.match(/filename="?([^"]+)"?/i);
      filename = match?.[1] ?? null;
    }
  }
  return { blob: await response.blob(), filename };
}

/** Download file (PDF/Excel) with fallbacks for mobile and Telegram WebApp. */
export async function downloadFile(path: string, fallbackFilename: string): Promise<void> {
  const { blob, filename } = await apiFile(path);
  const url = URL.createObjectURL(blob);

  if (typeof window !== "undefined" && window.Telegram?.WebApp?.openLink && blob.size < 5 * 1024 * 1024) {
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
      });
      window.Telegram.WebApp.openLink(dataUrl);
      setTimeout(() => URL.revokeObjectURL(url), 100);
      return;
    } catch {
      /* openLink may not support data URLs; fall through to window.open */
    }
  }

  const opened = window.open(url, "_blank");
  if (!opened) {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename ?? fallbackFilename;
    link.click();
  }
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

export const apiClient = { api, apiForm, apiFile };

const API_URL = import.meta.env.VITE_API_URL ?? "/api/v1";

const RETRYABLE_STATUSES = [502, 503, 504];
const RETRY_DELAYS_MS = [1000, 2000];

async function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

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

async function api<T>(path: string, options?: RequestInit, retriesLeft = RETRY_DELAYS_MS.length): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...buildAuthHeaders(),
      ...(options?.headers ?? {}),
    },
    ...options,
  });
  if (
    RETRYABLE_STATUSES.includes(response.status) &&
    retriesLeft > 0
  ) {
    await delay(RETRY_DELAYS_MS[RETRY_DELAYS_MS.length - retriesLeft]);
    return api(path, options, retriesLeft - 1);
  }
  return handleJsonResponse<T>(response);
}

/** POST FormData. Retry не используется: body потребляется после первого fetch. */
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

/**
 * Отправка FormData с отслеживанием прогресса загрузки (через XHR).
 * onProgress вызывается с 0–100 (приближённо по загруженным байтам).
 * При 502/503/504 выполняется повтор запроса с задержкой.
 */
function apiFormWithProgress<T>(
  path: string,
  formData: FormData,
  onProgress?: (percent: number) => void,
  retriesLeft = RETRY_DELAYS_MS.length
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const url = `${API_URL}${path}`;
    const auth = buildAuthHeaders();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status === 401) {
        handleUnauthorized();
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        const retryable = RETRYABLE_STATUSES.includes(xhr.status) && retriesLeft > 0;
        if (retryable) {
          delay(RETRY_DELAYS_MS[RETRY_DELAYS_MS.length - retriesLeft])
            .then(() =>
              apiFormWithProgress(path, formData, onProgress, retriesLeft - 1)
            )
            .then(resolve, reject);
          return;
        }
        let message = `API error: ${xhr.status}`;
        try {
          const data = JSON.parse(xhr.responseText);
          if (typeof data?.detail === "string") message = data.detail;
        } catch {
          // ignore
        }
        reject(new Error(message));
        return;
      }
      try {
        const data = xhr.responseText ? (JSON.parse(xhr.responseText) as T) : ({} as T);
        resolve(data);
      } catch {
        reject(new Error("Invalid JSON response"));
      }
    });

    xhr.addEventListener("error", () => {
      if (retriesLeft > 0) {
        delay(RETRY_DELAYS_MS[RETRY_DELAYS_MS.length - retriesLeft])
          .then(() => apiFormWithProgress(path, formData, onProgress, retriesLeft - 1))
          .then(resolve, reject);
      } else {
        reject(new Error("Network error"));
      }
    });
    xhr.addEventListener("abort", () => reject(new Error("Request aborted")));

    xhr.open("POST", url);
    Object.entries(auth).forEach(([key, value]) => xhr.setRequestHeader(key, value));
    xhr.send(formData);
  });
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

export const apiClient = { api, apiForm, apiFormWithProgress, apiFile };

/**
 * Yandex Metrika: инициализация и события воронки.
 * В production сборке VITE_YM_COUNTER_ID обязателен; при отсутствии в консоль пишется ошибка.
 */
declare global {
  interface Window {
    ym?: (id: number, action: string, target?: string | Record<string, unknown>, params?: Record<string, unknown>) => void;
  }
}

const COUNTER_ID = import.meta.env.VITE_YM_COUNTER_ID;
const IS_PROD = import.meta.env.PROD;

let metrikaId: number | null = null;

export function initAnalytics(): void {
  if (!COUNTER_ID || typeof COUNTER_ID !== "string") {
    if (IS_PROD) {
      console.error("[Birka] В production задайте VITE_YM_COUNTER_ID при сборке для аналитики.");
    }
    return;
  }
  const id = parseInt(COUNTER_ID, 10);
  if (Number.isNaN(id)) {
    if (IS_PROD) {
      console.error("[Birka] VITE_YM_COUNTER_ID должен быть числом.");
    }
    return;
  }
  metrikaId = id;

  const script = document.createElement("script");
  script.async = true;
  script.src = "https://mc.yandex.ru/metrika/tag.js";
  script.onload = () => {
    if (window.ym) {
      window.ym(id, "init", { clickmap: true, trackLinks: true, accurateTrackBounce: true, webvisor: true });
      reachGoal("app_init");
    }
  };
  document.head.appendChild(script);
}

/**
 * Отправить цель/событие в Метрику. Безопасно вызывать при отсутствии счётчика (no-op).
 */
export function reachGoal(name: string, params?: Record<string, unknown>): void {
  if (metrikaId == null || typeof window.ym !== "function") return;
  try {
    window.ym(metrikaId, "reachGoal", name, params);
  } catch {
    // игнорируем ошибки отправки
  }
}

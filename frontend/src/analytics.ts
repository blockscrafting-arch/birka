/**
 * Yandex Metrika: инициализация при наличии счётчика в env.
 * Задайте VITE_YM_COUNTER_ID при сборке, чтобы включить аналитику.
 */
declare global {
  interface Window {
    ym?: (id: number, action: string, params?: Record<string, unknown>) => void;
  }
}

const COUNTER_ID = import.meta.env.VITE_YM_COUNTER_ID;

export function initAnalytics(): void {
  if (!COUNTER_ID || typeof COUNTER_ID !== "string") return;
  const id = parseInt(COUNTER_ID, 10);
  if (Number.isNaN(id)) return;

  const script = document.createElement("script");
  script.async = true;
  script.src = "https://mc.yandex.ru/metrika/tag.js";
  script.onload = () => {
    if (window.ym) {
      window.ym(id, "init", { clickmap: true, trackLinks: true, accurateTrackBounce: true, webvisor: true });
    }
  };
  document.head.appendChild(script);
}

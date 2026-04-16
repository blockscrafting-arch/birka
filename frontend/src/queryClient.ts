import { QueryCache, QueryClient } from "@tanstack/react-query";

/** Глобальный обработчик ошибок запросов/мутаций: избегаем unhandled promise rejection. */
function onQueryError(error: unknown): void {
  if (typeof window === "undefined") return;
  const message = "Не удалось выполнить действие. Попробуйте ещё раз.";
  if (window.Telegram?.WebApp?.showAlert) {
    window.Telegram.WebApp.showAlert(message);
  } else {
    console.error("[Birka] Query error:", error);
  }
}

/** Общий экземпляр React Query для инвалидации кэша из App (например после auth/telegram). */
export const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: onQueryError }),
});

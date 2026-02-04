import { QueryClient } from "@tanstack/react-query";

/** Общий экземпляр React Query для инвалидации кэша из App (например после auth/telegram). */
export const queryClient = new QueryClient();

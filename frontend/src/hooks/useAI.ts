import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";

type AIChatResponse = {
  answer: string;
};

type AIChatPayload = {
  message: string;
  company_id?: number | null;
};

type ChatMessageOut = { role: string; text: string };

type AIChatHistoryResponse = {
  messages: ChatMessageOut[];
};

/** Load chat history from server (sync across devices). */
export function useAIHistory(companyId: number | null) {
  const params = new URLSearchParams();
  if (companyId != null) params.set("company_id", String(companyId));
  const queryString = params.toString();
  const path = queryString ? `/ai/history?${queryString}` : "/ai/history";
  return useQuery({
    queryKey: ["ai", "history", companyId ?? "global"],
    queryFn: () => apiClient.api<AIChatHistoryResponse>(path),
  });
}

/** Clear chat history on server. */
export function useClearAIHistory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (companyId: number | null) => {
      const params = new URLSearchParams();
      if (companyId != null) params.set("company_id", String(companyId));
      const qs = params.toString();
      return apiClient.api<{ status: string }>(qs ? `/ai/history?${qs}` : "/ai/history", {
        method: "DELETE",
      });
    },
    onSuccess: (_, companyId) => {
      queryClient.invalidateQueries({ queryKey: ["ai", "history", companyId ?? "global"] });
    },
  });
}

export function useAIChat() {
  return useMutation({
    mutationFn: (payload: AIChatPayload) =>
      apiClient.api<AIChatResponse>("/ai/chat", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  });
}

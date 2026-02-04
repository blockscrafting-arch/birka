import { useMutation } from "@tanstack/react-query";

import { apiClient } from "../services/api";

type AIChatResponse = {
  answer: string;
};

type AIChatPayload = {
  message: string;
  company_id?: number | null;
  history?: { role: string; text: string }[];
};

export function useAIChat() {
  return useMutation({
    mutationFn: (payload: AIChatPayload) =>
      apiClient.api<AIChatResponse>("/ai/chat", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  });
}

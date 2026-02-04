import { create } from "zustand";
import { persist } from "zustand/middleware";

/** Single message in AI chat history. */
export type ChatMessage = { role: "user" | "assistant"; text: string };

const MAX_MESSAGES_PER_COMPANY = 50;

function companyKey(companyId: number | null): string {
  return companyId !== null && companyId !== undefined ? String(companyId) : "global";
}

type AIChatStore = {
  /** History per company (key = companyId or "global"). */
  histories: Record<string, ChatMessage[]>;
  addMessage: (companyId: number | null, msg: ChatMessage) => void;
  getMessages: (companyId: number | null) => ChatMessage[];
  clearMessages: (companyId: number | null) => void;
};

/** Store for AI chat messages per company; persists in localStorage with size limit. */
export const useAIChatStore = create<AIChatStore>()(
  persist(
    (set, get) => ({
      histories: {},
      addMessage: (companyId, msg) => {
        const key = companyKey(companyId);
        set((s) => {
          const hist = s.histories ?? {};
          const list = [...(hist[key] ?? []), msg];
          const trimmed = list.length > MAX_MESSAGES_PER_COMPANY ? list.slice(-MAX_MESSAGES_PER_COMPANY) : list;
          return { histories: { ...hist, [key]: trimmed } };
        });
      },
      getMessages: (companyId) => {
        const key = companyKey(companyId);
        return get().histories?.[key] ?? [];
      },
      clearMessages: (companyId) => {
        const key = companyKey(companyId);
        set((s) => ({ histories: { ...(s.histories ?? {}), [key]: [] } }));
      },
    }),
    { name: "birka-ai-chat", partialize: (s) => ({ histories: s.histories }) }
  )
);

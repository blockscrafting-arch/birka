import { create } from "zustand";

/** Single message in AI chat history. */
export type ChatMessage = { role: "user" | "assistant"; text: string };

const MAX_MESSAGES_PER_COMPANY = 50;

function companyKey(companyId: number | null): string {
  return companyId !== null && companyId !== undefined ? String(companyId) : "global";
}

type AIChatStore = {
  histories: Record<string, ChatMessage[]>;
  addMessage: (companyId: number | null, msg: ChatMessage) => void;
  getMessages: (companyId: number | null) => ChatMessage[];
  setMessages: (companyId: number | null, messages: ChatMessage[]) => void;
  clearMessages: (companyId: number | null) => void;
};

/** Store for AI chat messages per company. Server is source of truth; no localStorage to avoid stale data across devices. */
export const useAIChatStore = create<AIChatStore>()((set, get) => ({
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
  setMessages: (companyId, messages) => {
    const key = companyKey(companyId);
    set((s) => ({ histories: { ...(s.histories ?? {}), [key]: messages } }));
  },
  clearMessages: (companyId) => {
    const key = companyKey(companyId);
    set((s) => ({ histories: { ...(s.histories ?? {}), [key]: [] } }));
  },
}));

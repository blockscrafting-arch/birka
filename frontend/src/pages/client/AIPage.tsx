import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { Button } from "../../components/ui/Button";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useAIChat, useAIHistory, useClearAIHistory } from "../../hooks/useAI";
import { useQueryClient } from "@tanstack/react-query";
import { useAIChatStore } from "../../stores/aiChatStore";

export function AIPage() {
  const { companyId } = useActiveCompany();
  const { getMessages, addMessage, setMessages, clearMessages } = useAIChatStore();
  const historyQuery = useAIHistory(companyId ?? null);
  const clearHistory = useClearAIHistory();
  const chat = useAIChat();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollDown, setShowScrollDown] = useState(false);
  const lastMessageCountRef = useRef(0);

  const serverLoadedOnce = historyQuery.data !== undefined;
  const messages = serverLoadedOnce ? getMessages(companyId ?? null) : [];

  // Hydrate store from server history when loaded
  useEffect(() => {
    if (historyQuery.data?.messages) {
      const list = historyQuery.data.messages.map((m) => ({ role: m.role as "user" | "assistant", text: m.text }));
      setMessages(companyId ?? null, list);
    }
  }, [historyQuery.data, companyId, setMessages]);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    messagesEndRef.current?.scrollIntoView({ behavior });
    setShowScrollDown(false);
  }, []);

  useEffect(() => {
    if (messages.length > lastMessageCountRef.current || chat.isPending) {
      scrollToBottom();
    }
    lastMessageCountRef.current = messages.length;
  }, [messages.length, chat.isPending, scrollToBottom]);

  const handleScroll = useCallback(() => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    setShowScrollDown(!atBottom);
  }, []);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || chat.isPending) {
      return;
    }

    addMessage(companyId ?? null, { role: "user", text: trimmed });
    setDraft("");

    chat.mutate(
      { message: trimmed, company_id: companyId ?? undefined },
      {
        onSuccess: (data) => {
          addMessage(companyId ?? null, { role: "assistant", text: data.answer });
          queryClient.invalidateQueries({ queryKey: ["ai", "history", companyId ?? "global"] });
        },
        onError: () => {
          addMessage(companyId ?? null, {
            role: "assistant",
            text: "Не удалось получить ответ. Попробуйте позже.",
          });
        },
      }
    );
  };

  const handleClear = () => {
    clearHistory.mutate(companyId ?? null, {
      onSuccess: () => {
        clearMessages(companyId ?? null);
      },
    });
  };

  return (
    <div className="flex min-h-[280px] h-[calc(100vh-9rem)] max-h-[calc(100vh-5rem)] flex-col gap-0">
      <div className="shrink-0 rounded-t-2xl border border-b-0 border-slate-200 bg-white p-4 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">AI-помощник</h2>
            <p className="mt-1 text-sm text-slate-600">
              Спросите про отгрузки, остатки, статусы и документы. История синхронизируется между устройствами.
            </p>
          </div>
          {messages.length > 0 && (
            <Button
              type="button"
              variant="ghost"
              onClick={handleClear}
              disabled={clearHistory.isPending}
            >
              {clearHistory.isPending ? "Очистка…" : "Очистить"}
            </Button>
          )}
        </div>
      </div>

      <div className="relative min-h-[8rem] min-w-0 flex-1">
        <div
          ref={messagesContainerRef}
          onScroll={handleScroll}
          role="log"
          aria-live="polite"
          aria-label="История сообщений"
          className="h-full space-y-3 overflow-y-auto border-x border-slate-200 bg-white p-4"
        >
          {historyQuery.isLoading && !serverLoadedOnce ? (
            <div className="text-sm text-slate-500">Загрузка истории…</div>
          ) : messages.length === 0 ? (
            <div className="text-sm text-slate-500">Сообщений пока нет.</div>
          ) : (
            messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`rounded-xl px-3 py-2 text-sm ${
                  message.role === "user" ? "bg-birka-50 text-slate-900" : "bg-slate-100 text-slate-700"
                }`}
              >
                <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">
                  {message.role === "user" ? "Вы" : "AI"}
                </span>
                <span className="whitespace-pre-wrap break-words">{message.text}</span>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
        {showScrollDown && (
          <Button
            type="button"
            variant="secondary"
            className="absolute bottom-2 left-1/2 -translate-x-1/2 shadow-md"
            onClick={() => scrollToBottom("smooth")}
          >
            Вниз
          </Button>
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="shrink-0 space-y-3 rounded-b-2xl border border-t-0 border-slate-200 bg-white p-4 shadow-soft"
      >
        <label className="block text-sm text-slate-600">
          Сообщение
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 shadow-soft focus:border-birka-500 focus:outline-none focus:ring-2 focus:ring-birka-100"
            rows={2}
            placeholder="Например: какие статусы у последних заявок?"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <Button type="submit" disabled={chat.isPending}>
          {chat.isPending ? "Отправляю..." : "Отправить"}
        </Button>
      </form>
    </div>
  );
}

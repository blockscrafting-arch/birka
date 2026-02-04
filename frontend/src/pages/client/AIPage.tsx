import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import { Button } from "../../components/ui/Button";
import { Toast } from "../../components/ui/Toast";
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
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);
  const lastMessageCountRef = useRef(0);

  const handleCopyMessage = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setToast({ message: "Скопировано в буфер обмена", variant: "success" });
    } catch {
      setToast({ message: "Не удалось скопировать", variant: "error" });
    }
  }, []);

  const serverLoadedOnce = historyQuery.isSuccess || historyQuery.isError;
  const messages = serverLoadedOnce ? getMessages(companyId ?? null) : [];
  const hasLocalMessages = messages.length > 0;

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

  const renderMessage = (message: { role: "user" | "assistant"; text: string }, index: number) => {
    const isUser = message.role === "user";
    return (
      <div
        key={`${message.role}-${index}`}
        className={`rounded-xl px-3 py-2 text-sm ${
          isUser ? "bg-birka-50 text-slate-900" : "bg-slate-100 text-slate-700"
        }`}
      >
        <div className="mb-1 flex items-center justify-between gap-2">
          <span className="text-xs uppercase tracking-wide text-slate-500">
            {isUser ? "Вы" : "AI"}
          </span>
          {!isUser && (
            <button
              type="button"
              onClick={() => handleCopyMessage(message.text)}
              className="rounded p-1 text-slate-500 hover:bg-slate-200 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-slate-400"
              title="Скопировать"
              aria-label="Скопировать сообщение"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          )}
        </div>
        <div className="prose prose-sm prose-slate max-w-none whitespace-pre-wrap break-words prose-p:my-0 prose-ul:my-1">
          <ReactMarkdown remarkPlugins={[remarkBreaks]}>{message.text}</ReactMarkdown>
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-full min-h-0 flex-col gap-0">
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

      <div className="relative min-h-0 min-w-0 flex-1">
        <div
          ref={messagesContainerRef}
          onScroll={handleScroll}
          role="log"
          aria-live="polite"
          aria-label="История сообщений"
          className="h-full space-y-3 overflow-y-auto border-x border-slate-200 bg-white p-4"
        >
          {historyQuery.isLoading && !hasLocalMessages ? (
            <div className="text-sm text-slate-500">Загрузка истории…</div>
          ) : historyQuery.isError ? (
            <>
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                История не загрузилась, показываем локальные сообщения.
              </div>
              {messages.length === 0 ? (
                <div className="text-sm text-slate-500">Сообщений пока нет.</div>
              ) : (
                messages.map((message, index) => renderMessage(message, index))
              )}
            </>
          ) : messages.length === 0 ? (
            <div className="text-sm text-slate-500">Сообщений пока нет.</div>
          ) : (
            messages.map((message, index) => renderMessage(message, index))
          )}
          {chat.isPending && (
            <div className="rounded-xl bg-slate-100 px-3 py-2 text-sm text-slate-700">
              <span className="text-xs uppercase tracking-wide text-slate-500">AI</span>
              <div className="mt-1 flex gap-1">
                <span className="animate-bounce">.</span>
                <span className="animate-bounce [animation-delay:0.2s]">.</span>
                <span className="animate-bounce [animation-delay:0.4s]">.</span>
              </div>
            </div>
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
      {toast ? (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      ) : null}
    </div>
  );
}

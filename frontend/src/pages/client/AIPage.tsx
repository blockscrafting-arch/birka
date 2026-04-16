import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import * as remarkBreaksModule from "remark-breaks";

import { Toast } from "../../components/ui/Toast";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useAIChat, useAIHistory, useClearAIHistory } from "../../hooks/useAI";
import { useQueryClient } from "@tanstack/react-query";
import { useAIChatStore } from "../../stores/aiChatStore";

const MAX_TEXTAREA_ROWS = 5;
const LINE_HEIGHT_PX = 24;

function IconTrash() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}

function IconSend() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
    </svg>
  );
}

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);
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

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const lineCount = (el.value.match(/\n/g)?.length ?? 0) + 1;
    const rows = Math.min(Math.max(1, lineCount), MAX_TEXTAREA_ROWS);
    const minHeight = 48;
    el.style.height = `${Math.max(minHeight, rows * LINE_HEIGHT_PX)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [draft, resizeTextarea]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || chat.isPending) {
      return;
    }

    addMessage(companyId ?? null, { role: "user", text: trimmed });
    setDraft("");
    resizeTextarea();

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

  const stripListPrefix = (line: string) => line.replace(/^(\* {3}|\* |- )\s*/, "");

  const renderMessage = (message: { role: "user" | "assistant"; text: string }, index: number) => {
    const isUser = message.role === "user";
    const raw = message.text ?? "";
    const normalized = isUser
      ? raw
      : (() => {
          const match = raw.match(/\n{2,}/);
          if (match && match.index !== undefined) {
            const first = raw.slice(0, match.index).trimEnd();
            const rest = raw.slice(match.index + match[0].length);
            const restLines = rest.split(/\n+/).filter(Boolean);
            const restMarkdown = restLines.map((line) => `- ${stripListPrefix(line)}`).join("\n");
            return first + "\n\n" + restMarkdown;
          }
          if (raw.includes("\n")) {
            const lines = raw.split(/\n+/).filter(Boolean);
            return lines.map((line) => `- ${stripListPrefix(line)}`).join("\n");
          }
          return raw;
        })();
    return (
      <div
        key={`${message.role}-${index}`}
        className={`flex ${isUser ? "justify-end" : "justify-start"}`}
      >
        <div
          className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
            isUser
              ? "rounded-br-md bg-birka-500 text-white"
              : "rounded-bl-md border border-slate-200 bg-white text-slate-800"
          }`}
        >
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <span className={`text-xs font-medium uppercase tracking-wide ${isUser ? "text-birka-100" : "text-slate-500"}`}>
              {isUser ? "Вы" : "AI"}
            </span>
            {!isUser && (
              <button
                type="button"
                onClick={() => handleCopyMessage(message.text)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-slate-300"
                title="Скопировать"
                aria-label="Скопировать сообщение"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            )}
          </div>
          <div className={`max-w-none break-words leading-relaxed [&_p]:mt-0 [&_p]:mb-2 [&_ul]:list-none [&_ul]:pl-0 [&_ul]:my-0 [&_li]:my-1 ${isUser ? "[&_a]:text-birka-100 [&_a]:underline" : ""}`}>
            <ReactMarkdown remarkPlugins={[remarkBreaksModule.default]}>
              {normalized}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    );
  };

  const emptyState = (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="rounded-full bg-birka-100 p-4 mb-4">
        <svg className="h-10 w-10 text-birka-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </div>
      <p className="text-base font-medium text-slate-700">AI-помощник Бирка</p>
      <p className="mt-1 text-sm text-slate-500 max-w-[260px]">
        Спросите про отгрузки, остатки, статусы заявок или документы. Напишите вопрос ниже.
      </p>
    </div>
  );

  return (
    <div className="flex-1 flex flex-col bg-slate-50 overflow-hidden rounded-t-3xl border-t border-slate-200 shadow-md min-h-0">
      {/* Компактная шапка */}
      <header className="shrink-0 flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3">
        <h2 className="text-base font-semibold text-slate-900 truncate">AI-помощник</h2>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={handleClear}
            disabled={clearHistory.isPending}
            className="shrink-0 rounded-full p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-birka-500 focus:ring-offset-2 disabled:opacity-50"
            title="Очистить историю"
            aria-label="Очистить историю"
          >
            <IconTrash />
          </button>
        )}
      </header>

      {/* Область сообщений */}
      <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
        <div
          ref={messagesContainerRef}
          onScroll={handleScroll}
          role="log"
          aria-live="polite"
          aria-label="История сообщений"
          className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain px-4 py-4"
          style={{ scrollBehavior: "smooth" }}
        >
          {historyQuery.isLoading && !hasLocalMessages ? (
            <div className="flex items-center justify-center py-8 text-sm text-slate-500">
              Загрузка истории…
            </div>
          ) : historyQuery.isError ? (
            <>
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800 mb-4">
                История не загрузилась, показываем локальные сообщения.
              </div>
              {messages.length === 0 ? (
                emptyState
              ) : (
                <div className="space-y-3">
                  {messages.map((message, index) => renderMessage(message, index))}
                </div>
              )}
            </>
          ) : messages.length === 0 ? (
            emptyState
          ) : (
            <div className="space-y-3">
              {messages.map((message, index) => renderMessage(message, index))}
            </div>
          )}
          {chat.isPending && (
            <div className="flex justify-start mt-3">
              <div className="max-w-[85%] rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
                <span className="text-xs font-medium uppercase tracking-wide text-slate-500">AI</span>
                <div className="mt-2 flex gap-1">
                  <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce" />
                  <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:0.2s]" />
                  <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} className="h-2 shrink-0" />
        </div>
        {showScrollDown && (
          <button
            type="button"
            onClick={() => scrollToBottom("smooth")}
            className="absolute bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-md hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-birka-500 focus:ring-offset-2"
            aria-label="Прокрутить вниз"
          >
            Вниз
          </button>
        )}
      </div>

      {/* Поле ввода: авторесайз + круглая кнопка отправки */}
      <form
        onSubmit={handleSubmit}
        className="flex shrink-0 flex-col border-t border-slate-200 bg-white px-4 pt-3 pb-[calc(env(safe-area-inset-bottom,0px)+72px)]"
      >
        <div className="flex items-end gap-2">
          <label className="min-w-0 flex-1">
            <span className="sr-only">Сообщение</span>
            <textarea
              ref={textareaRef}
              className="w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-birka-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-birka-100 min-h-[48px]"
              rows={1}
              placeholder="Напишите вопрос…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  (e.target as HTMLTextAreaElement).form?.requestSubmit();
                }
              }}
            />
          </label>
          <button
            type="submit"
            disabled={chat.isPending || !draft.trim()}
            className="shrink-0 flex items-center justify-center w-12 h-12 rounded-full bg-birka-500 text-white shadow-sm hover:bg-birka-600 focus:outline-none focus:ring-2 focus:ring-birka-500 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none"
            aria-label="Отправить"
          >
            <IconSend />
          </button>
        </div>
      </form>
      {toast ? (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      ) : null}
    </div>
  );
}

import { FormEvent, useState } from "react";

import { Button } from "../../components/ui/Button";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useAIChat } from "../../hooks/useAI";
import { useAIChatStore } from "../../stores/aiChatStore";

export function AIPage() {
  const { companyId } = useActiveCompany();
  const { getMessages, addMessage } = useAIChatStore();
  const messages = getMessages(companyId ?? null);
  const [draft, setDraft] = useState("");
  const chat = useAIChat();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || chat.isPending) {
      return;
    }

    const historyToSend = getMessages(companyId ?? null);
    addMessage(companyId ?? null, { role: "user", text: trimmed });
    setDraft("");

    chat.mutate(
      { message: trimmed, company_id: companyId, history: historyToSend },
      {
        onSuccess: (data) => {
          addMessage(companyId ?? null, { role: "assistant", text: data.answer });
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

  return (
    <div className="flex flex-1 flex-col gap-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        <h2 className="text-lg font-semibold text-slate-900">AI-помощник</h2>
        <p className="mt-1 text-sm text-slate-600">
          Спросите про отгрузки, остатки, статусы и документы. Ответ будет учитываться по активной компании.
        </p>
      </div>

      <div className="flex-1 space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
        {messages.length === 0 ? (
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
              {message.text}
            </div>
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <label className="block text-sm text-slate-600">
          Сообщение
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 shadow-soft focus:border-birka-500 focus:outline-none focus:ring-2 focus:ring-birka-100"
            rows={3}
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

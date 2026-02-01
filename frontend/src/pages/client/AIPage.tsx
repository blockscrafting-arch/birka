import { FormEvent, useState } from "react";

import { Button } from "../../components/ui/Button";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useAIChat } from "../../hooks/useAI";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};

export function AIPage() {
  const { companyId } = useActiveCompany();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const chat = useAIChat();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || chat.isPending) {
      return;
    }

    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setDraft("");

    chat.mutate(
      { message: trimmed, company_id: companyId },
      {
        onSuccess: (data) => {
          setMessages((current) => [...current, { role: "assistant", text: data.answer }]);
        },
        onError: () => {
          setMessages((current) => [
            ...current,
            { role: "assistant", text: "Не удалось получить ответ. Попробуйте позже." },
          ]);
        },
      }
    );
  };

  return (
    <div className="flex flex-1 flex-col gap-4">
      <div className="rounded-2xl border border-slate-800/70 bg-slate-900/40 p-4">
        <h2 className="text-lg font-semibold text-slate-100">AI-помощник</h2>
        <p className="mt-1 text-sm text-slate-400">
          Спросите про отгрузки, остатки, статусы и документы. Ответ будет учитываться по активной компании.
        </p>
      </div>

      <div className="flex-1 space-y-3 rounded-2xl border border-slate-800/70 bg-slate-950/40 p-4">
        {messages.length === 0 ? (
          <div className="text-sm text-slate-500">Сообщений пока нет.</div>
        ) : (
          messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`rounded-xl px-3 py-2 text-sm ${
                message.role === "user" ? "bg-sky-500/20 text-slate-100" : "bg-slate-800/60 text-slate-200"
              }`}
            >
              <span className="mb-1 block text-xs uppercase tracking-wide text-slate-400">
                {message.role === "user" ? "Вы" : "AI"}
              </span>
              {message.text}
            </div>
          ))
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <label className="block text-sm text-slate-300">
          Сообщение
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sky-400 focus:outline-none"
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

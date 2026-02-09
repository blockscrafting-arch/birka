import { useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Toast } from "../../components/ui/Toast";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { apiClient } from "../../services/api";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
};

export function AiChatPage() {
  const { data: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);
    try {
      const response = await apiClient.api<{ answer: string }>("/ai/chat", {
        method: "POST",
        body: JSON.stringify({ message: text, company_id: activeCompanyId ?? undefined }),
      });
      setMessages((prev) => [...prev, { role: "assistant", text: response.answer }]);
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Не удалось получить ответ", variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[70vh] flex-col gap-3">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-slate-800 bg-slate-900/60 p-4">
        {messages.length === 0 ? (
          <div className="text-sm text-slate-400">Задайте вопрос о заказах, остатках или процессе.</div>
        ) : null}
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
              message.role === "user"
                ? "ml-auto bg-slate-100 text-slate-900"
                : "bg-slate-800 text-slate-100"
            }`}
          >
            {message.text}
          </div>
        ))}
      </div>
      <div className="flex items-end gap-2">
        <textarea
          className="min-h-[72px] flex-1 resize-none rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-sm text-slate-100 placeholder:text-slate-500"
          placeholder="Напишите запрос для AI..."
          value={input}
          onChange={(event) => setInput(event.target.value)}
        />
        <Button onClick={handleSend} disabled={loading}>
          {loading ? "Отправка..." : "Отправить"}
        </Button>
      </div>
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Toast } from "../../components/ui/Toast";
import { apiClient } from "../../services/api";

const POPULAR_MODELS = [
  { provider: "openai", model: "gpt-4o-mini", label: "OpenAI GPT-4o mini" },
  { provider: "openai", model: "gpt-4o", label: "OpenAI GPT-4o" },
  { provider: "openrouter", model: "openai/gpt-4o-mini", label: "OpenRouter: GPT-4o mini" },
  { provider: "openrouter", model: "openai/gpt-4o", label: "OpenRouter: GPT-4o" },
  { provider: "openrouter", model: "anthropic/claude-3.5-sonnet", label: "OpenRouter: Claude 3.5 Sonnet" },
  { provider: "openrouter", model: "anthropic/claude-3-haiku", label: "OpenRouter: Claude 3 Haiku" },
];

export function AISettingsPage() {
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useQuery({
    queryKey: ["admin", "ai-settings"],
    queryFn: () => apiClient.api<{ provider: string; model: string; temperature: number }>("/admin/ai-settings"),
  });
  const [provider, setProvider] = useState(settings?.provider ?? "openai");
  const [model, setModel] = useState(settings?.model ?? "gpt-4o-mini");
  const [temperature, setTemperature] = useState("0.7");
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  useEffect(() => {
    if (!settings) return;
    setProvider(settings.provider);
    setModel(settings.model);
    setTemperature(String(settings.temperature));
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: (payload: { provider?: string; model?: string; temperature?: number }) =>
      apiClient.api<{ provider: string; model: string; temperature: number }>("/admin/ai-settings", {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: (data) => {
      setProvider(data.provider);
      setModel(data.model);
      setTemperature(String(data.temperature));
      queryClient.setQueryData(["admin", "ai-settings"], data);
      setToast({ message: "Настройки сохранены" });
    },
    onError: (err) => setToast({ message: err?.message ?? "Ошибка сохранения", variant: "error" }),
  });

  const testMutation = useMutation({
    mutationFn: () =>
      apiClient.api<{ ok: boolean; reply?: string }>("/admin/ai-settings/test", { method: "POST" }),
    onSuccess: (data) => {
      if (data.ok) setToast({ message: `Тест: ${data.reply ?? "ответ получен"}` });
      else setToast({ message: "Ошибка теста", variant: "error" });
    },
    onError: (err) => setToast({ message: err?.message ?? "Ошибка запроса к AI", variant: "error" }),
  });

  const handleSave = () => {
    const modelTrimmed = (model ?? "").trim();
    const providerTrimmed = (provider ?? "").trim();
    if (!modelTrimmed) {
      setToast({ message: "Укажите модель", variant: "error" });
      return;
    }
    if (modelTrimmed.length > 128) {
      setToast({ message: "Модель не более 128 символов", variant: "error" });
      return;
    }
    if (providerTrimmed && providerTrimmed.length > 32) {
      setToast({ message: "Провайдер не более 32 символов", variant: "error" });
      return;
    }
    const temp = Number(temperature);
    if (Number.isNaN(temp) || temp < 0 || temp > 1) {
      setToast({ message: "Температура от 0 до 1", variant: "error" });
      return;
    }
    updateMutation.mutate({ provider: providerTrimmed || undefined, model: modelTrimmed, temperature: temp });
  };

  const handleTest = () => testMutation.mutate();

  if (isLoading) return <div className="text-sm text-slate-600">Загрузка...</div>;

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <div className="text-lg font-semibold text-slate-900">Настройки AI</div>
      <p className="text-sm text-slate-600">
        Выбор провайдера и модели для чата с клиентами. Для OpenRouter укажите OPENROUTER_API_KEY в .env.
      </p>
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Провайдер</label>
          <select
            className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
          >
            <option value="openai">OpenAI</option>
            <option value="openrouter">OpenRouter</option>
          </select>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Модель</label>
          <Input
            label="ID модели (например gpt-4o-mini или openai/gpt-4o для OpenRouter)"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          />
          <p className="mt-1 text-xs text-slate-500">
            Популярные: {POPULAR_MODELS.filter((m) => m.provider === provider).map((m) => m.model).join(", ")}
          </p>
        </div>
        <Input
          label="Температура (0–1)"
          type="number"
          min={0}
          max={1}
          step={0.1}
          value={temperature}
          onChange={(e) => setTemperature(e.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          <Button onClick={handleSave} disabled={updateMutation.isPending}>
            {updateMutation.isPending ? "Сохранение..." : "Сохранить"}
          </Button>
          <Button variant="secondary" onClick={handleTest} disabled={testMutation.isPending}>
            {testMutation.isPending ? "Тест..." : "Тестовый запрос"}
          </Button>
        </div>
      </div>
    </div>
  );
}

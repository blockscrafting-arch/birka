import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Toast } from "../../components/ui/Toast";
import { useAdminDestinations, useCreateDestination, useUpdateDestination } from "../../hooks/useAdmin";

export function DestinationsPage() {
  const { items: destinations = [], isLoading, error } = useAdminDestinations();
  const create = useCreateDestination();
  const update = useUpdateDestination();
  const [name, setName] = useState("");
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  const handleCreate = async () => {
    const value = name.trim();
    if (!value) return;
    setToast(null);
    try {
      await create.mutateAsync({ name: value });
      setName("");
      setToast({ message: "Адрес добавлен", variant: "success" });
    } catch {
      setToast({ message: "Не удалось добавить адрес", variant: "error" });
    }
  };

  const handleToggleActive = (id: number, is_active: boolean) => {
    setToast(null);
    update.mutate(
      { id, is_active: !is_active },
      {
        onSuccess: () => setToast({ message: "Статус обновлён", variant: "success" }),
        onError: (err) => setToast({ message: err?.message ?? "Ошибка обновления статуса", variant: "error" }),
      }
    );
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <div className="text-lg font-semibold text-slate-900">Адреса/назначения</div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <Input label="Новый адрес" value={name} onChange={(e) => setName(e.target.value)} />
        <Button onClick={handleCreate} disabled={create.isPending}>
          Добавить
        </Button>
      </div>

      {isLoading ? <div className="text-sm text-slate-600">Загрузка адресов...</div> : null}
      {error ? <div className="text-sm text-rose-500">Ошибка загрузки адресов</div> : null}

      {!isLoading && !error && destinations.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center shadow-soft">
          <p className="text-sm text-slate-600">Пока нет адресов. Добавьте первый в форме выше.</p>
        </div>
      ) : null}

      <div className="space-y-2">
        {destinations.map((dest) => (
          <div key={dest.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
            <div className="text-sm font-semibold text-slate-900">{dest.name}</div>
            <div className="text-xs text-slate-500">Статус: {dest.is_active ? "Активен" : "Неактивен"}</div>
            <div className="mt-2 flex gap-2">
              <Button
                variant="secondary"
                onClick={() => handleToggleActive(dest.id, dest.is_active)}
                disabled={update.isPending}
              >
                {dest.is_active ? "Отключить" : "Включить"}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

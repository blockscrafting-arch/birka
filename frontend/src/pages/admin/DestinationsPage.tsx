import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { useAdminDestinations, useCreateDestination, useUpdateDestination } from "../../hooks/useAdmin";

export function DestinationsPage() {
  const { items: destinations = [], isLoading, error } = useAdminDestinations();
  const create = useCreateDestination();
  const update = useUpdateDestination();
  const [name, setName] = useState("");

  const handleCreate = async () => {
    const value = name.trim();
    if (!value) return;
    await create.mutateAsync({ name: value });
    setName("");
  };

  return (
    <div className="space-y-4">
      <div className="text-lg font-semibold text-slate-900">Адреса/назначения</div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <Input label="Новый адрес" value={name} onChange={(e) => setName(e.target.value)} />
        <Button onClick={handleCreate} disabled={create.isPending}>
          Добавить
        </Button>
      </div>

      {isLoading ? <div className="text-sm text-slate-600">Загрузка адресов...</div> : null}
      {error ? <div className="text-sm text-rose-500">Ошибка загрузки адресов</div> : null}

      <div className="space-y-2">
        {destinations.map((dest) => (
          <div key={dest.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
            <div className="text-sm font-semibold text-slate-900">{dest.name}</div>
            <div className="text-xs text-slate-500">Статус: {dest.is_active ? "Активен" : "Неактивен"}</div>
            <div className="mt-2 flex gap-2">
              <Button
                variant="secondary"
                onClick={() => update.mutate({ id: dest.id, is_active: !dest.is_active })}
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

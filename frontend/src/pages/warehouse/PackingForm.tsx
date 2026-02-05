import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useDestinations } from "../../hooks/useDestinations";
import { OrderItem } from "../../types";

export type PackingRow = {
  product_id: number;
  pallet_number?: string;
  box_number?: string;
  quantity: number;
};

type PackingFormProps = {
  items: OrderItem[];
  isSubmitting?: boolean;
  onSubmit: (payload: {
    product_id: number;
    employee_code: string;
    quantity: number;
    pallet_number?: string;
    box_number?: string;
    warehouse?: string;
    materials_used?: string;
    time_spent_minutes?: number;
  }) => void;
};

export function PackingForm({ items, isSubmitting, onSubmit }: PackingFormProps) {
  const { items: destinations } = useDestinations();
  const [employeeId, setEmployeeId] = useState("");
  const [rows, setRows] = useState<PackingRow[]>([{ product_id: 0, quantity: 1 }]);
  const [warehouse, setWarehouse] = useState("");
  const [materials, setMaterials] = useState("");
  const [time, setTime] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showDetailsFor, setShowDetailsFor] = useState<number | null>(null);

  const updateRow = (index: number, patch: Partial<PackingRow>) => {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  };

  const addRow = () => {
    setRows((prev) => [...prev, { product_id: 0, quantity: 1 }]);
  };

  const removeRow = (index: number) => {
    setRows((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        setError(null);
        if (!employeeId.trim()) {
          setError("Введите ID сотрудника");
          return;
        }
        const valid = rows.filter((r) => r.product_id && r.quantity > 0);
        if (valid.length === 0) {
          setError("Добавьте хотя бы одну позицию с товаром и количеством");
          return;
        }
        const toOptionalInt = (s: string | undefined): number | undefined => {
          const t = s?.trim();
          if (!t) return undefined;
          const n = Number(t);
          return Number.isNaN(n) ? undefined : n;
        };
        onSubmit(
          valid.map((row) => ({
            product_id: row.product_id,
            employee_code: employeeId.trim(),
            quantity: row.quantity,
            pallet_number: toOptionalInt(row.pallet_number),
            box_number: toOptionalInt(row.box_number),
            warehouse: warehouse.trim() || undefined,
            materials_used: materials.trim() || undefined,
            time_spent_minutes: time ? Number(time) : undefined,
          }))
        );
      }}
    >
      <Input label="ID сотрудника" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} />

      {items.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700 shadow-soft">
          В этой заявке нет позиций для упаковки.
        </div>
      ) : (
        <>
          <div className="text-sm font-medium text-slate-700">Позиции упаковки</div>
          {rows.map((row, index) => {
            const selected = items.find((item) => item.product_id === row.product_id);
            return (
              <div
                key={index}
                className="rounded-lg border border-slate-200 bg-white p-3 shadow-soft space-y-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Select
                    label="Товар"
                    value={row.product_id ? String(row.product_id) : ""}
                    onChange={(e) => updateRow(index, { product_id: Number(e.target.value) })}
                  >
                    <option value="" disabled>
                      Выберите товар
                    </option>
                    {items.map((item) => (
                      <option key={item.id} value={item.product_id}>
                        {item.product_name}
                      </option>
                    ))}
                  </Select>
                  {rows.length > 1 ? (
                    <Button type="button" variant="ghost" onClick={() => removeRow(index)}>
                      Удалить
                    </Button>
                  ) : null}
                </div>
                {selected ? (
                  <div className="rounded border border-slate-100 bg-slate-50 p-2 text-xs text-slate-600">
                    <span>ШК: {selected.barcode ?? "—"} · План: {selected.planned_qty} · Принято: {selected.received_qty}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      className="ml-2"
                      onClick={() => setShowDetailsFor(showDetailsFor === index ? null : index)}
                    >
                      {showDetailsFor === index ? "Скрыть" : "Подробнее"}
                    </Button>
                    {showDetailsFor === index ? (
                      <div className="mt-1 space-y-0.5">
                        Бренд: {selected.brand ?? "—"} · Размер: {selected.size ?? "—"} · Артикул WB: {selected.wb_article ?? "—"}
                      </div>
                    ) : null}
                  </div>
                ) : null}
                <div className="grid grid-cols-3 gap-2">
                  <Input
                    label="Паллета"
                    value={row.pallet_number ?? ""}
                    onChange={(e) => updateRow(index, { pallet_number: e.target.value })}
                  />
                  <Input
                    label="Короб"
                    value={row.box_number ?? ""}
                    onChange={(e) => updateRow(index, { box_number: e.target.value })}
                  />
                  <Input
                    label="Кол-во"
                    inputMode="numeric"
                    value={String(row.quantity)}
                    onChange={(e) => updateRow(index, { quantity: Number(e.target.value) || 0 })}
                  />
                </div>
              </div>
            );
          })}
          <Button type="button" variant="secondary" onClick={addRow} disabled={items.length === 0}>
            + Добавить товар
          </Button>
        </>
      )}

      <Select
        label="Склад назначения (необязательно)"
        value={warehouse}
        onChange={(e) => setWarehouse(e.target.value)}
      >
        <option value="">Не выбрано</option>
        {destinations.map((d) => (
          <option key={d.id} value={d.name}>
            {d.name}
          </option>
        ))}
      </Select>
      <Input label="Использованные материалы" value={materials} onChange={(e) => setMaterials(e.target.value)} />
      <Input label="Время упаковки (мин)" value={time} onChange={(e) => setTime(e.target.value)} />

      {error ? <div className="text-sm text-rose-500">{error}</div> : null}
      <Button type="submit" disabled={isSubmitting || items.length === 0}>
        Завершить упаковку
      </Button>
    </form>
  );
}

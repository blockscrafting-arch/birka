import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { useDestinations } from "../../hooks/useDestinations";
import { OrderItem } from "../../types";

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
  const [productId, setProductId] = useState("");
  const [pallet, setPallet] = useState("");
  const [box, setBox] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [warehouse, setWarehouse] = useState("");
  const [materials, setMaterials] = useState("");
  const [time, setTime] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const selected = items.find((item) => item.product_id === Number(productId));

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
        if (!productId) {
          setError("Выберите товар");
          return;
        }
        const qty = Number(quantity);
        if (Number.isNaN(qty) || qty <= 0) {
          setError("Введите корректное количество");
          return;
        }
        onSubmit({
          product_id: Number(productId),
          employee_code: employeeId.trim(),
          quantity: qty,
          pallet_number: pallet.trim() || undefined,
          box_number: box.trim() || undefined,
          warehouse: warehouse.trim() || undefined,
          materials_used: materials.trim() || undefined,
          time_spent_minutes: time ? Number(time) : undefined,
        });
      }}
    >
      <Input label="ID сотрудника" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} />
      {items.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700 shadow-soft">
          В этой заявке нет позиций для упаковки.
        </div>
      ) : (
        <Select label="Товар" value={productId} onChange={(e) => setProductId(e.target.value)}>
          <option value="" disabled>
            Выберите товар
          </option>
          {items.map((item) => (
            <option key={item.id} value={item.product_id}>
              {item.product_name}
            </option>
          ))}
        </Select>
      )}
      {selected ? (
        <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
          <div>
            ШК: {selected.barcode ?? "—"} · План: {selected.planned_qty} · Принято: {selected.received_qty}
          </div>
          <Button type="button" variant="ghost" onClick={() => setShowDetails((prev) => !prev)}>
            {showDetails ? "Скрыть карточку товара" : "Показать карточку товара"}
          </Button>
          {showDetails ? (
            <div className="space-y-1">
              <div>Бренд: {selected.brand ?? "—"}</div>
              <div>Размер: {selected.size ?? "—"}</div>
              <div>Цвет: {selected.color ?? "—"}</div>
              <div>Артикул WB: {selected.wb_article ?? "—"}</div>
              <div>Ссылка WB: {selected.wb_url ?? "—"}</div>
              <div>ТЗ: {selected.packing_instructions ?? "—"}</div>
              <div>Поставщик: {selected.supplier_name ?? "—"}</div>
            </div>
          ) : null}
        </div>
      ) : null}
      <Input label="Номер паллеты" value={pallet} onChange={(e) => setPallet(e.target.value)} />
      <Input label="Номер короба" value={box} onChange={(e) => setBox(e.target.value)} />
      <Input label="Количество в коробе" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
      <Select
          label="Склад назначения"
          value={warehouse}
          onChange={(e) => setWarehouse(e.target.value)}
        >
          <option value="">Выберите склад</option>
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

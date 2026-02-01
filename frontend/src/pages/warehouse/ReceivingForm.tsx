import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { OrderItem } from "../../types";

type ReceivingFormProps = {
  items: OrderItem[];
  isSubmitting?: boolean;
  onSubmit: (payload: { order_item_id: number; received_qty: number; defect_qty: number }) => void;
};

export function ReceivingForm({ items, isSubmitting, onSubmit }: ReceivingFormProps) {
  const [itemId, setItemId] = useState("");
  const [received, setReceived] = useState("0");
  const [defect, setDefect] = useState("0");
  const [error, setError] = useState<string | null>(null);

  const selected = items.find((item) => item.id === Number(itemId));

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        setError(null);
        if (!itemId) {
          setError("Выберите позицию");
          return;
        }
        const receivedQty = Number(received);
        const defectQty = Number(defect);
        if (Number.isNaN(receivedQty) || receivedQty < 0) {
          setError("Введите корректное количество");
          return;
        }
        if (Number.isNaN(defectQty) || defectQty < 0) {
          setError("Введите корректный брак");
          return;
        }
        onSubmit({ order_item_id: Number(itemId), received_qty: receivedQty, defect_qty: defectQty });
      }}
    >
      {items.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-sm text-slate-200">
          В этой заявке нет позиций для приёмки.
        </div>
      ) : (
        <Select label="Позиция" value={itemId} onChange={(e) => setItemId(e.target.value)}>
          <option value="" disabled>
            Выберите позицию
          </option>
          {items.map((item) => (
            <option key={item.id} value={item.id}>
              {item.product_name} · План {item.planned_qty}
            </option>
          ))}
        </Select>
      )}

      {selected ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3 text-xs text-slate-300">
          ШК: {selected.barcode ?? "—"} · План: {selected.planned_qty} · Принято: {selected.received_qty}
        </div>
      ) : null}

      <Input
        label="Фактическое количество"
        inputMode="numeric"
        value={received}
        onChange={(e) => setReceived(e.target.value)}
      />
      <Input label="Брак" inputMode="numeric" value={defect} onChange={(e) => setDefect(e.target.value)} />
      {error ? <div className="text-sm text-rose-300">{error}</div> : null}
      <Button type="submit" disabled={isSubmitting || items.length === 0}>
        Завершить приёмку
      </Button>
    </form>
  );
}

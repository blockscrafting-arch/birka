import { useState } from "react";

import { Product } from "../../types";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";

type OrderFormProps = {
  products: Product[];
  isSubmitting?: boolean;
  onSubmit: (payload: { destination?: string; items: { product_id: number; planned_qty: number }[] }) => void;
};

type ItemRow = {
  productId: string;
  qty: string;
};

export function OrderForm({ products, isSubmitting, onSubmit }: OrderFormProps) {
  const [destination, setDestination] = useState("");
  const [items, setItems] = useState<ItemRow[]>([{ productId: "", qty: "1" }]);
  const [error, setError] = useState<string | null>(null);

  const updateItem = (index: number, patch: Partial<ItemRow>) => {
    setItems((prev) => prev.map((item, idx) => (idx === index ? { ...item, ...patch } : item)));
  };

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, idx) => idx !== index));
  };

  const addItem = () => {
    setItems((prev) => [...prev, { productId: "", qty: "1" }]);
  };

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        setError(null);

        const prepared = items
          .map((item) => ({
            product_id: Number(item.productId),
            planned_qty: Number(item.qty),
          }))
          .filter((item) => item.product_id && item.planned_qty > 0);

        if (prepared.length === 0) {
          setError("Добавьте хотя бы одну позицию");
          return;
        }

        onSubmit({
          destination: destination.trim() || undefined,
          items: prepared,
        });
      }}
    >
      <Input label="Адрес/назначение" value={destination} onChange={(e) => setDestination(e.target.value)} />

      {products.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700 shadow-soft">
          Сначала добавьте товары, чтобы создавать заявки.
        </div>
      ) : null}

      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={`item-${index}`} className="rounded-lg border border-slate-200 bg-white p-3 shadow-soft">
            <Select
              label="Товар"
              value={item.productId}
              onChange={(event) => updateItem(index, { productId: event.target.value })}
            >
              <option value="" disabled>
                Выберите товар
              </option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name} {product.barcode ? `(${product.barcode})` : ""}
                </option>
              ))}
            </Select>
            <Input
              label="Количество"
              inputMode="numeric"
              value={item.qty}
              onChange={(event) => updateItem(index, { qty: event.target.value })}
            />
            {items.length > 1 ? (
              <Button type="button" variant="ghost" className="mt-2" onClick={() => removeItem(index)}>
                Удалить позицию
              </Button>
            ) : null}
          </div>
        ))}
      </div>

      <Button type="button" variant="secondary" onClick={addItem}>
        Добавить позицию
      </Button>

      {error ? <div className="text-sm text-rose-500">{error}</div> : null}
      <Button type="submit" disabled={isSubmitting || products.length === 0}>
        Создать заявку
      </Button>
    </form>
  );
}

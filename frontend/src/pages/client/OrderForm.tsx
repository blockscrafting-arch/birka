import { useState } from "react";

import { Destination, Product } from "../../types";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";

type OrderFormProps = {
  products: Product[];
  destinations?: Destination[];
  isSubmitting?: boolean;
  onSubmit: (payload: { destination?: string; items: { product_id: number; planned_qty: number }[] }) => void;
};

type ItemRow = {
  productId: string;
  qty: string;
};

export function OrderForm({ products, destinations = [], isSubmitting, onSubmit }: OrderFormProps) {
  const [destinationId, setDestinationId] = useState("");
  const [destinationCustom, setDestinationCustom] = useState("");
  const [items, setItems] = useState<ItemRow[]>([{ productId: "", qty: "1" }]);
  const [error, setError] = useState<string | null>(null);

  const destination =
    destinationId === "__custom__"
      ? destinationCustom.trim()
      : destinations.find((d) => String(d.id) === destinationId)?.name ?? "";

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
          destination: destination || undefined,
          items: prepared,
        });
      }}
    >
      {destinations.length > 0 ? (
        <Select
          label="Адрес/назначение"
          value={destinationId}
          onChange={(e) => {
            setDestinationId(e.target.value);
            if (e.target.value !== "__custom__") setDestinationCustom("");
          }}
        >
          <option value="">Не выбрано</option>
          {destinations.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
          <option value="__custom__">Свой вариант</option>
        </Select>
      ) : null}
      {destinationId === "__custom__" ? (
        <Input
          label="Адрес/назначение (свой вариант)"
          value={destinationCustom}
          onChange={(e) => setDestinationCustom(e.target.value)}
        />
      ) : null}

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

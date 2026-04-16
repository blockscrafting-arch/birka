import { useState } from "react";

import { Destination, Product } from "../../types";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";

type ServiceItem = { service_id: number; quantity: number };

type OrderFormPayload = {
  items: { product_id: number; planned_qty: number; destination?: string }[];
  services?: ServiceItem[];
};

type OrderFormProps = {
  products: Product[];
  destinations?: Destination[];
  initialServices?: ServiceItem[];
  isSubmitting?: boolean;
  onSubmit: (payload: OrderFormPayload) => void;
};

type ItemRow = {
  productId: string;
  qty: string;
  destinationId: string;
  destinationCustom: string;
};

export function OrderForm({
  products,
  destinations = [],
  initialServices,
  isSubmitting,
  onSubmit,
}: OrderFormProps) {
  const [items, setItems] = useState<ItemRow[]>([
    { productId: "", qty: "1", destinationId: "", destinationCustom: "" },
  ]);
  const [error, setError] = useState<string | null>(null);
  const services = initialServices ?? [];

  const getDestinationForRow = (row: ItemRow): string | undefined => {
    const value =
      row.destinationId === "__custom__"
        ? row.destinationCustom.trim()
        : destinations.find((d) => String(d.id) === row.destinationId)?.name ?? "";
    return value || undefined;
  };

  const updateItem = (index: number, patch: Partial<ItemRow>) => {
    setItems((prev) => prev.map((item, idx) => (idx === index ? { ...item, ...patch } : item)));
  };

  const removeItem = (index: number) => {
    setItems((prev) => prev.filter((_, idx) => idx !== index));
  };

  const addItem = () => {
    setItems((prev) => [...prev, { productId: "", qty: "1", destinationId: "", destinationCustom: "" }]);
  };

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        setError(null);

        const prepared = items
          .map((row) => ({
            product_id: Number(row.productId),
            planned_qty: Number(row.qty),
            destination: getDestinationForRow(row),
          }))
          .filter((item) => item.product_id && item.planned_qty > 0);

        if (prepared.length === 0) {
          setError("Добавьте хотя бы одну позицию");
          return;
        }

        onSubmit({
          items: prepared,
          ...(services.length > 0 ? { services } : {}),
        });
      }}
    >
      {services.length > 0 ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 shadow-soft">
          <div className="mb-1 font-medium text-slate-800">Услуги из калькулятора</div>
          <ul className="list-inside list-disc space-y-0.5">
            {services.map((s, i) => (
              <li key={i}>
                Услуга #{s.service_id}, кол-во: {s.quantity}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-xs text-slate-500">Будут привязаны к заявке с текущими ценами.</p>
        </div>
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
            {destinations.length > 0 ? (
              <div className="mt-2">
                <label className="mb-1 block text-xs font-medium text-slate-600">Склад / назначение (необязательно)</label>
                <Select
                  value={item.destinationId}
                  onChange={(e) => updateItem(index, { destinationId: e.target.value })}
                >
                  <option value="">Не указано</option>
                  {destinations.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                  <option value="__custom__">Свой вариант</option>
                </Select>
                {item.destinationId === "__custom__" ? (
                  <Input
                    className="mt-1"
                    value={item.destinationCustom}
                    onChange={(e) => updateItem(index, { destinationCustom: e.target.value })}
                    placeholder="Введите название склада"
                  />
                ) : null}
              </div>
            ) : null}
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

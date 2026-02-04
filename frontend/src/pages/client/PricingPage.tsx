import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Skeleton } from "../../components/ui/Skeleton";
import { useServices, useServiceCategories, useExportServicesPdf } from "../../hooks/useServices";
import { Service } from "../../types";

function groupByCategory(items: Service[]): Record<string, Service[]> {
  const map: Record<string, Service[]> = {};
  for (const s of items) {
    if (!map[s.category]) map[s.category] = [];
    map[s.category].push(s);
  }
  return map;
}

type TabId = "price" | "calculator";

export function PricingPage() {
  const navigate = useNavigate();
  const { items: services = [], isLoading, error } = useServices();
  const { categories } = useServiceCategories();
  const exportPdf = useExportServicesPdf();

  const [tab, setTab] = useState<TabId>("price");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [openCategory, setOpenCategory] = useState<string | null>(null);
  const [quantities, setQuantities] = useState<Record<number, number>>({});

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const filtered = useMemo(() => {
    if (!debouncedSearch.trim()) return services;
    const q = debouncedSearch.trim().toLowerCase();
    return services.filter(
      (s) =>
        s.name.toLowerCase().includes(q) || s.category.toLowerCase().includes(q)
    );
  }, [services, debouncedSearch]);

  const grouped = useMemo(() => groupByCategory(filtered), [filtered]);

  const toggleCategory = (cat: string) => {
    setOpenCategory((c) => (c === cat ? null : cat));
  };

  const setQty = (serviceId: number, value: number) => {
    setQuantities((prev) => {
      const next = { ...prev };
      if (value <= 0) delete next[serviceId];
      else next[serviceId] = value;
      return next;
    });
  };

  const selectedItems = useMemo(
    () =>
      Object.entries(quantities)
        .filter(([, q]) => q > 0)
        .map(([id, q]) => ({ service_id: Number(id), quantity: q })),
    [quantities]
  );

  const totalResult = useMemo(() => {
    if (selectedItems.length === 0) return null;
    let total = 0;
    for (const item of selectedItems) {
      const s = services.find((x) => x.id === item.service_id);
      if (s) total += s.price * item.quantity;
    }
    return total;
  }, [selectedItems, services]);

  const handleCreateOrder = () => {
    navigate("/client/orders", { state: { services: selectedItems } });
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-lg font-semibold text-slate-900">Прайс и калькулятор</div>
        <Button
          variant="secondary"
          onClick={() => exportPdf.mutate()}
          disabled={exportPdf.isPending || isLoading}
        >
          Скачать PDF
        </Button>
      </div>

      <div className="flex gap-2 rounded-xl border border-slate-200 bg-white p-2 shadow-soft">
        <button
          type="button"
          onClick={() => setTab("price")}
          className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
            tab === "price" ? "bg-birka-500 text-white" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Прайс
        </button>
        <button
          type="button"
          onClick={() => setTab("calculator")}
          className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
            tab === "calculator" ? "bg-birka-500 text-white" : "text-slate-600 hover:bg-slate-100"
          }`}
        >
          Калькулятор
        </button>
      </div>

      {tab === "price" && (
        <>
          <Input
            label="Поиск по услуге"
            placeholder="Название или категория..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <p className="text-xs text-slate-500">
            Первая неделя хранения — бесплатно.
          </p>
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-14 rounded-xl" />
              <Skeleton className="h-14 rounded-xl" />
              <Skeleton className="h-14 rounded-xl" />
            </div>
          ) : null}
          {error ? <div className="text-sm text-rose-500">Ошибка загрузки прайса</div> : null}
          {!isLoading && Object.keys(grouped).length === 0 && debouncedSearch && (
            <div className="text-sm text-slate-500">Ничего не найдено по запросу «{debouncedSearch}»</div>
          )}
          {!isLoading ? (
          <div className="space-y-2">
            {Object.entries(grouped).map(([category, items]) => (
              <div
                key={category}
                className="rounded-xl border border-slate-200 bg-white shadow-soft overflow-hidden"
              >
                <button
                  type="button"
                  className="flex w-full items-center justify-between p-4 text-left font-semibold text-slate-800"
                  onClick={() => toggleCategory(category)}
                >
                  <span>{category}</span>
                  <span className="text-slate-400">{openCategory === category ? "−" : "+"}</span>
                </button>
                {openCategory === category && (
                  <div className="border-t border-slate-100 px-4 pb-4">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-slate-500">
                          <th className="py-2">Услуга</th>
                          <th className="py-2">Цена</th>
                          <th className="py-2">Ед.</th>
                        </tr>
                      </thead>
                      <tbody>
                        {items.map((s) => (
                          <tr key={s.id} className="border-t border-slate-50">
                            <td className="py-2">
                              <span className="text-slate-800">{s.name}</span>
                              {s.comment ? (
                                <div className="text-xs text-slate-500">{s.comment}</div>
                              ) : null}
                            </td>
                            <td className="py-2 text-slate-700">{Number(s.price).toLocaleString("ru-RU")} ₽</td>
                            <td className="py-2 text-slate-600">{s.unit}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
          ) : null}
        </>
      )}

      {tab === "calculator" && (
        <>
          <p className="text-sm text-slate-600">
            Выберите услуги и укажите количество. Итоговая сумма обновится автоматически.
          </p>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-24 rounded-xl" />
              <Skeleton className="h-24 rounded-xl" />
            </div>
          ) : null}
          {error ? <div className="text-sm text-rose-500">Ошибка загрузки услуг</div> : null}
          <div className="space-y-4">
            {categories.map((cat) => {
              const items = services.filter((s) => s.category === cat);
              if (items.length === 0) return null;
              return (
                <div key={cat} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
                  <div className="mb-3 text-sm font-semibold text-slate-800">{cat}</div>
                  <div className="space-y-2">
                    {items.map((s) => (
                      <div
                        key={s.id}
                        className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-100 p-2"
                      >
                        <span className="text-sm text-slate-800">{s.name}</span>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            min={0}
                            step={1}
                            value={quantities[s.id] ?? ""}
                            onChange={(e) => {
                              const v = parseFloat(e.target.value);
                              setQty(s.id, Number.isNaN(v) ? 0 : v);
                            }}
                            className="w-20 rounded border border-slate-200 px-2 py-1 text-sm text-slate-800"
                          />
                          <span className="text-xs text-slate-500">{s.unit}</span>
                          <span className="text-sm text-slate-600">{Number(s.price).toLocaleString("ru-RU")} ₽</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          {selectedItems.length > 0 && (
            <div className="sticky bottom-16 rounded-xl border border-slate-200 bg-white p-4 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <span className="text-sm text-slate-600">Итого: </span>
                  <span className="text-lg font-semibold text-slate-900">
                    {totalResult?.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ₽
                  </span>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => setQuantities({})}>Сбросить</Button>
                  <Button onClick={handleCreateOrder}>Оформить заявку</Button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

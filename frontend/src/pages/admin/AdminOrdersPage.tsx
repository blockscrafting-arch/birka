import { useState, useEffect } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Pagination } from "../../components/ui/Pagination";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useCompanies } from "../../hooks/useCompanies";
import { useOrders } from "../../hooks/useOrders";
import type { Order } from "../../types";

const ORDER_STATUS_OPTIONS = [
  { value: "", label: "Все статусы" },
  { value: "На приемке", label: "На приемке" },
  { value: "Принято", label: "Принято" },
  { value: "Упаковка", label: "Упаковка" },
  { value: "Готово к отгрузке", label: "Готово к отгрузке" },
  { value: "Завершено", label: "Завершено" },
];

export function AdminOrdersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [companyIdFilter, setCompanyIdFilter] = useState<number | "">("");
  const limit = 20;
  const { items: companies = [] } = useCompanies(1, 200);
  const { items, total, isLoading, error, updateStatus } = useOrders(
    companyIdFilter === "" ? undefined : companyIdFilter,
    page,
    limit,
    statusFilter || undefined,
    search || undefined
  );
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  useEffect(() => {
    setPage(1);
  }, [search, statusFilter, companyIdFilter]);

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const handleResetStatus = (order: Order, newStatus: "На приемке" | "Упаковка") => {
    setToast(null);
    updateStatus.mutate(
      { id: order.id, status: newStatus },
      {
        onSuccess: () => setToast({ message: `Статус заявки ${order.order_number} изменён на «${newStatus}»` }),
        onError: (err) =>
          setToast({ message: err instanceof Error ? err.message : "Ошибка сброса статуса", variant: "error" }),
      }
    );
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">Заявки</h2>
      <p className="text-sm text-slate-600">
        Сброс статуса заявки не удаляет данные приёмки и упаковки. Проверьте количества при необходимости.
      </p>
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-soft">
        <Input
          label="Поиск по номеру"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="№ заявки"
          className="min-w-[120px] max-w-[180px]"
        />
        <Select
          label="Статус"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          {ORDER_STATUS_OPTIONS.map((o) => (
            <option key={o.value || "_all"} value={o.value}>
              {o.label}
            </option>
          ))}
        </Select>
        <Select
          label="Компания"
          value={companyIdFilter === "" ? "" : String(companyIdFilter)}
          onChange={(e) => setCompanyIdFilter(e.target.value === "" ? "" : Number(e.target.value))}
        >
          <option value="">Все компании</option>
          {companies.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name || c.inn}
            </option>
          ))}
        </Select>
      </div>
      {toast ? (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      ) : null}

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : null}
      {error ? (
        <div className="text-sm text-rose-500">Не удалось загрузить заявки</div>
      ) : null}
      {!isLoading && items.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
          Нет заявок.
        </div>
      ) : null}

      <div className="space-y-3">
        {items.map((order) => (
          <div
            key={order.id}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-slate-900">
                  {order.company_name ?? "—"} {order.order_number}
                </div>
                <div className="text-xs text-slate-500">Статус: {order.status}</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  className="text-xs py-1.5 px-2"
                  disabled={updateStatus.isPending || order.status === "На приемке"}
                  onClick={() => handleResetStatus(order, "На приемке")}
                >
                  Сбросить на приёмку
                </Button>
                <Button
                  variant="secondary"
                  className="text-xs py-1.5 px-2"
                  disabled={updateStatus.isPending || order.status === "Упаковка"}
                  onClick={() => handleResetStatus(order, "Упаковка")}
                >
                  Сбросить на упаковку
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}

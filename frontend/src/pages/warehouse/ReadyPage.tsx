import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/Button";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { useOrders } from "../../hooks/useOrders";

const STATUSES = "Готово к отгрузке,Завершено";

export function ReadyPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const limit = 20;
  const { items, total, isLoading, error } = useOrders(undefined, page, limit, STATUSES);

  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">Готово к отгрузке</h2>
      <p className="text-sm text-slate-600">
        Заявки со статусом «Готово к отгрузке» и «Завершено» — очередь и история.
      </p>

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
          Нет заявок в очереди или завершённых.
        </div>
      ) : null}

      <div className="space-y-3">
        {items.map((order) => (
          <div
            key={order.id}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft"
          >
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-slate-900">
                  {order.company_name ?? "—"} {order.order_number}
                </div>
                <div className="text-xs text-slate-500">Статус: {order.status}</div>
              </div>
              <Button
                variant="secondary"
                onClick={() => navigate(`/client/orders/${order.id}`)}
              >
                Открыть
              </Button>
            </div>
          </div>
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}

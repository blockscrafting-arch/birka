import { useEffect, useState } from "react";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { Button } from "../../components/ui/Button";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useShipping } from "../../hooks/useShipping";

export function ShippingPage() {
  const { items: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const [page, setPage] = useState(1);
  const limit = 20;
  const { items, total, isLoading, error, updateStatus } = useShipping(
    activeCompanyId ?? undefined,
    page,
    limit
  );
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  useEffect(() => {
    setPage(1);
  }, [activeCompanyId]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
        Сначала добавьте компанию, чтобы работать с отгрузками.
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-4">
      {toast ? (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      ) : null}
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : null}
      {error ? (
        <div className="text-sm text-rose-500">Не удалось загрузить отгрузки</div>
      ) : null}
      {!isLoading && items.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
          Нет заявок на отгрузку.
        </div>
      ) : null}

      <div className="space-y-3">
        {items.map((shipment) => (
          <div
            key={shipment.id}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft transition-all duration-200 hover:border-birka-200 hover:shadow-card"
          >
            <div className="text-sm font-semibold text-slate-900">
              Отгрузка: {shipment.destination_type}
            </div>
            <div className="text-xs text-slate-500">Статус: {shipment.status}</div>
            {shipment.destination_comment ? (
              <div className="mt-1 text-xs text-slate-500">
                Комментарий: {shipment.destination_comment}
              </div>
            ) : null}
            {shipment.status !== "Отгружено" ? (
              <Button
                className="mt-2"
                variant="secondary"
                onClick={async () => {
                  try {
                    await updateStatus.mutateAsync({ id: shipment.id, status: "Отгружено" });
                    setToast({ message: "Статус обновлён" });
                  } catch {
                    setToast({ message: "Не удалось обновить статус", variant: "error" });
                  }
                }}
              >
                Отметить как отгружено
              </Button>
            ) : null}
          </div>
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}

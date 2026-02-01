import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { OrderCard } from "../../components/shared/OrderCard";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useOrders } from "../../hooks/useOrders";
import { useProducts } from "../../hooks/useProducts";
import { OrderForm } from "./OrderForm";

export function OrdersPage() {
  const navigate = useNavigate();
  const { data: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const { data, isLoading, error, create } = useOrders(activeCompanyId ?? undefined);
  const { data: products = [] } = useProducts(activeCompanyId ?? undefined);
  const [open, setOpen] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
        Сначала добавьте компанию, чтобы создавать заявки.
      </div>
    );
  }

  const orders = data ?? [];

  const handleCreate = async (payload: { destination?: string; items: { product_id: number; planned_qty: number }[] }) => {
    if (!activeCompanyId) return;
    setPageError(null);
    try {
      await create.mutateAsync({ company_id: activeCompanyId, ...payload });
      setOpen(false);
      setToast({ message: "Заявка создана" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось создать заявку");
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />
      <div className="flex items-center justify-between gap-2">
        <Button onClick={() => setOpen(true)}>Создать заявку</Button>
        {pageError ? <div className="text-sm text-rose-300">{pageError}</div> : null}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-rose-300">Не удалось загрузить заявки</div> : null}
      {!isLoading && orders.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
          Пока нет заявок.
        </div>
      ) : null}

      <div className="space-y-3">
        {orders.map((order) => (
          <OrderCard
            key={order.id}
            title={order.order_number}
            status={order.status}
            onClick={() => navigate(`/client/orders/${order.id}`)}
          />
        ))}
      </div>

      <Modal title="Новая заявка" open={open} onClose={() => setOpen(false)}>
        <OrderForm products={products} isSubmitting={create.isPending} onSubmit={handleCreate} />
      </Modal>
    </div>
  );
}

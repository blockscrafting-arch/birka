import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { OrderCard } from "../../components/shared/OrderCard";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useDestinations } from "../../hooks/useDestinations";
import { useOrders } from "../../hooks/useOrders";
import { useProducts } from "../../hooks/useProducts";
import { OrderForm } from "./OrderForm";

type OrderFormPayload = {
  destination?: string;
  items: { product_id: number; planned_qty: number }[];
  services?: { service_id: number; quantity: number }[];
};

export function OrdersPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { items: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const limit = 20;
  const { items, total, isLoading, error, create } = useOrders(activeCompanyId ?? undefined, page, limit, statusFilter);
  const { items: products = [] } = useProducts(activeCompanyId ?? undefined, 1, 100);
  const { items: destinations = [] } = useDestinations(true);
  const [open, setOpen] = useState(false);
  const [initialServicesFromCalculator, setInitialServicesFromCalculator] = useState<
    { service_id: number; quantity: number }[] | null
  >(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  useEffect(() => {
    const stateServices = (location.state as { services?: { service_id: number; quantity: number }[] } | null)?.services;
    if (stateServices?.length) {
      setInitialServicesFromCalculator(stateServices);
      setOpen(true);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, location.pathname, navigate]);

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
        Сначала добавьте компанию, чтобы создавать заявки.
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const orders = items;

  const handleCreate = async (payload: { destination?: string; items: { product_id: number; planned_qty: number }[] }) => {
    if (!activeCompanyId) return;
    setPageError(null);
    try {
      await create.mutateAsync({ company_id: activeCompanyId, ...payload });
      setOpen(false);
      setPage(1);
      setToast({ message: "Заявка создана" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось создать заявку");
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Select
            value={statusFilter ?? ""}
            onChange={(e) => {
              setStatusFilter(e.target.value || undefined);
              setPage(1);
            }}
          >
            <option value="">Все статусы</option>
            <option value="На приемке">На приемке</option>
            <option value="Принято">Принято</option>
            <option value="Упаковка">Упаковка</option>
            <option value="Готово к отгрузке">Готово к отгрузке</option>
            <option value="Завершено">Завершено</option>
          </Select>
          <Button onClick={() => setOpen(true)}>Создать заявку</Button>
        </div>
        {pageError ? <div className="text-sm text-rose-500">{pageError}</div> : null}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-rose-500">Не удалось загрузить заявки</div> : null}
      {!isLoading && orders.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center shadow-soft">
          <p className="mb-4 text-sm text-slate-600">Пока нет заявок. Создайте первую заявку.</p>
          <Button onClick={() => setOpen(true)}>Создать заявку</Button>
        </div>
      ) : null}

      <div className="space-y-3">
        {orders.map((order) => (
          <OrderCard
            key={order.id}
            title={order.order_number}
            status={order.status}
            photoCount={order.photo_count}
            onClick={() => navigate(`/client/orders/${order.id}`)}
          />
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />

      <Modal
        title="Новая заявка"
        open={open}
        onClose={() => {
          setOpen(false);
          setInitialServicesFromCalculator(null);
        }}
      >
        <OrderForm
          products={products}
          destinations={destinations}
          initialServices={initialServicesFromCalculator ?? undefined}
          isSubmitting={create.isPending}
          onSubmit={handleCreate}
        />
      </Modal>
    </div>
  );
}

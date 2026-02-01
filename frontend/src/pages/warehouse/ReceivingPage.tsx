import { useEffect, useState } from "react";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { Button } from "../../components/ui/Button";
import { Loader } from "../../components/ui/Loader";
import { Modal } from "../../components/ui/Modal";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useOrderItems } from "../../hooks/useOrderItems";
import { useOrders } from "../../hooks/useOrders";
import { useWarehouse } from "../../hooks/useWarehouse";
import { ReceivingForm } from "./ReceivingForm";

export function ReceivingPage() {
  const { items: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const { items: orders = [], isLoading } = useOrders(activeCompanyId ?? undefined, 1, 200);
  const [activeOrderId, setActiveOrderId] = useState<number | null>(null);
  const { data: items = [], isLoading: itemsLoading } = useOrderItems(activeOrderId ?? undefined);
  const { completeReceiving } = useWarehouse();
  const [pageError, setPageError] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
        Сначала добавьте компанию, чтобы работать со складом.
      </div>
    );
  }

  const handleSubmit = async (payload: { order_item_id: number; received_qty: number; defect_qty: number }) => {
    if (!activeOrderId) return;
    setPageError(null);
    try {
      await completeReceiving.mutateAsync({
        order_id: activeOrderId,
        items: [payload],
      });
      setActiveOrderId(null);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось завершить приёмку");
    }
  };

  return (
    <div className="space-y-4">
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />
      {pageError ? <div className="text-sm text-rose-300">{pageError}</div> : null}

      {isLoading ? <div className="text-sm text-slate-300">Загрузка заявок...</div> : null}
      {!isLoading && orders.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
          Нет заявок для приёмки.
        </div>
      ) : null}

      <div className="space-y-3">
        {orders.map((order) => (
          <div key={order.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-100">{order.order_number}</div>
            <Button className="mt-2" onClick={() => setActiveOrderId(order.id)}>
              Взять в работу
            </Button>
          </div>
        ))}
      </div>

      <Modal title="Приёмка" open={Boolean(activeOrderId)} onClose={() => setActiveOrderId(null)}>
        {itemsLoading ? (
          <Loader text="Загрузка позиций..." />
        ) : (
          <ReceivingForm items={items} isSubmitting={completeReceiving.isPending} onSubmit={handleSubmit} />
        )}
      </Modal>
    </div>
  );
}

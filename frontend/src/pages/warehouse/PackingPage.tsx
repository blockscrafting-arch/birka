import { useEffect, useState } from "react";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { PhotoGallery } from "../../components/shared/PhotoGallery";
import { PhotoUpload } from "../../components/shared/PhotoUpload";
import { Button } from "../../components/ui/Button";
import { Loader } from "../../components/ui/Loader";
import { Modal } from "../../components/ui/Modal";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useOrderItems } from "../../hooks/useOrderItems";
import { useOrders } from "../../hooks/useOrders";
import { useWarehouse } from "../../hooks/useWarehouse";
import { useOrderPhotos } from "../../hooks/useOrderPhotos";
import { PackingForm } from "./PackingForm";

export function PackingPage() {
  const { items: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const { items: orders = [], isLoading, updateStatus } = useOrders(
    activeCompanyId ?? undefined,
    1,
    100,
    "Принято,Упаковка"
  );
  const [activeOrderId, setActiveOrderId] = useState<number | null>(null);
  const { data: items = [], isLoading: itemsLoading } = useOrderItems(activeOrderId ?? undefined);
  const { createPacking } = useWarehouse();
  const { data: photos = [], upload } = useOrderPhotos(activeOrderId ?? undefined);
  const [pageError, setPageError] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
        Сначала добавьте компанию, чтобы работать со складом.
      </div>
    );
  }

  const handleSubmit = async (payload: {
    product_id: number;
    employee_code: string;
    quantity: number;
    pallet_number?: string;
    box_number?: string;
    warehouse?: string;
    materials_used?: string;
    time_spent_minutes?: number;
  }) => {
    if (!activeOrderId) return;
    setPageError(null);
    try {
      await createPacking.mutateAsync({ order_id: activeOrderId, ...payload });
      setActiveOrderId(null);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось завершить упаковку");
    }
  };

  return (
    <div className="space-y-4">
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />
      {pageError ? <div className="text-sm text-rose-500">{pageError}</div> : null}

      {isLoading ? <div className="text-sm text-slate-600">Загрузка заявок...</div> : null}
      {!isLoading && orders.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
          Нет заявок для упаковки.
        </div>
      ) : null}

      <div className="space-y-3">
        {orders.map((order) => (
          <div key={order.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
            <div className="text-sm font-semibold text-slate-900">{order.order_number}</div>
            <Button
              className="mt-2"
              onClick={async () => {
                setPageError(null);
                try {
                  if (order.status === "Принято") {
                    await updateStatus.mutateAsync({ id: order.id, status: "Упаковка" });
                  }
                  setActiveOrderId(order.id);
                } catch (err) {
                  setPageError(err instanceof Error ? err.message : "Не удалось взять заявку в работу");
                }
              }}
            >
              Взять в работу
            </Button>
          </div>
        ))}
      </div>

      <Modal title="Упаковка" open={Boolean(activeOrderId)} onClose={() => setActiveOrderId(null)}>
        {itemsLoading ? (
          <Loader text="Загрузка позиций..." />
        ) : (
          <div className="space-y-4">
            <PackingForm items={items} isSubmitting={createPacking.isPending} onSubmit={handleSubmit} />
            <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-soft">
              <div className="text-sm font-semibold text-slate-900">Фото заявки</div>
              <div className="mt-2">
                <PhotoGallery photos={photos.map((photo) => photo.url)} />
              </div>
              <div className="mt-3">
                <PhotoUpload
                  label="Приложить фото"
                  onFileChange={(file) => {
                    if (!activeOrderId) return;
                    upload.mutate({ orderId: activeOrderId, file, photo_type: "packing" });
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

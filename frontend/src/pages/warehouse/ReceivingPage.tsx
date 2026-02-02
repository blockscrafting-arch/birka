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
import { ReceivingForm } from "./ReceivingForm";

export function ReceivingPage() {
  const { items: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const { items: orders = [], isLoading } = useOrders(activeCompanyId ?? undefined, 1, 100, "На приемке");
  const [activeOrderId, setActiveOrderId] = useState<number | null>(null);
  const { data: items = [], isLoading: itemsLoading } = useOrderItems(activeOrderId ?? undefined);
  const { completeReceiving } = useWarehouse();
  const { data: photos = [], upload } = useOrderPhotos(activeOrderId ?? undefined);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  useEffect(() => {
    if (!activeOrderId) {
      setSelectedItemId(null);
    }
  }, [activeOrderId]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
        Сначала добавьте компанию, чтобы работать со складом.
      </div>
    );
  }

  const handleSubmit = async (payload: {
    order_item_id: number;
    received_qty: number;
    defect_qty: number;
    adjustment_qty: number;
    adjustment_note?: string;
  }) => {
    if (!activeOrderId) return;
    setPageError(null);
    try {
      await completeReceiving.mutateAsync({
        order_id: activeOrderId,
        items: [payload],
      });
      setActiveOrderId(null);
      setSelectedItemId(null);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось завершить приёмку");
    }
  };

  return (
    <div className="space-y-4">
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />
      {pageError ? <div className="text-sm text-rose-500">{pageError}</div> : null}

      {isLoading ? <div className="text-sm text-slate-600">Загрузка заявок...</div> : null}
      {!isLoading && orders.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
          Нет заявок для приёмки.
        </div>
      ) : null}

      <div className="space-y-3">
        {orders.map((order) => (
          <div key={order.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
            <div className="text-sm font-semibold text-slate-900">{order.order_number}</div>
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
          <div className="space-y-4">
            <ReceivingForm
              items={items}
              defectPhotosByProduct={defectPhotosByProduct}
              isSubmitting={completeReceiving.isPending}
              onSubmit={handleSubmit}
              onSelectItem={(itemId) => setSelectedItemId(itemId)}
            />
            <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-soft">
              <div className="text-sm font-semibold text-slate-900">Фото заявки</div>
              <div className="mt-2">
                <PhotoGallery photos={photos.map((photo) => photo.url)} />
              </div>
              <div className="mt-3">
                <PhotoUpload
                  label="Фото груза"
                  onFileChange={(file) => {
                    if (!activeOrderId) return;
                    const selectedItem = items.find((item) => item.id === selectedItemId);
                    upload.mutate({
                      orderId: activeOrderId,
                      file,
                      photo_type: "receiving",
                      product_id: selectedItem?.product_id,
                    });
                  }}
                />
                <div className="mt-3">
                  <PhotoUpload
                    label="Фото брака"
                    onFileChange={(file) => {
                      if (!activeOrderId) return;
                      const selectedItem = items.find((item) => item.id === selectedItemId);
                      upload.mutate({
                        orderId: activeOrderId,
                        file,
                        photo_type: "defect",
                        product_id: selectedItem?.product_id,
                      });
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

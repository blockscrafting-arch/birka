import { useState } from "react";

import { PhotoGallery } from "../../components/shared/PhotoGallery";
import { PhotoUpload } from "../../components/shared/PhotoUpload";
import { Button } from "../../components/ui/Button";
import { Loader } from "../../components/ui/Loader";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { Modal } from "../../components/ui/Modal";
import { Toast } from "../../components/ui/Toast";
import { useOrderItems } from "../../hooks/useOrderItems";
import { useOrders } from "../../hooks/useOrders";
import { useWarehouse } from "../../hooks/useWarehouse";
import { useOrderPhotos } from "../../hooks/useOrderPhotos";
import { apiClient } from "../../services/api";
import { PackingForm } from "./PackingForm";

export function PackingPage() {
  const { items: orders = [], isLoading, updateStatus } = useOrders(
    undefined,
    1,
    100,
    "Принято,Упаковка,Готово к отгрузке"
  );
  const [activeOrderId, setActiveOrderId] = useState<number | null>(null);
  const [formResetKey, setFormResetKey] = useState(0);
  const { data: items = [], isLoading: itemsLoading } = useOrderItems(activeOrderId ?? undefined);
  const { createPacking, completeOrder } = useWarehouse();
  const { data: photos = [], upload } = useOrderPhotos(activeOrderId ?? undefined);
  const activeOrder = activeOrderId ? orders.find((o) => o.id === activeOrderId) : null;
  const effectivePlan = activeOrder && items.length > 0
    ? Math.max(0, activeOrder.received_qty - items.reduce((s, i) => s + i.defect_qty, 0))
    : activeOrder?.received_qty ?? 0;
  const isFullyPacked = Boolean(activeOrder && effectivePlan > 0 && activeOrder.packed_qty >= effectivePlan);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  const handleExportFBO = async (orderId: number) => {
    try {
      await apiClient.api(`/warehouse/export-fbo/send?order_id=${orderId}`, { method: "POST" });
      setToast({ message: "Файл отправлен вам в Telegram" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка выгрузки", variant: "error" });
    }
  };

  const handleSubmit = async (
    payloads: {
      order_item_id: number;
      product_id: number;
      employee_code: string;
      quantity: number;
      pallet_number?: number;
      box_number?: number;
      warehouse?: string;
      materials_used?: string;
      time_spent_minutes?: number;
    }[]
  ) => {
    if (!activeOrderId) return;
    setPageError(null);
    try {
      for (const p of payloads) {
        await createPacking.mutateAsync({ order_id: activeOrderId, ...p });
      }
      setToast({ message: "Упаковка сохранена" });
      setFormResetKey((k) => k + 1);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось завершить упаковку");
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
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
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm font-semibold text-slate-900">{order.company_name} {order.order_number}</div>
              <StatusBadge status={order.status} />
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <Button
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
              <Button
                variant="secondary"
                onClick={() => handleExportFBO(order.id)}
              >
                Скачать FBO (Excel)
              </Button>
            </div>
          </div>
        ))}
      </div>

      <Modal title="Упаковка" open={Boolean(activeOrderId)} onClose={() => setActiveOrderId(null)}>
        {itemsLoading ? (
          <Loader text="Загрузка товаров..." />
        ) : (
          <div className="space-y-4">
            {activeOrder ? (
              <div className="text-sm font-semibold text-slate-900">
                {activeOrder.company_name} {activeOrder.order_number}
              </div>
            ) : null}
            <PackingForm
              items={items}
              isSubmitting={createPacking.isPending}
              onSubmit={handleSubmit}
              resetKey={formResetKey}
            />
            {activeOrder && isFullyPacked ? (
              <Button
                variant="secondary"
                onClick={() => activeOrderId && completeOrder.mutate(activeOrderId)}
                disabled={completeOrder.isPending}
              >
                Завершить заказ
              </Button>
            ) : null}
            <Button variant="secondary" className="mt-2" onClick={() => setActiveOrderId(null)}>
              Закрыть
            </Button>
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

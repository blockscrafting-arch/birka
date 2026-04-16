import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { PhotoUpload } from "../../components/shared/PhotoUpload";
import { Button } from "../../components/ui/Button";
import { Loader } from "../../components/ui/Loader";
import { Modal } from "../../components/ui/Modal";
import { Toast } from "../../components/ui/Toast";
import { useOrderItems } from "../../hooks/useOrderItems";
import { useOrders } from "../../hooks/useOrders";
import { useWarehouse } from "../../hooks/useWarehouse";
import { useOrderPhotos } from "../../hooks/useOrderPhotos";
import { apiClient } from "../../services/api";
import { OrderItem } from "../../types";
import { ReceivingForm } from "./ReceivingForm";

export function ReceivingPage() {
  const { items: orders = [], isLoading } = useOrders(undefined, 1, 100, "На приемке");
  const [activeOrderId, setActiveOrderId] = useState<number | null>(null);
  const { data: items = [], isLoading: itemsLoading } = useOrderItems(activeOrderId ?? undefined);
  const queryClient = useQueryClient();
  const { completeReceiving } = useWarehouse();
  const { data: photos = [], upload } = useOrderPhotos(activeOrderId ?? undefined);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string } | null>(null);
  const defectPhotosByProduct = useMemo(() => {
    const counts: Record<number, number> = {};
    for (const photo of photos) {
      if (photo.photo_type !== "defect") continue;
      const productId = photo.product_id;
      if (!productId) continue;
      counts[productId] = (counts[productId] ?? 0) + 1;
    }
    return counts;
  }, [photos]);

  useEffect(() => {
    if (!activeOrderId) {
      setSelectedItemId(null);
    }
  }, [activeOrderId]);

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
      await queryClient.invalidateQueries({ queryKey: ["order-items", activeOrderId] });
      const nextItems: OrderItem[] =
        (await queryClient.fetchQuery({
          queryKey: ["order-items", activeOrderId],
          queryFn: () => apiClient.api<OrderItem[]>(`/orders/${activeOrderId}/items`),
        })) ?? [];
      const remaining = nextItems.filter((i) => (i.received_qty ?? 0) < (i.planned_qty ?? 0));
      const nextIncomplete = nextItems.find((i) => (i.received_qty ?? 0) < (i.planned_qty ?? 0));
      if (remaining.length > 0 && nextIncomplete) {
        setToast({ message: `Товар принят. Осталось позиций: ${remaining.length}` });
        setSelectedItemId(nextIncomplete.id);
      } else {
        setActiveOrderId(null);
        setSelectedItemId(null);
        setToast({ message: "Приёмка завершена" });
      }
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось завершить приёмку");
    }
  };

  const handleFillZeros = async () => {
    if (!activeOrderId || items.length === 0) return;
    setPageError(null);
    try {
      const fullItems = items.map((i) => ({
        order_item_id: i.id,
        received_qty: i.received_qty ?? 0,
        defect_qty: i.defect_qty ?? 0,
        adjustment_qty: i.adjustment_qty ?? 0,
        adjustment_note: i.adjustment_note ?? undefined,
      }));
      await completeReceiving.mutateAsync({ order_id: activeOrderId, items: fullItems });
      setActiveOrderId(null);
      setSelectedItemId(null);
      setToast({ message: "Приёмка завершена (недопоставка отмечена нулями)" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось завершить приёмку");
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} onClose={() => setToast(null)} /> : null}
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
            <div className="text-sm font-semibold text-slate-900">{order.company_name} {order.order_number}</div>
            <Button className="mt-2" onClick={() => setActiveOrderId(order.id)}>
              Взять в работу
            </Button>
          </div>
        ))}
      </div>

      <Modal title="Приёмка" open={Boolean(activeOrderId)} onClose={() => setActiveOrderId(null)}>
        {itemsLoading ? (
          <Loader text="Загрузка товаров..." />
        ) : (
          <div className="space-y-4">
            <ReceivingForm
              items={items}
              selectedItemId={selectedItemId}
              defectPhotosByProduct={defectPhotosByProduct}
              isSubmitting={completeReceiving.isPending}
              onSubmit={handleSubmit}
              onSelectItem={(itemId) => setSelectedItemId(itemId)}
              onUploadDefectPhoto={(file) => {
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
            <div className="text-sm text-slate-500">
              «Завершить приёмку» отправит текущие количества (по непринятым позициям — нули) и закроет окно.
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                disabled={items.length === 0 || completeReceiving.isPending}
                onClick={handleFillZeros}
              >
                Завершить приёмку
              </Button>
              {items.some((i) => (i.received_qty ?? 0) === 0) ? (
                <Button
                  type="button"
                  variant="ghost"
                  disabled={completeReceiving.isPending}
                  onClick={handleFillZeros}
                >
                  Проставить 0 для оставшихся
                </Button>
              ) : null}
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-soft">
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
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

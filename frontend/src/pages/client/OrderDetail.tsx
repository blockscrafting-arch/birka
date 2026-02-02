import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { PhotoGallery } from "../../components/shared/PhotoGallery";
import { PhotoUpload } from "../../components/shared/PhotoUpload";
import { Button } from "../../components/ui/Button";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { Toast } from "../../components/ui/Toast";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useOrders } from "../../hooks/useOrders";
import { useOrderItems } from "../../hooks/useOrderItems";
import { useOrderPhotos } from "../../hooks/useOrderPhotos";
import { apiClient } from "../../services/api";

export function OrderDetail() {
  const { orderId } = useParams();
  const { items: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const { items: orders } = useOrders(activeCompanyId ?? undefined, 1, 100);
  const order = useMemo(() => orders.find((item) => item.id === Number(orderId)), [orders, orderId]);
  const { data: items = [] } = useOrderItems(order?.id);
  const { data: photos = [], upload } = useOrderPhotos(order?.id);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  const handleExportReceiving = async () => {
    if (!order) return;
    try {
      const { blob, filename } = await apiClient.apiFile(`/orders/${order.id}/export-receiving`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename ?? `Приемка_${order.order_number}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      setToast({ message: "Файл скачан" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка выгрузки", variant: "error" });
    }
  };

  if (!order) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
        Заявка не найдена или недоступна.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-semibold text-slate-900">{order.order_number}</div>
            <StatusBadge status={order.status} />
          </div>
          <Button variant="secondary" onClick={handleExportReceiving}>
            Скачать приёмку (Excel)
          </Button>
        </div>
        <div className="mt-2 text-xs text-slate-500">
          План: {order.planned_qty} · Принято: {order.received_qty} · Упаковано: {order.packed_qty}
        </div>
        {order.destination ? (
          <div className="mt-1 text-xs text-slate-500">Назначение: {order.destination}</div>
        ) : null}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
        <div className="text-sm font-semibold text-slate-900">Позиции</div>
        {items.length === 0 ? (
          <div className="mt-2 text-sm text-slate-600">Позиции пока не добавлены.</div>
        ) : (
          <div className="mt-2 space-y-2 text-sm text-slate-700">
            {items.map((item) => (
              <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 pb-2">
                <span>{item.product_name}</span>
                <span className="text-xs text-slate-500">
                  План: {item.planned_qty} · Принято: {item.received_qty} · Брак: {item.defect_qty}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
        <div className="text-sm font-semibold text-slate-900">Фото</div>
        <div className="mt-2">
          <PhotoGallery photos={photos.map((photo) => photo.url)} />
        </div>
        <div className="mt-3">
          <PhotoUpload
            label="Добавить фото к заявке"
            onFileChange={(file) => {
              if (!order) return;
              upload.mutate({ orderId: order.id, file, photo_type: "order" });
            }}
          />
        </div>
      </div>
    </div>
  );
}

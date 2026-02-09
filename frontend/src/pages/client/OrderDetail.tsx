import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { PhotoGallery } from "../../components/shared/PhotoGallery";
import { StatusBadge } from "../../components/ui/StatusBadge";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useOrders } from "../../hooks/useOrders";
import { useOrderItems } from "../../hooks/useOrderItems";
import { apiClient } from "../../services/api";

export function OrderDetail() {
  const { orderId } = useParams();
  const { data: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const { data } = useOrders(activeCompanyId ?? undefined);
  const order = useMemo(() => data?.find((item) => item.id === Number(orderId)), [data, orderId]);
  const { data: items = [] } = useOrderItems(order?.id);
  const [photos, setPhotos] = useState<string[]>([]);
  const [photosError, setPhotosError] = useState<string | null>(null);
  const [photosLoading, setPhotosLoading] = useState(false);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  useEffect(() => {
    if (!order?.id) return;
    setPhotosLoading(true);
    setPhotosError(null);
    apiClient
      .api<{ url: string }[]>(`/orders/${order.id}/photos`)
      .then((data) => setPhotos(data.map((photo) => photo.url)))
      .catch((err) => {
        setPhotosError(err instanceof Error ? err.message : "Не удалось загрузить фото заказа");
        setPhotos([]);
      })
      .finally(() => setPhotosLoading(false));
  }, [order?.id]);

  if (!order) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
        Заявка не найдена или недоступна.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-slate-100">{order.order_number}</div>
          <StatusBadge status={order.status} />
        </div>
        <div className="mt-2 text-xs text-slate-400">
          План: {order.planned_qty} · Принято: {order.received_qty} · Упаковано: {order.packed_qty}
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
        <div className="text-sm font-semibold text-slate-100">Позиции</div>
        {items.length === 0 ? (
          <div className="mt-2 text-sm text-slate-300">Позиции пока не добавлены.</div>
        ) : (
          <div className="mt-2 space-y-2 text-sm text-slate-300">
            {items.map((item) => (
              <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
                <span>{item.product_name}</span>
                <span className="text-xs text-slate-400">
                  План: {item.planned_qty} · Принято: {item.received_qty} · Брак: {item.defect_qty}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
        <div className="text-sm font-semibold text-slate-100">Фото</div>
        <div className="mt-2">
          {photosLoading ? <div className="text-sm text-slate-400">Загрузка фото...</div> : null}
          {photosError ? <div className="text-sm text-rose-300">{photosError}</div> : null}
          {!photosLoading && !photosError ? <PhotoGallery photos={photos} /> : null}
        </div>
      </div>
    </div>
  );
}

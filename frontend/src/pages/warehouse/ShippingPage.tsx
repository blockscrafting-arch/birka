import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useOrderPackingRecords } from "../../hooks/useOrders";
import { useShipping } from "../../hooks/useShipping";
import { apiClient, downloadFile } from "../../services/api";
import type { ShippingRequest } from "../../types";

export function ShippingPage() {
  const [page, setPage] = useState(1);
  const limit = 20;
  const { items, total, isLoading, error, updateStatus } = useShipping(undefined, page, limit);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);
  const [downloadFboOrderId, setDownloadFboOrderId] = useState<number | null>(null);
  const [sendFboOrderId, setSendFboOrderId] = useState<number | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const handleDownloadFbo = async (orderId: number, orderNumber: string | null) => {
    setDownloadFboOrderId(orderId);
    setToast(null);
    try {
      await downloadFile(
        `/warehouse/export-fbo?order_id=${orderId}`,
        `Отгрузка_FBO_заявка_${orderNumber ?? orderId}.xlsx`
      );
      setToast({ message: "Таблица скачана", variant: "success" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка скачивания", variant: "error" });
    } finally {
      setDownloadFboOrderId(null);
    }
  };

  const handleSendFboToTelegram = async (orderId: number) => {
    setSendFboOrderId(orderId);
    setToast(null);
    try {
      await apiClient.api(`/warehouse/export-fbo/send?order_id=${orderId}`, { method: "POST" });
      setToast({ message: "Файл отправлен вам в Telegram", variant: "success" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка отправки файла", variant: "error" });
    } finally {
      setSendFboOrderId(null);
    }
  };

  return (
    <div className="space-y-4">
      {toast ? (
        <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} />
      ) : null}

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
          <ShipmentCard
            key={shipment.id}
            shipment={shipment}
            updateStatus={updateStatus}
            setToast={setToast}
            onDownloadFbo={
              shipment.order_id
                ? () => handleDownloadFbo(shipment.order_id!, shipment.order_number ?? null)
                : undefined
            }
            onSendFboToTelegram={
              shipment.order_id ? () => handleSendFboToTelegram(shipment.order_id!) : undefined
            }
            downloadFboPending={downloadFboOrderId === shipment.order_id}
            sendFboPending={sendFboOrderId === shipment.order_id}
          />
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}

function ShipmentCard({
  shipment,
  updateStatus,
  setToast,
  onDownloadFbo,
  onSendFboToTelegram,
  downloadFboPending,
  sendFboPending,
}: {
  shipment: ShippingRequest;
  updateStatus: ReturnType<typeof useShipping>["updateStatus"];
  setToast: (t: { message: string; variant?: "success" | "error" } | null) => void;
  onDownloadFbo?: () => void;
  onSendFboToTelegram?: () => void;
  downloadFboPending?: boolean;
  sendFboPending?: boolean;
}) {
  const { data: packingRecords = [] } = useOrderPackingRecords(shipment.order_id ?? undefined);
  const formatDate = (s: string | null) =>
    s
      ? new Date(s).toLocaleDateString("ru-RU", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
        })
      : null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft transition-all duration-200 hover:border-birka-200 hover:shadow-card">
      <div className="text-sm font-semibold text-slate-900">
        Отгрузка: {shipment.destination_type}
      </div>
      {shipment.order_number ? (
        <div className="text-xs text-slate-600">Заявка: {shipment.order_number}</div>
      ) : null}
      {shipment.warehouse_name ? (
        <div className="text-xs text-slate-600">Склад: {shipment.warehouse_name}</div>
      ) : null}
      {shipment.delivery_date ? (
        <div className="text-xs text-slate-600">
          Дата поставки: {formatDate(shipment.delivery_date)}
        </div>
      ) : null}
      <div className="text-xs text-slate-500">Статус: {shipment.status}</div>
      {shipment.destination_comment ? (
        <div className="mt-1 text-xs text-slate-500">
          Комментарий: {shipment.destination_comment}
        </div>
      ) : null}

      <div className="mt-3 rounded-lg border border-birka-200 bg-birka-50 p-3 shadow-soft">
        <div className="text-xs font-semibold text-slate-800">Таблица отгрузки (FBO)</div>
        {packingRecords.length > 0 ? (
          <div className="mt-2 space-y-2 text-sm text-slate-700">
            {packingRecords.map((r) => (
              <div key={r.id} className="border-b border-slate-200/60 pb-2 last:border-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span>{r.product_name}</span>
                  <span className="text-xs text-slate-500">
                    {r.quantity} шт.
                    {r.pallet_number != null ? ` · Паллета ${r.pallet_number}` : ""}
                    {r.box_number != null ? ` · Короб ${r.box_number}` : ""}
                    {r.warehouse ? ` · ${r.warehouse}` : ""}
                    {r.box_barcode ? ` · ШК короба ${r.box_barcode}` : ""}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-1 text-xs text-slate-500">
            Записи упаковки / данные FBO ещё не заполнены.
          </p>
        )}
        {(onDownloadFbo ?? onSendFboToTelegram) ? (
          <div className="mt-2 flex flex-wrap gap-2">
            {onDownloadFbo ? (
              <Button
                variant="secondary"
                onClick={onDownloadFbo}
                disabled={downloadFboPending}
              >
                {downloadFboPending ? "Скачивание…" : "Скачать таблицу"}
              </Button>
            ) : null}
            {onSendFboToTelegram ? (
              <Button
                variant="secondary"
                onClick={onSendFboToTelegram}
                disabled={sendFboPending}
              >
                {sendFboPending ? "Отправка…" : "Отправить в Telegram"}
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {shipment.supply_barcode_url ? (
          <a
            href={shipment.supply_barcode_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-birka-600 underline"
          >
            Скачать ШК поставки
          </a>
        ) : (
          <span className="text-xs text-slate-400">ШК поставки не загружен</span>
        )}
        {shipment.box_barcodes_url ? (
          <a
            href={shipment.box_barcodes_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-birka-600 underline"
          >
            Скачать ШК коробов
          </a>
        ) : (
          <span className="text-xs text-slate-400">ШК коробов не загружен</span>
        )}
      </div>
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
  );
}

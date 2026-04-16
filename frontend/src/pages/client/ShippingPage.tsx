import { useRef, useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { Select } from "../../components/ui/Select";
import { useCompanies } from "../../hooks/useCompanies";
import {
  useFBOSupply,
  useFBOCreate,
  useFBOImportBarcodes,
  useFBOSyncBarcodes,
  useFBOBoxStickers,
} from "../../hooks/useFBOSupplies";
import {
  useOrdersReadyForShipping,
  useShipping,
} from "../../hooks/useShipping";
import { apiClient, downloadFile } from "../../services/api";
import type { ShippingRequest } from "../../types";

export function ShippingPage() {
  const { items: companies = [] } = useCompanies();
  const activeCompanyId = companies[0]?.id ?? null;
  const [page, setPage] = useState(1);
  const limit = 20;
  const {
    items,
    total,
    isLoading,
    error,
    create,
    uploadSupplyBarcode,
    uploadBoxBarcodes,
    linkFbo,
  } = useShipping(activeCompanyId ?? undefined, page, limit);
  const createFboSupply = useFBOCreate();
  const { data: ordersReady = [], isLoading: ordersReadyLoading } =
    useOrdersReadyForShipping(activeCompanyId ?? undefined);
  const [open, setOpen] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);
  const [destinationType, setDestinationType] = useState("WB");
  const [orderId, setOrderId] = useState<string>("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [comment, setComment] = useState("");
  const [fboSupplyId, setFboSupplyId] = useState<number | null>(null);
  const [createFboFor, setCreateFboFor] = useState<{
    shipmentId: number;
    orderId: number;
    companyId: number;
  } | null>(null);
  const [createFboMarketplace, setCreateFboMarketplace] = useState<"wb" | "ozon">("wb");

  const supplyBarcodeInputRef = useRef<HTMLInputElement>(null);
  const boxBarcodesInputRef = useRef<HTMLInputElement>(null);
  const importFboInputRef = useRef<HTMLInputElement>(null);
  const importFboOrderIdRef = useRef<number | null>(null);
  const [importFboPending, setImportFboPending] = useState(false);
  const [exportFboPendingId, setExportFboPendingId] = useState<number | null>(null);
  const [downloadFboPendingId, setDownloadFboPendingId] = useState<number | null>(null);

  useEffect(() => {
    setPage(1);
  }, [activeCompanyId]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
        Сначала добавьте компанию, чтобы создавать отгрузки.
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const orderIdsWithShipment = new Set(
    items.map((s) => s.order_id).filter((id): id is number => id != null)
  );
  const ordersAvailable = ordersReady.filter((o) => !orderIdsWithShipment.has(o.id));

  const handleCreate = async () => {
    if (!activeCompanyId) return;
    setPageError(null);
    setFormError(null);
    if (!orderId || !orderId.trim()) {
      setFormError("Выберите заявку на поставку");
      return;
    }
    try {
      await create.mutateAsync({
        company_id: activeCompanyId,
        order_id: Number(orderId),
        destination_type: destinationType,
        destination_comment: comment.trim() || undefined,
        delivery_date: deliveryDate || undefined,
      });
      setOpen(false);
      setComment("");
      setOrderId("");
      setDeliveryDate("");
      setPage(1);
      setToast({ message: "Заявка на отгрузку создана" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось создать заявку на отгрузку");
    }
  };

  const handleSupplyBarcodeChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const shipmentId = (e.target as HTMLInputElement).dataset.shipmentId;
    if (!shipmentId) return;
    try {
      await uploadSupplyBarcode.mutateAsync({ requestId: Number(shipmentId), file });
      setToast({ message: "ШК поставки загружен" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка загрузки", variant: "error" });
    }
    e.target.value = "";
  };

  const handleBoxBarcodesChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const shipmentId = (e.target as HTMLInputElement).dataset.shipmentId;
    if (!shipmentId) return;
    try {
      await uploadBoxBarcodes.mutateAsync({ requestId: Number(shipmentId), file });
      setToast({ message: "ШК коробов загружен" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка загрузки", variant: "error" });
    }
    e.target.value = "";
  };

  const handleImportFboClick = (orderId: number) => {
    importFboOrderIdRef.current = orderId;
    importFboInputRef.current?.click();
  };

  const handleImportFboChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    const orderId = importFboOrderIdRef.current;
    e.target.value = "";
    importFboOrderIdRef.current = null;
    if (!file || !orderId) return;
    setImportFboPending(true);
    setPageError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiClient.apiForm<{ updated: number }>(
        `/warehouse/orders/${orderId}/import-fbo`,
        formData
      );
      setToast({ message: `Обновлено записей: ${res.updated ?? 0}` });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка импорта FBO", variant: "error" });
    } finally {
      setImportFboPending(false);
    }
  };

  const handleDownloadFbo = async (orderId: number) => {
    setDownloadFboPendingId(orderId);
    setToast(null);
    try {
      await downloadFile(
        `/orders/${orderId}/export-fbo`,
        `Отгрузка_FBO_заявка_${orderId}.xlsx`
      );
      setToast({ message: "Таблица скачана", variant: "success" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка скачивания", variant: "error" });
    } finally {
      setDownloadFboPendingId(null);
    }
  };

  const handleExportFboSend = async (orderId: number) => {
    setFormError(null);
    setToast(null);
    setExportFboPendingId(orderId);
    try {
      await apiClient.api(`/orders/${orderId}/export-fbo/send`, { method: "POST" });
      setToast({ message: "Таблица отправлена вам в Telegram", variant: "success" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка отправки файла", variant: "error" });
    } finally {
      setExportFboPendingId(null);
    }
  };

  const handleCreateFboAndLink = async () => {
    if (!createFboFor || !activeCompanyId) return;
    setPageError(null);
    try {
      const supply = await createFboSupply.mutateAsync({
        company_id: createFboFor.companyId,
        order_id: createFboFor.orderId,
        marketplace: createFboMarketplace,
      });
      await linkFbo.mutateAsync({
        requestId: createFboFor.shipmentId,
        fbo_supply_id: supply.id,
      });
      setCreateFboFor(null);
      setToast({ message: "FBO поставка создана и привязана к отгрузке" });
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : "Не удалось создать FBO поставку",
        variant: "error",
      });
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <div className="flex items-center justify-between gap-2">
        <Button onClick={() => setOpen(true)}>Создать отгрузку</Button>
        {pageError ? <div className="text-sm text-rose-500">{pageError}</div> : null}
      </div>

      <div className="rounded-xl border border-birka-200 bg-birka-50 p-3 text-sm text-slate-700 shadow-soft">
        <div className="font-semibold text-slate-800">Таблица отгрузки (FBO)</div>
        <p className="mt-1 text-xs text-slate-600">
          Создайте отгрузку → в карточке нажмите <strong>«Скачать таблицу»</strong> → заполните в файле столбцы <strong>«Баркод короба»</strong>, <strong>«Склад»</strong>, <strong>«Дата поставки»</strong> → нажмите <strong>«Загрузить таблицу»</strong>. После этого данные уйдут на склад.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-rose-500">Не удалось загрузить отгрузки</div> : null}
      {!isLoading && items.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
          Пока нет заявок на отгрузку. Нажмите «Создать отгрузку» — в каждой карточке появится блок «Таблица отгрузки» (скачать → заполнить → загрузить).
        </div>
      ) : null}

      <div className="space-y-3">
        {items.map((shipment) => (
          <ShipmentCard
            key={shipment.id}
            shipment={shipment}
            onDownloadFbo={
              shipment.order_id ? () => handleDownloadFbo(shipment.order_id!) : undefined
            }
            onExportFboSend={
              shipment.order_id
                ? () => handleExportFboSend(shipment.order_id!)
                : undefined
            }
            downloadFboPending={downloadFboPendingId === shipment.order_id}
            exportFboPending={exportFboPendingId === shipment.order_id}
            onImportFBO={
              shipment.order_id
                ? () => handleImportFboClick(shipment.order_id!)
                : undefined
            }
            importFboPending={importFboPending}
            onOpenFBO={
              shipment.fbo_supply_id ? () => setFboSupplyId(shipment.fbo_supply_id!) : undefined
            }
            onCreateFBO={
              shipment.order_id && !shipment.fbo_supply_id && activeCompanyId
                ? () =>
                    setCreateFboFor({
                      shipmentId: shipment.id,
                      orderId: shipment.order_id!,
                      companyId: activeCompanyId,
                    })
                : undefined
            }
            onCreateFboPending={createFboSupply.isPending || linkFbo.isPending}
            onUploadSupplyBarcode={(id) => {
              supplyBarcodeInputRef.current?.setAttribute("data-shipment-id", String(id));
              supplyBarcodeInputRef.current?.click();
            }}
            onUploadBoxBarcodes={(id) => {
              boxBarcodesInputRef.current?.setAttribute("data-shipment-id", String(id));
              boxBarcodesInputRef.current?.click();
            }}
            uploadSupplyPending={uploadSupplyBarcode.isPending}
            uploadBoxPending={uploadBoxBarcodes.isPending}
          />
        ))}
      </div>

      {fboSupplyId != null ? (
        <FBOSupplyDetailModal
          supplyId={fboSupplyId}
          onClose={() => setFboSupplyId(null)}
        />
      ) : null}

      <input
        ref={supplyBarcodeInputRef}
        type="file"
        className="hidden"
        accept=".pdf,image/*"
        onChange={handleSupplyBarcodeChange}
      />
      <input
        ref={boxBarcodesInputRef}
        type="file"
        className="hidden"
        accept=".pdf,image/*,.xlsx,.xls"
        onChange={handleBoxBarcodesChange}
      />
      <input
        ref={importFboInputRef}
        type="file"
        className="hidden"
        accept=".xlsx,.xls"
        onChange={handleImportFboChange}
      />

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />

      <Modal
        title="Создать FBO поставку"
        open={createFboFor != null}
        onClose={() => setCreateFboFor(null)}
      >
        {createFboFor ? (
          <div className="space-y-3">
            <Select
              label="Маркетплейс"
              value={createFboMarketplace}
              onChange={(e) => setCreateFboMarketplace(e.target.value as "wb" | "ozon")}
            >
              <option value="wb">WB</option>
              <option value="ozon">Ozon</option>
            </Select>
            <Button
              onClick={handleCreateFboAndLink}
              disabled={createFboSupply.isPending || linkFbo.isPending}
            >
              {createFboSupply.isPending || linkFbo.isPending ? "Создаю..." : "Создать и привязать"}
            </Button>
          </div>
        ) : null}
      </Modal>

      <Modal title="Новая отгрузка" open={open} onClose={() => { setOpen(false); setFormError(null); }}>
        <div className="space-y-3">
          {formError ? <p className="text-sm text-rose-500">{formError}</p> : null}
          <Select
            label="Какую заявку отгружаем"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
          >
            <option value="">— Выберите заявку —</option>
            {ordersReadyLoading
              ? (
                <option value="" disabled>Загрузка...</option>
                )
              : ordersAvailable.length === 0
                ? (
                  <option value="" disabled>Нет заявок «Готово к отгрузке» или все уже отгружены</option>
                  )
                : ordersAvailable.map((o) => (
                  <option key={o.id} value={String(o.id)}>
                    Заявка {o.order_number}
                  </option>
                ))}
          </Select>

          <Select
            label="Отгрузка на"
            value={destinationType}
            onChange={(e) => setDestinationType(e.target.value)}
          >
            <option value="WB">WB</option>
            <option value="OZON">OZON</option>
            <option value="Другое">Другое</option>
          </Select>

          <Input
            label="Дата поставки"
            type="date"
            value={deliveryDate}
            onChange={(e) => setDeliveryDate(e.target.value)}
          />

          <Input
            label="Комментарий"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />

          {!orderId ? (
            <p className="text-xs text-slate-500">Сначала выберите заявку со статусом «Готово к отгрузке».</p>
          ) : null}
          <Button onClick={handleCreate} disabled={create.isPending || !orderId}>
            {create.isPending ? "Создаю..." : "Создать"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}

function ShipmentCard({
  shipment,
  onDownloadFbo,
  onExportFboSend,
  downloadFboPending,
  exportFboPending,
  onImportFBO,
  importFboPending,
  onOpenFBO,
  onCreateFBO,
  onCreateFboPending,
  onUploadSupplyBarcode,
  onUploadBoxBarcodes,
  uploadSupplyPending,
  uploadBoxPending,
}: {
  shipment: ShippingRequest;
  onDownloadFbo?: () => void;
  onExportFboSend?: () => void;
  downloadFboPending?: boolean;
  exportFboPending?: boolean;
  onImportFBO?: () => void;
  importFboPending?: boolean;
  onOpenFBO?: () => void;
  onCreateFBO?: () => void;
  onCreateFboPending?: boolean;
  onUploadSupplyBarcode: (id: number) => void;
  onUploadBoxBarcodes: (id: number) => void;
  uploadSupplyPending: boolean;
  uploadBoxPending: boolean;
}) {
  const formatDate = (s: string | null) =>
    s ? new Date(s).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" }) : null;
  const hasOrder = Boolean(shipment.order_id);
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
      <div className="text-sm font-semibold text-slate-900">Отгрузка: {shipment.destination_type}</div>
      {shipment.order_number ? (
        <div className="text-xs text-slate-600">Заявка: {shipment.order_number}</div>
      ) : null}
      {shipment.warehouse_name ? (
        <div className="text-xs text-slate-600">Склад: {shipment.warehouse_name}</div>
      ) : null}
      {shipment.delivery_date ? (
        <div className="text-xs text-slate-600">Дата: {formatDate(shipment.delivery_date)}</div>
      ) : null}
      <div className="text-xs text-slate-500">Статус: {shipment.status}</div>
      {shipment.destination_comment ? (
        <div className="mt-1 text-xs text-slate-500">Комментарий: {shipment.destination_comment}</div>
      ) : null}

      {hasOrder ? (
        <div className="mt-3 rounded-lg border border-birka-200 bg-birka-50 p-3">
          <div className="text-xs font-semibold text-slate-800">Таблица отгрузки</div>
          <p className="mt-1.5 text-xs text-slate-600">
            ① Скачайте таблицу с данными упаковки.
          </p>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            {onDownloadFbo ? (
              <Button
                type="button"
                variant="primary"
                className="text-xs py-1.5 px-2"
                onClick={onDownloadFbo}
                disabled={downloadFboPending}
              >
                {downloadFboPending ? "Скачиваю…" : "Скачать таблицу"}
              </Button>
            ) : null}
            {onExportFboSend ? (
              <button
                type="button"
                className="text-xs text-birka-600 underline hover:no-underline"
                onClick={onExportFboSend}
                disabled={exportFboPending}
              >
                {exportFboPending ? "Отправляю…" : "Отправить в Telegram"}
              </button>
            ) : null}
          </div>
          <p className="mt-2 text-xs text-slate-600">
            ② Заполните столбцы: <strong>«Баркод короба»</strong>, <strong>«Склад»</strong>, <strong>«Дата поставки»</strong> — и сохраните файл.
          </p>
          <p className="mt-1.5 text-xs text-slate-600">
            ③ Загрузите заполненную таблицу обратно.
          </p>
          {onImportFBO ? (
            <Button
              type="button"
              variant="secondary"
              className="mt-1.5 text-xs py-1.5 px-2"
              onClick={onImportFBO}
              disabled={importFboPending}
            >
              {importFboPending ? "Загружаю…" : "Загрузить таблицу"}
            </Button>
          ) : null}
        </div>
      ) : (
        <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-2">
          <p className="text-xs text-slate-500">Заявка не привязана — привяжите заявку к отгрузке для работы с таблицей.</p>
        </div>
      )}

      <div className="mt-3 rounded-lg border border-slate-200 bg-amber-50/80 p-2">
        <div className="text-xs font-semibold text-slate-700">FBO поставка (WB/Ozon)</div>
        <p className="mt-0.5 text-xs text-slate-500">Для синхронизации штрихкодов коробов с маркетплейсом (по желанию).</p>
        <div className="mt-1.5 flex flex-wrap gap-2">
          {onOpenFBO ? (
            <button
              type="button"
              className="text-xs text-birka-600 underline"
              onClick={onOpenFBO}
            >
              Открыть
            </button>
          ) : null}
          {onCreateFBO ? (
            <Button
              type="button"
              variant="secondary"
              className="text-xs py-1.5 px-2"
              onClick={onCreateFBO}
              disabled={onCreateFboPending}
            >
              {onCreateFboPending ? "…" : "Создать"}
            </Button>
          ) : null}
        </div>
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
          <Button
            type="button"
            variant="secondary"
            className="text-xs py-1.5 px-2"
            onClick={() => onUploadSupplyBarcode(shipment.id)}
            disabled={uploadSupplyPending}
          >
            {uploadSupplyPending ? "..." : "Загрузить ШК поставки"}
          </Button>
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
          <Button
            type="button"
            variant="secondary"
            className="text-xs py-1.5 px-2"
            onClick={() => onUploadBoxBarcodes(shipment.id)}
            disabled={uploadBoxPending}
          >
            {uploadBoxPending ? "..." : "Загрузить ШК коробов"}
          </Button>
        )}
      </div>
    </div>
  );
}

function FBOSupplyDetailModal({
  supplyId,
  onClose,
}: {
  supplyId: number;
  onClose: () => void;
}) {
  const { data: supply, isLoading, refetch } = useFBOSupply(supplyId);
  const sync = useFBOSyncBarcodes(supplyId);
  const importBarcodes = useFBOImportBarcodes(supplyId);
  const boxStickers = useFBOBoxStickers(supplyId);
  const [barcodeText, setBarcodeText] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [stickersDataUrl, setStickersDataUrl] = useState<string[] | null>(null);
  const [exportPending, setExportPending] = useState(false);
  const [importExcelPending, setImportExcelPending] = useState(false);
  const importExcelInputRef = useRef<HTMLInputElement>(null);

  const handleDownloadExcel = async () => {
    setActionError(null);
    setExportPending(true);
    try {
      await downloadFile(`/fbo/supplies/${supplyId}/export`, "FBO_поставка_короба.xlsx");
      setActionSuccess("Файл скачан");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Ошибка скачивания");
    } finally {
      setExportPending(false);
    }
  };

  const handleImportExcelChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setActionError(null);
    setActionSuccess(null);
    setImportExcelPending(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await apiClient.apiForm<unknown>(`/fbo/supplies/${supplyId}/import`, formData);
      await refetch();
      setActionSuccess("Короба обновлены из файла");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Ошибка загрузки файла");
    } finally {
      setImportExcelPending(false);
    }
  };

  const handleGetStickers = () => {
    setActionError(null);
    setStickersDataUrl(null);
    boxStickers.mutate("png", {
      onSuccess: (data) => {
        const urls = (data.stickers ?? [])
          .filter((s) => s.file_base64)
          .map((s) => `data:${s.content_type};base64,${s.file_base64}`);
        setStickersDataUrl(urls);
      },
      onError: (err) => {
        setActionError(err instanceof Error ? err.message : "Ошибка загрузки стикеров");
      },
    });
  };

  const handleImport = () => {
    const barcodes = barcodeText
      .split(/[\n,;\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (barcodes.length === 0) return;
    setActionError(null);
    setActionSuccess(null);
    importBarcodes.mutate(barcodes, {
      onSuccess: () => {
        setBarcodeText("");
        setActionSuccess("Штрихкоды импортированы");
      },
      onError: (err) => {
        setActionError(err instanceof Error ? err.message : "Ошибка импорта");
      },
    });
  };

  const handleSync = () => {
    setActionError(null);
    setActionSuccess(null);
    sync.mutate(undefined, {
      onSuccess: () => {
        setActionSuccess("Короба синхронизированы из маркетплейса");
      },
      onError: (err) => {
        setActionError(err instanceof Error ? err.message : "Ошибка синхронизации");
      },
    });
  };

  return (
    <Modal title="FBO поставка" open onClose={onClose}>
      <div className="space-y-3">
        {isLoading ? (
          <div className="text-sm text-slate-500">Загрузка...</div>
        ) : supply ? (
          <>
            <div className="rounded-lg border border-birka-200 bg-birka-50 p-2 text-xs text-slate-700">
              <div className="font-semibold text-slate-800">Ручной режим (без API)</div>
              <ol className="mt-1 list-inside list-decimal space-y-0.5">
                <li>Скачайте Excel с текущими коробами.</li>
                <li>Заполните столбец «Штрихкод» и при необходимости добавьте строки.</li>
                <li>Загрузите файл обратно — короба обновятся.</li>
              </ol>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  className="text-xs py-1.5 px-2"
                  disabled={exportPending}
                  onClick={handleDownloadExcel}
                >
                  {exportPending ? "Скачиваю..." : "Скачать Excel"}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  className="text-xs py-1.5 px-2"
                  disabled={importExcelPending}
                  onClick={() => importExcelInputRef.current?.click()}
                >
                  {importExcelPending ? "Загружаю..." : "Загрузить Excel"}
                </Button>
                <input
                  ref={importExcelInputRef}
                  type="file"
                  accept=".xlsx,.xls"
                  className="hidden"
                  onChange={handleImportExcelChange}
                />
              </div>
            </div>
            <div className="text-sm text-slate-700">
              Маркетплейс: {supply.marketplace.toUpperCase()} · Статус: {supply.status}
              {supply.external_supply_id ? ` · ID: ${supply.external_supply_id}` : null}
            </div>
            {!supply.external_supply_id && (
              <p className="text-xs text-amber-700 bg-amber-50 rounded p-2">
                Создайте поставку в кабинете WB/Ozon или дождитесь авто-создания при отгрузке.
              </p>
            )}
            <div className="text-xs font-medium text-slate-600">Короба ({supply.boxes.length})</div>
            <ul className="max-h-32 overflow-y-auto rounded border border-slate-200 bg-slate-50 p-2 text-xs">
              {supply.boxes.length === 0 ? (
                <li className="text-slate-500">Нет штрихкодов. Синхронизируйте или введите вручную.</li>
              ) : (
                supply.boxes.map((b) => (
                  <li key={b.id}>
                    №{b.box_number}: {b.external_box_id ? `ID: ${b.external_box_id}` : ""}
                    {b.external_box_id && b.external_barcode ? " · " : ""}
                    {b.external_barcode ? `ШК: ${b.external_barcode}` : ""}
                    {!b.external_box_id && !b.external_barcode ? "—" : null}
                  </li>
                ))
              )}
            </ul>
            {actionError ? (
              <p className="text-xs text-red-600 bg-red-50 rounded p-2">{actionError}</p>
            ) : null}
            {actionSuccess ? (
              <p className="text-xs text-emerald-700 bg-emerald-50 rounded p-2">{actionSuccess}</p>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                className="text-xs py-1.5 px-2"
                disabled={sync.isPending || !supply.external_supply_id}
                onClick={handleSync}
              >
                {sync.isPending ? "Синхронизация..." : "Синхронизировать короба из маркетплейса"}
              </Button>
              {supply.marketplace === "wb" &&
                supply.boxes.some((b) => b.external_box_id) && (
                  <Button
                    variant="secondary"
                    className="text-xs py-1.5 px-2"
                    disabled={boxStickers.isPending}
                    onClick={handleGetStickers}
                  >
                    {boxStickers.isPending ? "Загрузка..." : "Получить стикеры коробов"}
                  </Button>
                )}
            </div>
            {stickersDataUrl && stickersDataUrl.length > 0 && (
              <div className="rounded border border-slate-200 bg-slate-50 p-2">
                <div className="text-xs font-medium text-slate-600 mb-1">Стикеры для печати</div>
                <div className="flex flex-wrap gap-2">
                  {stickersDataUrl.map((url, i) => (
                    <img key={i} src={url} alt={`Стикер ${i + 1}`} className="max-h-24 object-contain" />
                  ))}
                </div>
              </div>
            )}
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">
                Ручной ввод ШК (по одному в строку)
              </label>
              <textarea
                className="w-full rounded border border-slate-300 p-2 text-sm"
                rows={3}
                placeholder="WB-123..."
                value={barcodeText}
                onChange={(e) => setBarcodeText(e.target.value)}
              />
              <Button
                variant="primary"
                className="mt-1 text-xs py-1.5 px-2"
                disabled={importBarcodes.isPending || !barcodeText.trim()}
                onClick={handleImport}
              >
                {importBarcodes.isPending ? "Импорт..." : "Импортировать"}
              </Button>
            </div>
          </>
        ) : null}
      </div>
    </Modal>
  );
}

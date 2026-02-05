import { useRef, useEffect, useState } from "react";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { Select } from "../../components/ui/Select";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useDestinations } from "../../hooks/useDestinations";
import {
  useFBOSupply,
  useFBOImportBarcodes,
  useFBOSyncBarcodes,
} from "../../hooks/useFBOSupplies";
import {
  useOrdersReadyForShipping,
  useShipping,
} from "../../hooks/useShipping";
import type { FBOSupply, ShippingRequest } from "../../types";

export function ShippingPage() {
  const { items: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
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
  } = useShipping(activeCompanyId ?? undefined, page, limit);
  const { data: ordersReady = [], isLoading: ordersReadyLoading } =
    useOrdersReadyForShipping(activeCompanyId ?? undefined);
  const { items: destinations = [] } = useDestinations(true);

  const [open, setOpen] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);
  const [destinationType, setDestinationType] = useState("WB");
  const [orderId, setOrderId] = useState<string>("");
  const [warehouseName, setWarehouseName] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [comment, setComment] = useState("");
  const [fboSupplyId, setFboSupplyId] = useState<number | null>(null);

  const supplyBarcodeInputRef = useRef<HTMLInputElement>(null);
  const boxBarcodesInputRef = useRef<HTMLInputElement>(null);

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
        Сначала добавьте компанию, чтобы создавать отгрузки.
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const handleCreate = async () => {
    if (!activeCompanyId) return;
    setPageError(null);
    try {
      await create.mutateAsync({
        company_id: activeCompanyId,
        order_id: orderId ? Number(orderId) : undefined,
        destination_type: destinationType,
        destination_comment: comment.trim() || undefined,
        warehouse_name: warehouseName.trim() || undefined,
        delivery_date: deliveryDate || undefined,
      });
      setOpen(false);
      setComment("");
      setOrderId("");
      setWarehouseName("");
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

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />
      <div className="flex items-center justify-between gap-2">
        <Button onClick={() => setOpen(true)}>Создать отгрузку</Button>
        {pageError ? <div className="text-sm text-rose-500">{pageError}</div> : null}
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
          Пока нет заявок на отгрузку.
        </div>
      ) : null}

      <div className="space-y-3">
        {items.map((shipment) => (
          <ShipmentCard
            key={shipment.id}
            shipment={shipment}
            onOpenFBO={
              shipment.fbo_supply_id ? () => setFboSupplyId(shipment.fbo_supply_id!) : undefined
            }
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

      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />

      <Modal title="Новая отгрузка" open={open} onClose={() => setOpen(false)}>
        <div className="space-y-3">
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
              : ordersReady.map((o) => (
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

          {destinationType === "Другое" ? (
            <Input
              label="Склад назначения (или куда отгружаем)"
              value={warehouseName}
              onChange={(e) => setWarehouseName(e.target.value)}
            />
          ) : (
            <Select
              label="Склад назначения"
              value={warehouseName}
              onChange={(e) => setWarehouseName(e.target.value)}
            >
              <option value="">— Выберите склад —</option>
              {destinations.map((d) => (
                <option key={d.id} value={d.name}>
                  {d.name}
                </option>
              ))}
            </Select>
          )}

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

          <Button onClick={handleCreate} disabled={create.isPending}>
            {create.isPending ? "Создаю..." : "Создать"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}

function ShipmentCard({
  shipment,
  onOpenFBO,
  onUploadSupplyBarcode,
  onUploadBoxBarcodes,
  uploadSupplyPending,
  uploadBoxPending,
}: {
  shipment: ShippingRequest;
  onOpenFBO?: () => void;
  onUploadSupplyBarcode: (id: number) => void;
  onUploadBoxBarcodes: (id: number) => void;
  uploadSupplyPending: boolean;
  uploadBoxPending: boolean;
}) {
  const formatDate = (s: string | null) =>
    s ? new Date(s).toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit", year: "numeric" }) : null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
      <div className="text-sm font-semibold text-slate-900">Отгрузка: {shipment.destination_type}</div>
      {shipment.order_number ? (
        <div className="text-xs text-slate-600">Заявка: {shipment.order_number}</div>
      ) : null}
      {onOpenFBO ? (
        <div className="mt-1">
          <button
            type="button"
            className="text-xs text-birka-600 underline"
            onClick={onOpenFBO}
          >
            FBO поставка
          </button>
        </div>
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
  const { data: supply, isLoading } = useFBOSupply(supplyId);
  const sync = useFBOSyncBarcodes(supplyId);
  const importBarcodes = useFBOImportBarcodes(supplyId);
  const [barcodeText, setBarcodeText] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const handleImport = () => {
    const barcodes = barcodeText
      .split(/[\n,;\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (barcodes.length === 0) return;
    setActionError(null);
    importBarcodes.mutate(barcodes, {
      onSuccess: () => {
        setBarcodeText("");
      },
      onError: (err) => {
        setActionError(err instanceof Error ? err.message : "Ошибка импорта");
      },
    });
  };

  const handleSync = () => {
    setActionError(null);
    sync.mutate(undefined, {
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
            <div className="text-sm text-slate-700">
              Маркетплейс: {supply.marketplace.toUpperCase()} · Статус: {supply.status}
              {supply.external_supply_id ? ` · ID: ${supply.external_supply_id}` : null}
            </div>
            <div className="text-xs font-medium text-slate-600">Короба ({supply.boxes.length})</div>
            <ul className="max-h-32 overflow-y-auto rounded border border-slate-200 bg-slate-50 p-2 text-xs">
              {supply.boxes.length === 0 ? (
                <li className="text-slate-500">Нет штрихкодов</li>
              ) : (
                supply.boxes.map((b) => (
                  <li key={b.id}>
                    №{b.box_number}: {b.external_barcode ?? "—"}
                  </li>
                ))
              )}
            </ul>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="secondary"
                className="text-xs py-1.5 px-2"
                disabled={sync.isPending || !supply.external_supply_id}
                onClick={handleSync}
              >
                {sync.isPending ? "Синхронизация..." : "Синхронизировать ШК из маркетплейса"}
              </Button>
            </div>
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

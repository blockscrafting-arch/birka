import { useCallback, useRef, useState } from "react";

import { BarcodeScanner } from "../../components/shared/BarcodeScanner";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { SCAN_WARNING_NOT_IN_ORDER, getCameraErrorMessage } from "../../constants/scanner";
import { useScanFeedback } from "../../hooks/useScanFeedback";
import { OrderItem } from "../../types";

const SCAN_DEBOUNCE_MS = 500;

type ReceivingFormProps = {
  items: OrderItem[];
  defectPhotosByProduct?: Record<number, number>;
  isSubmitting?: boolean;
  onSubmit: (payload: {
    order_item_id: number;
    received_qty: number;
    defect_qty: number;
    adjustment_qty: number;
    adjustment_note?: string;
  }) => void;
  onSelectItem?: (itemId: number | null) => void;
};

export function ReceivingForm({
  items,
  defectPhotosByProduct = {},
  isSubmitting,
  onSubmit,
  onSelectItem,
}: ReceivingFormProps) {
  const [itemId, setItemId] = useState("");
  const [received, setReceived] = useState("0");
  const [defect, setDefect] = useState("0");
  const [adjustment, setAdjustment] = useState("0");
  const [adjustmentNote, setAdjustmentNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [pieceByPieceMode, setPieceByPieceMode] = useState(false);
  const [scanWarning, setScanWarning] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const lastScannedRef = useRef({ barcode: "", time: 0 });
  const { playSuccess, playWarning } = useScanFeedback();

  const selected = items.find((item) => item.id === Number(itemId));

  const handleScan = useCallback(
    (text: string) => {
      setCameraError(null);
      setScanWarning(null);
      const now = Date.now();
      const sameAsLast = lastScannedRef.current.barcode === text && now - lastScannedRef.current.time < SCAN_DEBOUNCE_MS;

      if (pieceByPieceMode && selected && String(selected.barcode ?? "") === text) {
        lastScannedRef.current = { barcode: text, time: now };
        setReceived((prev) => String(Number(prev) + 1));
        playSuccess();
        return;
      }

      if (pieceByPieceMode && selected && sameAsLast) return;
      lastScannedRef.current = { barcode: text, time: now };

      const item = items.find((i) => (i.barcode ?? "").trim() === text.trim());
      if (item) {
        setItemId(String(item.id));
        onSelectItem?.(item.id);
        if (pieceByPieceMode) setReceived("1");
        playSuccess();
      } else {
        setScanWarning("ШК не найден в позициях заявки");
        playWarning();
      }
    },
    [items, pieceByPieceMode, selected, onSelectItem, playSuccess, playWarning]
  );

  const handleScannerError = useCallback((msg: string) => {
    setCameraError(getCameraErrorMessage(msg));
  }, []);

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        setError(null);
        if (!itemId) {
          setError("Выберите позицию");
          return;
        }
        const receivedQty = Number(received);
        const defectQty = Number(defect);
        if (Number.isNaN(receivedQty) || receivedQty < 0) {
          setError("Введите корректное количество");
          return;
        }
        if (Number.isNaN(defectQty) || defectQty < 0) {
          setError("Введите корректный брак");
          return;
        }
        const adjustmentQty = Number(adjustment);
        if (Number.isNaN(adjustmentQty) || adjustmentQty < 0) {
          setError("Введите корректное списание");
          return;
        }
        onSubmit({
          order_item_id: Number(itemId),
          received_qty: receivedQty,
          defect_qty: defectQty,
          adjustment_qty: adjustmentQty,
          adjustment_note: adjustmentNote.trim() || undefined,
        });
      }}
    >
      {items.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700 shadow-soft">
          В этой заявке нет позиций для приёмки.
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Select
              label="Позиция"
              value={itemId}
              onChange={(e) => {
                const nextValue = e.target.value;
                setItemId(nextValue);
                onSelectItem?.(nextValue ? Number(nextValue) : null);
              }}
            >
              <option value="" disabled>
                Выберите позицию
              </option>
              {items.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.product_name} · План {item.planned_qty}
                </option>
              ))}
            </Select>
            <Button type="button" variant="ghost" onClick={() => setScannerOpen((p) => !p)}>
              {scannerOpen ? "Закрыть сканер" : "Сканировать ШК"}
            </Button>
          </div>
          {scannerOpen ? (
            <>
              <BarcodeScanner
                compact
                active={scannerOpen}
                onScan={handleScan}
                onError={handleScannerError}
              />
              {cameraError ? (
                <div className="rounded-lg border-2 border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
                  {cameraError}
                </div>
              ) : null}
            </>
          ) : null}
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={pieceByPieceMode}
              onChange={(e) => setPieceByPieceMode(e.target.checked)}
            />
            Поштучный режим (каждый скан +1 к количеству)
          </label>
          {scanWarning ? (
            <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              {scanWarning}
            </div>
          ) : null}
        </div>
      )}

      {selected ? (
        <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
          <div>
            ШК: {selected.barcode ?? "—"} · План: {selected.planned_qty} · Принято: {selected.received_qty}
          </div>
          <Button type="button" variant="ghost" onClick={() => setShowDetails((prev) => !prev)}>
            {showDetails ? "Скрыть карточку товара" : "Показать карточку товара"}
          </Button>
          {showDetails ? (
            <div className="space-y-1">
              <div>Бренд: {selected.brand ?? "—"}</div>
              <div>Размер: {selected.size ?? "—"}</div>
              <div>Цвет: {selected.color ?? "—"}</div>
              <div>Артикул WB: {selected.wb_article ?? "—"}</div>
              <div>Ссылка WB: {selected.wb_url ?? "—"}</div>
              <div>ТЗ: {selected.packing_instructions ?? "—"}</div>
              <div>Поставщик: {selected.supplier_name ?? "—"}</div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-1">
        <Input
          label="Фактическое количество"
          inputMode="numeric"
          value={received}
          onChange={(e) => setReceived(e.target.value)}
        />
        {pieceByPieceMode && selected ? (
          <div className="text-xs text-slate-500">
            При поштучном режиме: отсканировано {received} шт.
          </div>
        ) : null}
      </div>
      <Input label="Брак" inputMode="numeric" value={defect} onChange={(e) => setDefect(e.target.value)} />
      {selected && Number(defect) > 0 ? (
        (() => {
          const count = defectPhotosByProduct[selected.product_id] ?? 0;
          const needPhoto = count === 0;
          return (
            <div className={needPhoto ? "text-amber-600 text-sm" : "text-slate-600 text-sm"}>
              {needPhoto ? "Нужно фото брака для этой позиции" : `Фото брака: ${count} шт.`}
            </div>
          );
        })()
      ) : null}
      <Input
        label="Списание (фотосессия и др.)"
        inputMode="numeric"
        value={adjustment}
        onChange={(e) => setAdjustment(e.target.value)}
      />
      <Input
        label="Комментарий к списанию"
        value={adjustmentNote}
        onChange={(e) => setAdjustmentNote(e.target.value)}
      />
      {error ? <div className="text-sm text-rose-500">{error}</div> : null}
      {(() => {
        const defectQty = Number(defect);
        const needDefectPhoto =
          selected &&
          !Number.isNaN(defectQty) &&
          defectQty > 0 &&
          (defectPhotosByProduct[selected.product_id] ?? 0) === 0;
        return (
          <Button
            type="submit"
            disabled={isSubmitting || items.length === 0 || needDefectPhoto}
          >
            Завершить приёмку
          </Button>
        );
      })()}
    </form>
  );
}

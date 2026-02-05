import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { BarcodeScanner } from "../../components/shared/BarcodeScanner";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useOrders } from "../../hooks/useOrders";
import { useWarehouse } from "../../hooks/useWarehouse";

const DEBOUNCE_MS = 2000;
const MAX_HISTORY = 50;

export function ScannerPage() {
  const { companyId } = useActiveCompany();
  const { items: companies = [] } = useCompanies();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const { items: orders = [] } = useOrders(activeCompanyId ?? undefined, 1, 100);
  const { validateBarcode, validateBarcodeInOrder } = useWarehouse();

  const [active, setActive] = useState(false);
  const [orderId, setOrderId] = useState<number | null>(null);
  const [result, setResult] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"ok" | "error" | null>(null);
  const [orderContextMessage, setOrderContextMessage] = useState<string | null>(null);
  const [orderContextFound, setOrderContextFound] = useState<boolean | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [product, setProduct] = useState<{
    id: number;
    name: string;
    brand?: string | null;
    size?: string | null;
    color?: string | null;
    wb_article?: string | null;
    barcode?: string | null;
  } | null>(null);
  const [box, setBox] = useState<{
    id: number;
    box_number: number;
    supply_id: number;
    external_box_id?: string | null;
    external_barcode?: string | null;
  } | null>(null);
  const [scanHistory, setScanHistory] = useState<string[]>([]);
  const lastScannedRef = useRef<string>("");
  const lastScanTimeRef = useRef<number>(0);

  const handleError = useCallback((msg: string) => {
    setCameraError(getCameraErrorMessage(msg));
  }, []);

  useEffect(() => {
    if (!active) setCameraError(null);
  }, [active]);

  const handleScan = useCallback(
    async (text: string) => {
      const now = Date.now();
      if (text === lastScannedRef.current && now - lastScanTimeRef.current < DEBOUNCE_MS) {
        return;
      }
      lastScannedRef.current = text;
      lastScanTimeRef.current = now;
      setCameraError(null);
      setOrderContextMessage(null);
      setOrderContextFound(null);
      setResult(text);
      setStatus(null);
      setProduct(null);
      setBox(null);

      setScanHistory((prev) => [...prev.slice(-(MAX_HISTORY - 1)), text]);

      if (orderId) {
        try {
          const inOrder = await validateBarcodeInOrder.mutateAsync({ barcode: text, order_id: orderId });
          setOrderContextFound(inOrder.found);
          setOrderContextMessage(inOrder.message);
        } catch {
          setOrderContextFound(false);
          setOrderContextMessage("Ошибка проверки в заявке");
        }
      }

      try {
        const response = await validateBarcode.mutateAsync({ barcode: text });
        setMessage(response.message);
        setStatus(response.valid ? "ok" : "error");
        setProduct(response.product ?? null);
        setBox(response.box ?? null);
      } catch {
        setMessage("Ошибка проверки штрихкода");
        setStatus("error");
      }
    },
    [orderId, validateBarcode, validateBarcodeInOrder]
  );

  const historyStats = useMemo(() => {
    const total = scanHistory.length;
    const unique = new Set(scanHistory).size;
    return { total, unique };
  }, [scanHistory]);

  const clearHistory = useCallback(() => {
    setScanHistory([]);
  }, []);

  return (
    <div className="space-y-3">
      {activeCompanyId && orders.length > 0 ? (
        <Select
          label="Заявка (для проверки ШК)"
          value={orderId ?? ""}
          onChange={(e) => setOrderId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Без заявки</option>
          {orders.map((o) => (
            <option key={o.id} value={o.id}>
              {o.order_number}
            </option>
          ))}
        </Select>
      ) : null}

      <Button onClick={() => setActive((prev) => !prev)}>
        {active ? "Остановить сканер" : "Открыть сканер"}
      </Button>
      {active ? (
        <>
          <BarcodeScanner active={active} onScan={handleScan} onError={handleError} />
          {cameraError ? (
            <div
              className="rounded-lg border-2 border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800"
              role="alert"
              aria-live="polite"
            >
              {cameraError}
            </div>
          ) : null}
        </>
      ) : null}

      {orderContextMessage != null && orderId ? (
        <div
          className={`rounded-lg border-2 px-4 py-3 text-sm ${
            orderContextFound
              ? "border-emerald-300 bg-emerald-50 text-emerald-800"
              : "border-amber-300 bg-amber-50 text-amber-800"
          }`}
        >
          {orderContextMessage}
        </div>
      ) : null}

      {scanHistory.length > 0 ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          <span>Отсканировано: {historyStats.total} шт., {historyStats.unique} уникальных ШК</span>
          <Button type="button" variant="ghost" className="ml-2" onClick={clearHistory}>
            Очистить историю
          </Button>
        </div>
      ) : null}

      {result ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Отсканировано</div>
          <div className="mt-1 break-all text-lg font-mono font-semibold text-slate-900">{result}</div>
        </div>
      ) : null}
      {message ? <div className="text-sm text-slate-600">{message}</div> : null}
      {status ? (
        <div
          className={`rounded-lg border-2 px-4 py-3 text-sm font-semibold ${
            status === "ok"
              ? "border-emerald-300 bg-emerald-50 text-emerald-800"
              : "border-rose-300 bg-rose-50 text-rose-800"
          }`}
          role="status"
        >
          {status === "ok" ? "✓ Штрихкод найден в базе" : "✗ Штрихкод не найден"}
        </div>
      ) : null}
      {product ? (
        <div className="rounded-xl border-2 border-slate-200 bg-white p-4 shadow-soft">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Товар в базе</div>
          <div className="mt-2 font-semibold text-slate-900">{product.name}</div>
          <div className="mt-1 text-sm text-slate-700">ШК: {product.barcode ?? "—"}</div>
          <div className="mt-0.5 text-sm text-slate-700">Артикул WB: {product.wb_article ?? "—"}</div>
          <div className="mt-1 text-sm text-slate-600">
            {[product.brand, product.size, product.color].filter(Boolean).join(" · ") || "—"}
          </div>
        </div>
      ) : null}
      {box ? (
        <div className="rounded-xl border-2 border-slate-200 bg-white p-4 shadow-soft">
          <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">Короб FBO</div>
          <div className="mt-2 font-semibold text-slate-900">Короб №{box.box_number}</div>
          <div className="mt-1 text-sm text-slate-700">ID поставки: {box.supply_id}</div>
          <div className="mt-0.5 text-sm text-slate-700">Внешний ID: {box.external_box_id ?? "—"}</div>
          <div className="mt-1 text-sm text-slate-600">ШК: {box.external_barcode ?? "—"}</div>
        </div>
      ) : null}
    </div>
  );
}

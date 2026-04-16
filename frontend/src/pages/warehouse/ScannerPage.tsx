import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { BarcodeScanner } from "../../components/shared/BarcodeScanner";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useOrders } from "../../hooks/useOrders";
import { useWarehouse } from "../../hooks/useWarehouse";
import { getCameraErrorMessage, isScanFrameError } from "../../constants/scanner";

const THROTTLE_MS = 800;
const DEBOUNCE_MS = 15000;
const MAX_HISTORY = 50;
/** Сколько секунд держать зелёную подсветку области сканера после успешного скана (библиотека мигает только на кадр). */
const SUCCESS_HIGHLIGHT_SEC = 5;

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
  const [showSuccessHighlight, setShowSuccessHighlight] = useState(false);
  const [readabilityOk, setReadabilityOk] = useState(false);
  const [noScanTimeout, setNoScanTimeout] = useState(false);
  const lastScannedRef = useRef<string>("");
  const lastScanTimeRef = useRef<number>(0);
  const lastAcceptedScanTimeRef = useRef<number>(0);
  const successHighlightTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const noScanTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const NO_SCAN_HINT_SEC = 8;

  const handleError = useCallback((msg: string) => {
    if (isScanFrameError(msg)) return;
    setCameraError(getCameraErrorMessage(msg));
  }, []);

  useEffect(() => {
    if (!active) {
      setCameraError(null);
      setNoScanTimeout(false);
      setReadabilityOk(false);
      if (noScanTimeoutRef.current) {
        clearTimeout(noScanTimeoutRef.current);
        noScanTimeoutRef.current = null;
      }
      return;
    }
    setReadabilityOk(false);
    setNoScanTimeout(false);
    noScanTimeoutRef.current = setTimeout(() => {
      setNoScanTimeout(true);
      noScanTimeoutRef.current = null;
    }, NO_SCAN_HINT_SEC * 1000);
    return () => {
      if (noScanTimeoutRef.current) {
        clearTimeout(noScanTimeoutRef.current);
        noScanTimeoutRef.current = null;
      }
    };
  }, [active]);

  const handleScan = useCallback(
    async (text: string) => {
      const now = Date.now();
      const normalized = (text ?? "").trim();
      if (normalized === "") return;
      if (noScanTimeoutRef.current) {
        clearTimeout(noScanTimeoutRef.current);
        noScanTimeoutRef.current = null;
      }
      setNoScanTimeout(false);
      setReadabilityOk(true);
      if (now - lastAcceptedScanTimeRef.current < THROTTLE_MS) return;
      if (normalized === lastScannedRef.current && now - lastScanTimeRef.current < DEBOUNCE_MS) return;
      lastScannedRef.current = normalized;
      lastScanTimeRef.current = now;
      lastAcceptedScanTimeRef.current = now;
      setCameraError(null);
      setOrderContextMessage(null);
      setOrderContextFound(null);
      setResult(normalized);
      setStatus(null);
      setProduct(null);
      setBox(null);
      setShowSuccessHighlight(false);

      setScanHistory((prev) => [...prev.slice(-(MAX_HISTORY - 1)), normalized]);

      if (orderId) {
        try {
          const inOrder = await validateBarcodeInOrder.mutateAsync({
            barcode: normalized,
            order_id: orderId,
          });
          setOrderContextFound(inOrder.found);
          setOrderContextMessage(inOrder.message);
        } catch {
          setOrderContextFound(false);
          setOrderContextMessage("Ошибка проверки в заявке");
        }
      }

      try {
        const response = await validateBarcode.mutateAsync({
          barcode: normalized,
          company_id: activeCompanyId ?? undefined,
          order_id: orderId ?? undefined,
        });
        setMessage(response.message);
        setStatus(response.valid ? "ok" : "error");
        setProduct(response.product ?? null);
        setBox(response.box ?? null);
        if (response.valid) {
          if (successHighlightTimeoutRef.current) clearTimeout(successHighlightTimeoutRef.current);
          setShowSuccessHighlight(true);
          successHighlightTimeoutRef.current = setTimeout(() => {
            setShowSuccessHighlight(false);
            successHighlightTimeoutRef.current = null;
          }, SUCCESS_HIGHLIGHT_SEC * 1000);
        }
      } catch {
        setMessage("Ошибка проверки штрихкода");
        setStatus("error");
      }
    },
    [orderId, activeCompanyId, validateBarcode, validateBarcodeInOrder]
  );

  useEffect(() => {
    return () => {
      if (successHighlightTimeoutRef.current) clearTimeout(successHighlightTimeoutRef.current);
    };
  }, []);

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
      <style>{`
        #qr-shaded-region > div { display: none !important; }
        #qr-shaded-region { box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.5) !important; }
      `}</style>
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
          <p className="text-sm text-slate-600">
            Наведите на штрихкод. Если ШК не сканируется — проверьте печать и освещение.
          </p>
          {noScanTimeout ? (
            <div
              className="rounded-lg border-2 border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800"
              role="status"
            >
              ШК не распознаётся. Проверьте качество печати и освещение.
            </div>
          ) : null}
          <div className="relative rounded-lg">
            <div
              className={
                showSuccessHighlight
                  ? "relative z-0 rounded-lg ring-4 ring-emerald-500 ring-offset-2 transition-all duration-200"
                  : "relative z-0 rounded-lg ring-4 ring-transparent ring-offset-2 transition-all duration-200"
              }
            >
              <BarcodeScanner active={active} onScan={handleScan} onError={handleError} />
            </div>
            {showSuccessHighlight ? (
              <div
                className="absolute inset-0 z-10 rounded-lg border-4 border-emerald-500 bg-emerald-500/15 pointer-events-none"
                aria-hidden
              />
            ) : null}
          </div>
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

      {readabilityOk && result ? (
        <div className="rounded-lg border-2 border-emerald-300 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800" role="status">
          ШК читается
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

import { useCallback, useEffect, useRef, useState } from "react";

import { BarcodeScanner } from "../../components/shared/BarcodeScanner";
import { Button } from "../../components/ui/Button";
import { useWarehouse } from "../../hooks/useWarehouse";

const DEBOUNCE_MS = 2000;

export function ScannerPage() {
  const [active, setActive] = useState(false);
  const [result, setResult] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"ok" | "error" | null>(null);
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
  const { validateBarcode } = useWarehouse();
  const lastScannedRef = useRef<string>("");
  const lastScanTimeRef = useRef<number>(0);

  const handleError = useCallback((msg: string) => {
    if (msg.includes("NotAllowedError") || msg.includes("Permission") || msg.includes("NotAllowed")) {
      setCameraError("Разрешите доступ к камере в настройках браузера");
    } else if (msg.includes("NotFoundError") || msg.includes("NotFound")) {
      setCameraError("Камера не найдена");
    } else if (msg.includes("NotReadableError") || msg.includes("NotReadable")) {
      setCameraError("Камера занята или недоступна");
    } else {
      const short = String(msg).slice(0, 80);
      setCameraError(short ? `Ошибка сканера: ${short}${String(msg).length > 80 ? "…" : ""}` : "Ошибка сканера");
    }
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
      setResult(text);
      setStatus(null);
      setProduct(null);
      try {
        const response = await validateBarcode.mutateAsync({ barcode: text });
        setMessage(response.message);
        setStatus(response.valid ? "ok" : "error");
        setProduct(response.product ?? null);
      } catch {
        setMessage("Ошибка проверки штрихкода");
        setStatus("error");
      }
    },
    [validateBarcode]
  );

  return (
    <div className="space-y-3">
      <Button onClick={() => setActive((prev) => !prev)}>
        {active ? "Остановить сканер" : "Открыть сканер"}
      </Button>
      {active ? (
        <>
          <BarcodeScanner onScan={handleScan} onError={handleError} />
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
    </div>
  );
}

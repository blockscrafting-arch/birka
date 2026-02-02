import { useState } from "react";

import { BarcodeScanner } from "../../components/shared/BarcodeScanner";
import { Button } from "../../components/ui/Button";
import { useWarehouse } from "../../hooks/useWarehouse";

export function ScannerPage() {
  const [active, setActive] = useState(false);
  const [result, setResult] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<"ok" | "error" | null>(null);
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

  return (
    <div className="space-y-3">
      <Button onClick={() => setActive((prev) => !prev)}>
        {active ? "Остановить сканер" : "Открыть сканер"}
      </Button>
      {active ? (
        <BarcodeScanner
          onScan={async (text) => {
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
          }}
          onError={() => undefined}
        />
      ) : null}
      {result ? (
        <div className="rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-700 shadow-soft">
          Результат: {result}
        </div>
      ) : null}
      {message ? <div className="text-xs text-slate-500">{message}</div> : null}
      {status ? (
        <div
          className={`rounded-lg border px-3 py-2 text-xs font-semibold ${
            status === "ok"
              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
              : "border-rose-200 bg-rose-50 text-rose-700"
          }`}
        >
          {status === "ok" ? "Штрихкод корректен" : "Штрихкод не найден"}
        </div>
      ) : null}
      {product ? (
        <div className="rounded-xl border border-slate-200 bg-white p-3 text-xs text-slate-700 shadow-soft">
          <div className="font-semibold text-slate-900">{product.name}</div>
          <div>ШК: {product.barcode ?? "—"}</div>
          <div>Артикул WB: {product.wb_article ?? "—"}</div>
          <div>
            {product.brand ? `Бренд: ${product.brand}` : null}
            {product.size ? ` | Размер: ${product.size}` : null}
            {product.color ? ` | Цвет: ${product.color}` : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

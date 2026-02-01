import { useState } from "react";

import { BarcodeScanner } from "../../components/shared/BarcodeScanner";
import { Button } from "../../components/ui/Button";
import { useWarehouse } from "../../hooks/useWarehouse";

export function ScannerPage() {
  const [active, setActive] = useState(false);
  const [result, setResult] = useState("");
  const [message, setMessage] = useState("");
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
            try {
              const response = await validateBarcode.mutateAsync({ barcode: text });
              setMessage(response.message);
            } catch {
              setMessage("Ошибка проверки штрихкода");
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
    </div>
  );
}

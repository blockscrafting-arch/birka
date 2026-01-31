import { useState } from "react";

import { BarcodeScanner } from "../../components/shared/BarcodeScanner";
import { Button } from "../../components/ui/Button";

export function ScannerPage() {
  const [active, setActive] = useState(false);
  const [result, setResult] = useState("");

  return (
    <div className="space-y-3">
      <Button onClick={() => setActive((prev) => !prev)}>
        {active ? "Остановить сканер" : "Открыть сканер"}
      </Button>
      {active ? (
        <BarcodeScanner onScan={(text) => setResult(text)} onError={() => undefined} />
      ) : null}
      {result ? <div className="rounded bg-white p-3 text-sm">Результат: {result}</div> : null}
    </div>
  );
}

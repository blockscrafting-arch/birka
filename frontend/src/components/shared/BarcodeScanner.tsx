import { useEffect, useRef } from "react";
import { Html5Qrcode } from "html5-qrcode";

type BarcodeScannerProps = {
  onScan: (text: string) => void;
  onError?: (message: string) => void;
  /** Компактный режим: меньшая область сканирования, встраивается в форму */
  compact?: boolean;
  /** Управление камерой: true — запустить, false — остановить. По умолчанию true (старт при mount). */
  active?: boolean;
};

export function BarcodeScanner({ onScan, onError, compact = false, active = true }: BarcodeScannerProps) {
  const scannerId = useRef(`scanner-${Math.random().toString(36).slice(2)}`);
  const onScanRef = useRef(onScan);
  const onErrorRef = useRef(onError);
  const scannerRef = useRef<Html5Qrcode | null>(null);

  useEffect(() => {
    onScanRef.current = onScan;
    onErrorRef.current = onError;
  });

  useEffect(() => {
    if (!active) {
      const prev = scannerRef.current;
      if (prev) {
        prev.stop().catch(() => undefined);
        scannerRef.current = null;
      }
      return;
    }

    const id = scannerId.current;
    const scanner = new Html5Qrcode(id);
    scannerRef.current = scanner;
    let mounted = true;
    const qrbox = compact ? { width: 180, height: 120 } : { width: 250, height: 250 };

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox },
        (decodedText) => onScanRef.current(decodedText),
        (error) => onErrorRef.current?.(String(error))
      )
      .then(() => {
        if (!mounted) scanner.stop().catch(() => undefined);
      })
      .catch((error) => {
        if (mounted) onErrorRef.current?.(String(error));
      });

    return () => {
      mounted = false;
      scannerRef.current = null;
      scanner.stop().catch(() => undefined);
    };
  }, [active, compact]);

  const containerClass = compact
    ? "rounded border-0 bg-white p-1 min-h-[140px]"
    : "rounded border bg-white p-2";

  return <div id={scannerId.current} className={containerClass} />;
}

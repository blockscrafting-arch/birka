import { useEffect, useRef } from "react";
import { Html5Qrcode } from "html5-qrcode";

type BarcodeScannerProps = {
  onScan: (text: string) => void;
  onError?: (message: string) => void;
};

export function BarcodeScanner({ onScan, onError }: BarcodeScannerProps) {
  const scannerId = useRef(`scanner-${Math.random().toString(36).slice(2)}`);

  useEffect(() => {
    const scanner = new Html5Qrcode(scannerId.current);
    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => onScan(decodedText),
        (error) => onError?.(String(error))
      )
      .catch((error) => onError?.(String(error)));

    return () => {
      scanner.stop().catch(() => undefined);
      scanner.clear().catch(() => undefined);
    };
  }, [onScan, onError]);

  return <div id={scannerId.current} className="rounded border bg-white p-2" />;
}

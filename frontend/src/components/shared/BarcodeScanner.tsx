import { useEffect, useRef } from "react";
import { Html5Qrcode } from "html5-qrcode";

type BarcodeScannerProps = {
  onScan: (text: string) => void;
  onError?: (message: string) => void;
};

export function BarcodeScanner({ onScan, onError }: BarcodeScannerProps) {
  const scannerId = useRef(`scanner-${Math.random().toString(36).slice(2)}`);
  const onScanRef = useRef(onScan);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onScanRef.current = onScan;
    onErrorRef.current = onError;
  });

  useEffect(() => {
    const scanner = new Html5Qrcode(scannerId.current);
    let mounted = true;

    scanner
      .start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
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
      scanner.stop().catch(() => undefined);
    };
  }, []);

  return <div id={scannerId.current} className="rounded border bg-white p-2" />;
}

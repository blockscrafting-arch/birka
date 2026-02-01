import { useEffect } from "react";

type ToastProps = {
  message: string;
  variant?: "success" | "error";
  onClose: () => void;
  durationMs?: number;
};

export function Toast({ message, variant = "success", onClose, durationMs = 2500 }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onClose, durationMs);
    return () => clearTimeout(timer);
  }, [durationMs, onClose]);

  const variantClass =
    variant === "success"
      ? "border-emerald-400/40 bg-white text-emerald-700 shadow-soft"
      : "border-rose-400/40 bg-white text-rose-700 shadow-soft";

  return (
    <div className={`fixed top-4 left-1/2 z-50 -translate-x-1/2 rounded-xl border px-4 py-2 text-sm ${variantClass}`}>
      {message}
    </div>
  );
}

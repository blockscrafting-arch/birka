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
      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
      : "border-rose-400/30 bg-rose-400/10 text-rose-200";

  return (
    <div className={`fixed top-4 left-1/2 z-50 -translate-x-1/2 rounded-xl border px-4 py-2 text-sm ${variantClass}`}>
      {message}
    </div>
  );
}

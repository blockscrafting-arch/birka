import { useEffect, useState } from "react";

/**
 * Показывает баннер, когда нет соединения с интернетом.
 */
export function OfflineBanner() {
  const [online, setOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true
  );

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onOnline = () => setOnline(true);
    const onOffline = () => setOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  if (online) return null;

  return (
    <div
      className="bg-amber-500 px-4 py-2 text-center text-sm font-medium text-white"
      role="alert"
    >
      Нет соединения с интернетом. Проверьте сеть и обновите страницу.
    </div>
  );
}

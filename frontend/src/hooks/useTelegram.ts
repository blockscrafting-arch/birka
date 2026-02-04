import { useEffect, useState } from "react";

type TelegramWebApp = {
  initData: string;
  initDataUnsafe: {
    user?: { id?: number; username?: string };
  };
  ready: () => void;
  openLink?: (url: string) => void;
  showAlert?: (message: string) => void;
  hapticFeedback?: {
    impactOccurred: (style: string) => void;
  };
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export function useTelegram() {
  const [webApp, setWebApp] = useState<TelegramWebApp | null>(null);

  useEffect(() => {
    const app = window.Telegram?.WebApp ?? null;
    if (app) {
      app.ready();
    }
    setWebApp(app);
  }, []);

  return { webApp };
}

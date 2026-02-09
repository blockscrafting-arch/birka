import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { useTelegram } from "./hooks/useTelegram";
import { apiClient } from "./services/api";
import { Header } from "./components/layout/Header";
import { Page } from "./components/layout/Page";
import { TabBar } from "./components/layout/TabBar";
import { Loader } from "./components/ui/Loader";
import { CompanyPage } from "./pages/client/CompanyPage";
import { OrdersPage } from "./pages/client/OrdersPage";
import { ProductsPage } from "./pages/client/ProductsPage";
import { OrderDetail } from "./pages/client/OrderDetail";
import { AiChatPage } from "./pages/client/AiChatPage";
import { FBOPage } from "./pages/warehouse/FBOPage";
import { PrintPage } from "./pages/warehouse/PrintPage";
import { ReceivingPage } from "./pages/warehouse/ReceivingPage";
import { PackingPage } from "./pages/warehouse/PackingPage";
import { ScannerPage } from "./pages/warehouse/ScannerPage";

export default function App() {
  const { webApp } = useTelegram();
  const [ready, setReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const runAuth = () => {
    setAuthError(null);
    const initData = webApp?.initData;
    if (!initData) {
      setReady(true);
      return;
    }
    setReady(false);
    apiClient
      .api<{ session_token: string }>("/auth/telegram", {
        method: "POST",
        body: JSON.stringify({ init_data: initData }),
      })
      .then((data) => {
        if (data.session_token) {
          localStorage.setItem("birka_session_token", data.session_token);
        }
      })
      .catch((err) => {
        console.error("auth/telegram failed", err);
        setAuthError("Не удалось войти. Проверьте подключение или попробуйте позже.");
      })
      .finally(() => setReady(true));
  };

  useEffect(() => {
    runAuth();
  }, [webApp]);

  if (!ready) {
    return (
      <div className="min-h-screen bg-slate-950 p-4">
        <Loader text="Подключение к Telegram..." />
      </div>
    );
  }

  if (authError) {
    return (
      <div className="min-h-screen bg-slate-950 p-4 flex flex-col items-center justify-center gap-4">
        <p className="text-slate-200 text-center">{authError}</p>
        <button
          type="button"
          onClick={() => runAuth()}
          className="px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-500"
        >
          Повторить
        </button>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Page>
        <Header
          title="Бирка — Mini App"
          subtitle={`Telegram ID: ${webApp?.initDataUnsafe?.user?.id ?? "—"}`}
        />
        <TabBar />
        <Routes>
          <Route path="/" element={<Navigate to="/client/company" replace />} />
          <Route path="/client/company" element={<CompanyPage />} />
          <Route path="/client/products" element={<ProductsPage />} />
          <Route path="/client/orders" element={<OrdersPage />} />
          <Route path="/client/orders/:orderId" element={<OrderDetail />} />
          <Route path="/client/ai" element={<AiChatPage />} />
          <Route path="/warehouse/fbo" element={<FBOPage />} />
          <Route path="/warehouse/print" element={<PrintPage />} />
          <Route path="/warehouse/receiving" element={<ReceivingPage />} />
          <Route path="/warehouse/packing" element={<PackingPage />} />
          <Route path="/warehouse/scanner" element={<ScannerPage />} />
        </Routes>
      </Page>
    </BrowserRouter>
  );
}

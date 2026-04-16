import { lazy, Suspense, useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ErrorBoundary } from "./components/ui/ErrorBoundary";

import { useTelegram } from "./hooks/useTelegram";
import { queryClient } from "./queryClient";
import { apiClient } from "./services/api";
import { Header } from "./components/layout/Header";
import { Page } from "./components/layout/Page";
import { TabBar } from "./components/layout/TabBar";
import { OfflineBanner } from "./components/ui/OfflineBanner";
import { Loader } from "./components/ui/Loader";
import { UploadManager } from "./components/shared/UploadManager";
import { UserProvider, useUser } from "./contexts/UserContext";
const CompanyPage = lazy(() => import("./pages/client/CompanyPage").then((m) => ({ default: m.CompanyPage })));
const OrdersPage = lazy(() => import("./pages/client/OrdersPage").then((m) => ({ default: m.OrdersPage })));
const ProductsPage = lazy(() => import("./pages/client/ProductsPage").then((m) => ({ default: m.ProductsPage })));
const OrderDetail = lazy(() => import("./pages/client/OrderDetail").then((m) => ({ default: m.OrderDetail })));
const AIPage = lazy(() => import("./pages/client/AIPage").then((m) => ({ default: m.AIPage })));
const PricingPage = lazy(() => import("./pages/client/PricingPage").then((m) => ({ default: m.PricingPage })));
const ShippingPage = lazy(() => import("./pages/client/ShippingPage").then((m) => ({ default: m.ShippingPage })));
const AdminPage = lazy(() => import("./pages/admin/AdminPage").then((m) => ({ default: m.AdminPage })));
const AdminOrdersPage = lazy(() => import("./pages/admin/AdminOrdersPage").then((m) => ({ default: m.AdminOrdersPage })));
const UsersPage = lazy(() => import("./pages/admin/UsersPage").then((m) => ({ default: m.UsersPage })));
const DestinationsPage = lazy(() => import("./pages/admin/DestinationsPage").then((m) => ({ default: m.DestinationsPage })));
const ContractTemplatesPage = lazy(() => import("./pages/admin/ContractTemplatesPage").then((m) => ({ default: m.ContractTemplatesPage })));
const DocumentsPage = lazy(() => import("./pages/admin/DocumentsPage").then((m) => ({ default: m.DocumentsPage })));
const ServicesPage = lazy(() => import("./pages/admin/ServicesPage").then((m) => ({ default: m.ServicesPage })));
const AISettingsPage = lazy(() => import("./pages/admin/AISettingsPage").then((m) => ({ default: m.AISettingsPage })));
const PrintPage = lazy(() => import("./pages/warehouse/PrintPage").then((m) => ({ default: m.PrintPage })));
const ReceivingPage = lazy(() => import("./pages/warehouse/ReceivingPage").then((m) => ({ default: m.ReceivingPage })));
const PackingPage = lazy(() => import("./pages/warehouse/PackingPage").then((m) => ({ default: m.PackingPage })));
const ScannerPage = lazy(() => import("./pages/warehouse/ScannerPage").then((m) => ({ default: m.ScannerPage })));
const ReadyPage = lazy(() => import("./pages/warehouse/ReadyPage").then((m) => ({ default: m.ReadyPage })));
const WarehouseShippingPage = lazy(() => import("./pages/warehouse/ShippingPage").then((m) => ({ default: m.ShippingPage })));

function AppRoutes() {
  const { user, isLoading } = useUser();
  const canWarehouse = user?.role === "warehouse" || user?.role === "admin";
  const canAdmin = user?.role === "admin";

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 p-4">
        <Loader text="Загрузка профиля..." />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-4">
        <p className="text-center text-slate-600">
          Не удалось загрузить профиль. Откройте приложение через Telegram.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="rounded-xl bg-blue-600 px-4 py-2 text-sm text-white"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/client/company" replace />} />
      <Route path="/client/company" element={<CompanyPage />} />
      <Route path="/client/products" element={<ProductsPage />} />
      <Route path="/client/orders" element={<OrdersPage />} />
      <Route path="/client/orders/:orderId" element={<OrderDetail />} />
      <Route path="/client/ai" element={<AIPage />} />
      <Route path="/client/pricing" element={<PricingPage />} />
      <Route path="/client/shipping" element={<ShippingPage />} />
      <Route
        path="/warehouse/print"
        element={canWarehouse ? <PrintPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/warehouse/receiving"
        element={canWarehouse ? <ReceivingPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/warehouse/packing"
        element={canWarehouse ? <PackingPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/warehouse/scanner"
        element={canWarehouse ? <ScannerPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/warehouse/ready"
        element={canWarehouse ? <ReadyPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/warehouse/shipping"
        element={canWarehouse ? <WarehouseShippingPage /> : <Navigate to="/client/company" replace />}
      />
      <Route path="/admin" element={canAdmin ? <AdminPage /> : <Navigate to="/client/company" replace />} />
      <Route
        path="/admin/orders"
        element={canAdmin ? <AdminOrdersPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/admin/users"
        element={canAdmin ? <UsersPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/admin/destinations"
        element={canAdmin ? <DestinationsPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/admin/templates"
        element={canAdmin ? <ContractTemplatesPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/admin/services"
        element={canAdmin ? <ServicesPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/admin/documents"
        element={canAdmin ? <DocumentsPage /> : <Navigate to="/client/company" replace />}
      />
      <Route
        path="/admin/ai-settings"
        element={canAdmin ? <AISettingsPage /> : <Navigate to="/client/company" replace />}
      />
    </Routes>
  );
}

function AppLayout() {
  const location = useLocation();
  const isAI = location.pathname === "/client/ai";

  return (
    <Page noPadding={isAI}>
      <div className={isAI ? "shrink-0 px-4 pt-4" : "shrink-0"}>
        <Header title="Бирка — фулфилмент" />
        <TabBar />
      </div>
      <main
        className={
          isAI
            ? "flex min-h-0 flex-1 flex-col overflow-hidden"
            : "flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden pb-20"
        }
      >
        <div className={`min-w-0 flex-col relative ${isAI ? "flex min-h-0 flex-1 flex-col" : ""}`}>
          <Suspense fallback={<Loader text="Загрузка..." />}>
            <AppRoutes />
          </Suspense>
        </div>
      </main>
    </Page>
  );
}

export default function App() {
  const { webApp } = useTelegram();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const initData = webApp?.initData;
    if (!initData) {
      setReady(true);
      return;
    }
    apiClient
      .api<{ session_token: string }>("/auth/telegram", {
        method: "POST",
        body: JSON.stringify({ init_data: initData }),
      })
      .then((data) => {
        if (data.session_token) {
          localStorage.setItem("birka_session_token", data.session_token);
          queryClient.invalidateQueries({ queryKey: ["current-user"] });
        }
      })
      .finally(() => setReady(true));
  }, [webApp]);

  useEffect(() => {
    if (ready) document.getElementById("splash")?.remove();
  }, [ready]);

  if (!ready) {
    return (
      <div className="min-h-screen bg-slate-50 p-4">
        <Loader text="Подключение к Telegram..." />
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <UserProvider>
          <OfflineBanner />
          <UploadManager />
          <AppLayout />
        </UserProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

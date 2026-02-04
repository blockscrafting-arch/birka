import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { useTelegram } from "./hooks/useTelegram";
import { apiClient } from "./services/api";
import { Header } from "./components/layout/Header";
import { Page } from "./components/layout/Page";
import { TabBar } from "./components/layout/TabBar";
import { Loader } from "./components/ui/Loader";
import { UserProvider, useUser } from "./contexts/UserContext";
import { CompanyPage } from "./pages/client/CompanyPage";
import { OrdersPage } from "./pages/client/OrdersPage";
import { ProductsPage } from "./pages/client/ProductsPage";
import { OrderDetail } from "./pages/client/OrderDetail";
import { AIPage } from "./pages/client/AIPage";
import { PricingPage } from "./pages/client/PricingPage";
import { ShippingPage } from "./pages/client/ShippingPage";
import { AdminPage } from "./pages/admin/AdminPage";
import { UsersPage } from "./pages/admin/UsersPage";
import { DestinationsPage } from "./pages/admin/DestinationsPage";
import { ContractTemplatesPage } from "./pages/admin/ContractTemplatesPage";
import { DocumentsPage } from "./pages/admin/DocumentsPage";
import { ServicesPage } from "./pages/admin/ServicesPage";
import { PrintPage } from "./pages/warehouse/PrintPage";
import { ReceivingPage } from "./pages/warehouse/ReceivingPage";
import { PackingPage } from "./pages/warehouse/PackingPage";
import { ScannerPage } from "./pages/warehouse/ScannerPage";
import { ShippingPage as WarehouseShippingPage } from "./pages/warehouse/ShippingPage";

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
        path="/warehouse/shipping"
        element={canWarehouse ? <WarehouseShippingPage /> : <Navigate to="/client/company" replace />}
      />
      <Route path="/admin" element={canAdmin ? <AdminPage /> : <Navigate to="/client/company" replace />} />
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
    </Routes>
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
    <BrowserRouter>
      <UserProvider>
        <Page>
          <Header title="Бирка — фулфилмент" />
          <TabBar />
          <AppRoutes />
        </Page>
      </UserProvider>
    </BrowserRouter>
  );
}

import { NavLink, useLocation } from "react-router-dom";

import { useUser } from "../../contexts/UserContext";

const primaryTabs = [
  { to: "/client/company", label: "Клиент" },
  { to: "/warehouse/receiving", label: "Склад" },
  { to: "/admin/users", label: "Админка" },
];

const clientTabs = [
  { to: "/client/company", label: "Компании" },
  { to: "/client/products", label: "Товары" },
  { to: "/client/orders", label: "Заявки" },
  { to: "/client/shipping", label: "Отгрузка" },
  { to: "/client/ai", label: "AI-помощник" },
];

const warehouseTabs = [
  { to: "/warehouse/receiving", label: "Приёмка" },
  { to: "/warehouse/packing", label: "Упаковка" },
  { to: "/warehouse/shipping", label: "Отгрузка" },
  { to: "/warehouse/print", label: "Печать" },
  { to: "/warehouse/scanner", label: "Сканер" },
];

const adminTabs = [
  { to: "/admin/users", label: "Пользователи" },
  { to: "/admin/destinations", label: "Адреса" },
  { to: "/admin/templates", label: "Шаблоны" },
];

export function TabBar() {
  const location = useLocation();
  const { user } = useUser();
  const canWarehouse = user?.role === "warehouse" || user?.role === "admin";
  const canAdmin = user?.role === "admin";
  const isAdmin = location.pathname.startsWith("/admin");
  const isWarehouse = location.pathname.startsWith("/warehouse");
  const tabs = isAdmin ? adminTabs : isWarehouse ? warehouseTabs : clientTabs;
  const visiblePrimaryTabs = primaryTabs.filter((tab) => {
    if (tab.to.startsWith("/warehouse")) {
      return canWarehouse;
    }
    if (tab.to.startsWith("/admin")) {
      return canAdmin;
    }
    return true;
  });

  return (
    <div className="mb-6 space-y-3">
      <div className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-soft">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              `rounded-xl px-3 py-2 text-xs font-semibold transition ${
                isActive ? "bg-birka-500 text-white shadow-soft" : "text-slate-600 hover:bg-slate-100"
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-lg items-center justify-around p-2">
          {visiblePrimaryTabs.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                `rounded-xl px-4 py-2 text-sm font-semibold transition ${
                  isActive ? "bg-birka-500 text-white shadow-soft" : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}

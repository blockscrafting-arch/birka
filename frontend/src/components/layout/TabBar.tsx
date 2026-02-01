import { NavLink, useLocation } from "react-router-dom";

const primaryTabs = [
  { to: "/client/company", label: "Клиент" },
  { to: "/warehouse/receiving", label: "Склад" },
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

export function TabBar() {
  const location = useLocation();
  const isWarehouse = location.pathname.startsWith("/warehouse");
  const tabs = isWarehouse ? warehouseTabs : clientTabs;

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
          {primaryTabs.map((tab) => (
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

import { NavLink } from "react-router-dom";

const tabs = [
  { to: "/client/company", label: "Клиент" },
  { to: "/warehouse/receiving", label: "Склад" },
];

export function TabBar() {
  return (
    <nav className="mb-6 flex gap-2">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          className={({ isActive }) =>
            `rounded px-3 py-2 text-sm ${
              isActive ? "bg-slate-900 text-white" : "bg-white border"
            }`
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}

import { StatusBadge } from "../ui/StatusBadge";

type OrderCardProps = {
  title: string;
  status: "На приемке" | "Принято" | "Упаковка" | "Готово к отгрузке" | "Завершено";
  onClick?: () => void;
};

export function OrderCard({ title, status, onClick }: OrderCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-left shadow-sm transition hover:border-slate-700 hover:bg-slate-900"
    >
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-100">{title}</div>
        <StatusBadge status={status} />
      </div>
    </button>
  );
}

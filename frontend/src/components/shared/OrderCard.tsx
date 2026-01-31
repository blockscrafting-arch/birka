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
      className="w-full rounded bg-white p-4 text-left shadow-sm hover:bg-slate-50"
    >
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold">{title}</div>
        <StatusBadge status={status} />
      </div>
    </button>
  );
}

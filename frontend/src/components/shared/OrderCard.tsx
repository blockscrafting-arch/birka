import { OrderStatus } from "../../types";
import { StatusBadge } from "../ui/StatusBadge";

type OrderCardProps = {
  title: string;
  status: OrderStatus;
  onClick?: () => void;
  onExport?: () => void;
  photoCount?: number;
};

export function OrderCard({ title, status, onClick, onExport, photoCount }: OrderCardProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
      <button
        type="button"
        onClick={onClick}
        className="w-full text-left transition hover:border-slate-700 hover:bg-slate-900"
      >
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-slate-100">{title}</div>
          <StatusBadge status={status} />
        </div>
        {photoCount ? <div className="mt-1 text-xs text-slate-400">Фото: {photoCount}</div> : null}
      </button>
      {onExport ? (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onExport();
          }}
          className="mt-2 text-xs text-slate-400 underline hover:text-slate-300"
        >
          Экспорт Excel в Telegram
        </button>
      ) : null}
    </div>
  );
}

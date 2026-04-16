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
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
      <button
        type="button"
        onClick={onClick}
        className="w-full text-left transition hover:border-birka-200"
      >
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-slate-900">{title}</div>
          <StatusBadge status={status} />
        </div>
        {photoCount ? <div className="mt-1 text-xs text-slate-500">Фото: {photoCount}</div> : null}
      </button>
      {onExport ? (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onExport();
          }}
          className="mt-2 text-xs text-birka-600 underline hover:text-birka-700"
        >
          Экспорт Excel в Telegram
        </button>
      ) : null}
    </div>
  );
}

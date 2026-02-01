type Status = "На приемке" | "Принято" | "Упаковка" | "Готово к отгрузке" | "Завершено";

const statusClasses: Record<Status, string> = {
  "На приемке": "bg-amber-50 text-amber-700 border border-amber-200",
  "Принято": "bg-birka-50 text-birka-700 border border-birka-200",
  "Упаковка": "bg-purple-50 text-purple-700 border border-purple-200",
  "Готово к отгрузке": "bg-emerald-50 text-emerald-700 border border-emerald-200",
  "Завершено": "bg-slate-100 text-slate-600 border border-slate-200",
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`rounded-full px-2 py-1 text-xs font-medium ${statusClasses[status]}`}>
      {status}
    </span>
  );
}

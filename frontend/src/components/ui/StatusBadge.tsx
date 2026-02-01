type Status = "На приемке" | "Принято" | "Упаковка" | "Готово к отгрузке" | "Завершено";

const statusClasses: Record<Status, string> = {
  "На приемке": "bg-amber-400/20 text-amber-300 border border-amber-400/30",
  "Принято": "bg-sky-400/20 text-sky-300 border border-sky-400/30",
  "Упаковка": "bg-purple-400/20 text-purple-300 border border-purple-400/30",
  "Готово к отгрузке": "bg-emerald-400/20 text-emerald-300 border border-emerald-400/30",
  "Завершено": "bg-slate-400/20 text-slate-200 border border-slate-400/30",
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`rounded-full px-2 py-1 text-xs font-medium ${statusClasses[status]}`}>
      {status}
    </span>
  );
}

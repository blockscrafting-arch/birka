type Status = "На приемке" | "Принято" | "Упаковка" | "Готово к отгрузке" | "Завершено";

const statusClasses: Record<Status, string> = {
  "На приемке": "bg-yellow-100 text-yellow-800",
  "Принято": "bg-blue-100 text-blue-800",
  "Упаковка": "bg-purple-100 text-purple-800",
  "Готово к отгрузке": "bg-green-100 text-green-800",
  "Завершено": "bg-slate-100 text-slate-700",
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`rounded-full px-2 py-1 text-xs font-medium ${statusClasses[status]}`}>
      {status}
    </span>
  );
}

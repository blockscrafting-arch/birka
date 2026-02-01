import { Button } from "./Button";

type PaginationProps = {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
};

export function Pagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className="flex items-center justify-between gap-2 rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
      <Button
        type="button"
        variant="ghost"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Назад
      </Button>
      <span className="text-xs text-slate-300">
        Страница {page} из {totalPages}
      </span>
      <Button
        type="button"
        variant="ghost"
        disabled={page >= totalPages}
        onClick={() => onPageChange(page + 1)}
      >
        Вперёд
      </Button>
    </div>
  );
}

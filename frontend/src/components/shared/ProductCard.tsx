type ProductCardProps = {
  name: string;
  barcode?: string;
  stock?: number;
  defect?: number;
  onClick?: () => void;
  onShowDefects?: () => void;
};

export function ProductCard({ name, barcode, stock, defect, onClick, onShowDefects }: ProductCardProps) {
  return (
    <div className="w-full rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-left shadow-sm">
      <button
        type="button"
        onClick={onClick}
        className="w-full text-left transition hover:text-slate-100"
      >
        <div className="text-sm font-semibold text-slate-100">{name}</div>
        <div className="mt-1 text-xs text-slate-400">ШК: {barcode ?? "—"}</div>
        <div className="mt-2 flex gap-4 text-xs text-slate-400">
          <span>Остаток: {stock ?? 0}</span>
          <span>Брак: {defect ?? 0}</span>
        </div>
      </button>
      {defect && defect > 0 && onShowDefects ? (
        <button
          type="button"
          className="mt-2 text-xs text-slate-300 underline decoration-dashed underline-offset-4"
          onClick={onShowDefects}
        >
          Фото брака
        </button>
      ) : null}
    </div>
  );
}

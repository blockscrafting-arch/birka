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
    <div className="w-full rounded-xl border border-slate-200 bg-white p-4 text-left shadow-soft">
      <button
        type="button"
        onClick={onClick}
        className="w-full text-left transition hover:border-birka-200"
      >
        <div className="text-sm font-semibold text-slate-900">{name}</div>
        <div className="mt-1 text-xs text-slate-500">ШК: {barcode ?? "—"}</div>
        <div className="mt-2 flex gap-4 text-xs font-semibold text-slate-700">
          <span>Остаток: {stock ?? 0}</span>
          <span>Брак: {defect ?? 0}</span>
        </div>
      </button>
      {defect && defect > 0 && onShowDefects ? (
        <button
          type="button"
          className="mt-2 text-xs text-birka-600 underline decoration-dashed underline-offset-4 hover:text-birka-700"
          onClick={onShowDefects}
        >
          Фото брака
        </button>
      ) : null}
    </div>
  );
}

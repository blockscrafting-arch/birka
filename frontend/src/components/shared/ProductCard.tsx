type ProductCardProps = {
  name: string;
  barcode?: string;
  stock?: number;
  defect?: number;
  onClick?: () => void;
};

export function ProductCard({ name, barcode, stock, defect, onClick }: ProductCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-xl border border-slate-800 bg-slate-900/60 p-4 text-left shadow-sm transition hover:border-slate-700 hover:bg-slate-900"
    >
      <div className="text-sm font-semibold text-slate-100">{name}</div>
      <div className="mt-1 text-xs text-slate-400">ШК: {barcode ?? "—"}</div>
      <div className="mt-2 flex gap-4 text-xs text-slate-400">
        <span>Остаток: {stock ?? 0}</span>
        <span>Брак: {defect ?? 0}</span>
      </div>
    </button>
  );
}

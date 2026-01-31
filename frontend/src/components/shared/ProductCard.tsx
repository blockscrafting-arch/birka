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
      className="w-full rounded bg-white p-4 text-left shadow-sm hover:bg-slate-50"
    >
      <div className="text-sm font-semibold">{name}</div>
      <div className="mt-1 text-xs text-slate-600">ШК: {barcode ?? "—"}</div>
      <div className="mt-2 flex gap-4 text-xs text-slate-600">
        <span>Остаток: {stock ?? 0}</span>
        <span>Брак: {defect ?? 0}</span>
      </div>
    </button>
  );
}

/** Прогресс-бар для загрузки и длительных операций. */
type ProgressBarProps = {
  value: number;
  max?: number;
  label?: string;
  className?: string;
};

export function ProgressBar({ value, max = 100, label, className = "" }: ProgressBarProps) {
  const percent = Math.min(100, Math.max(0, max > 0 ? (value / max) * 100 : 0));
  const valueClamped = Math.max(0, Math.min(max, value));
  return (
    <div className={className}>
      {(label !== undefined || percent < 100) && (
        <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
          {label ? <span>{label}</span> : <span />}
          <span>{Math.round(percent)}%</span>
        </div>
      )}
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-birka-500 transition-[width] duration-200"
          style={{ width: `${percent}%` }}
          role="progressbar"
          aria-valuenow={valueClamped}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-label={label ?? "Прогресс"}
        />
      </div>
    </div>
  );
}

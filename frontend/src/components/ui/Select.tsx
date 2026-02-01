import { SelectHTMLAttributes } from "react";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label?: string;
  error?: string;
};

export function Select({ label, error, className = "", children, ...props }: SelectProps) {
  return (
    <label className="block text-sm">
      {label ? <span className="mb-1 block text-slate-700">{label}</span> : null}
      <select
        className={`w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-soft focus:border-birka-500 focus:outline-none focus:ring-2 focus:ring-birka-100 ${className}`}
        {...props}
      >
        {children}
      </select>
      {error ? <span className="mt-1 block text-xs text-rose-500">{error}</span> : null}
    </label>
  );
}

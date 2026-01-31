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
        className={`w-full rounded border px-3 py-2 text-sm focus:border-slate-400 focus:outline-none ${className}`}
        {...props}
      >
        {children}
      </select>
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
    </label>
  );
}

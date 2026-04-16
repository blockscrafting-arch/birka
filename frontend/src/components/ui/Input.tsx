import { InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label?: string;
  error?: string;
};

export function Input({ label, error, className = "", ...props }: InputProps) {
  return (
    <label className="block text-sm">
      {label ? <span className="mb-1 block text-slate-700">{label}</span> : null}
      <input
        className={`w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-500 shadow-soft focus:border-birka-500 focus:outline-none focus:ring-2 focus:ring-birka-100 ${className}`}
        {...props}
      />
      {error ? <span className="mt-1 block text-xs text-rose-500">{error}</span> : null}
    </label>
  );
}

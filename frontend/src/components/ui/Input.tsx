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
        className={`w-full rounded border px-3 py-2 text-sm focus:border-slate-400 focus:outline-none ${className}`}
        {...props}
      />
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
    </label>
  );
}

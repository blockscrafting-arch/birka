import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-gradient-to-r from-indigo-500 to-sky-500 text-white hover:from-indigo-400 hover:to-sky-400 shadow-lg shadow-indigo-500/20",
  secondary: "border border-slate-700 bg-slate-900/60 text-slate-100 hover:bg-slate-800",
  danger: "bg-rose-600 text-white hover:bg-rose-500",
  ghost: "text-slate-300 hover:bg-slate-800/80",
};

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return (
    <button
      className={`rounded-lg px-4 py-2 text-sm font-medium transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 ${variantClasses[variant]} ${className}`}
      {...props}
    />
  );
}

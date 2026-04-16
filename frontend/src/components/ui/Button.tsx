import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-birka-500 text-white shadow-soft hover:bg-birka-600 active:bg-birka-700 focus-visible:ring-2 focus-visible:ring-birka-500 focus-visible:ring-offset-2",
  secondary:
    "border border-slate-200 bg-white text-slate-700 shadow-soft hover:border-birka-200 hover:text-slate-900 focus-visible:ring-2 focus-visible:ring-birka-500 focus-visible:ring-offset-2",
  danger:
    "bg-rose-500 text-white shadow-soft hover:bg-rose-600 focus-visible:ring-2 focus-visible:ring-rose-500 focus-visible:ring-offset-2",
  ghost:
    "text-slate-600 hover:bg-slate-100 focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2",
};

export function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return (
    <button
      className={`min-h-[44px] rounded-lg px-4 py-2 text-sm font-medium transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 outline-none focus:outline-none ${variantClasses[variant]} ${className}`}
      {...props}
    />
  );
}

import { ReactNode } from "react";

type HeaderProps = {
  title: string;
  subtitle?: string;
  right?: ReactNode;
};

export function Header({ title, subtitle, right }: HeaderProps) {
  return (
    <header className="mb-4 flex items-center justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">{title}</h1>
        {subtitle ? <p className="text-sm text-slate-400">{subtitle}</p> : null}
      </div>
      {right}
    </header>
  );
}

import { ReactNode } from "react";

import { LOGO_URL } from "../../services/api";

type HeaderProps = {
  title: string;
  subtitle?: string;
  right?: ReactNode;
};

export function Header({ title, subtitle, right }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 mb-4 border-b border-slate-200 bg-white/95 shadow-soft backdrop-blur">
      <div className="flex items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-3">
          <img src={LOGO_URL} alt="Бирка" className="h-9 w-9 rounded-lg object-cover" />
          <div>
            <h1 className="text-lg font-semibold text-slate-800">{title}</h1>
            {subtitle ? <p className="text-xs text-slate-600">{subtitle}</p> : null}
            <p className="text-[11px] text-slate-500">Build: {__BUILD_ID__}</p>
          </div>
        </div>
        {right}
      </div>
    </header>
  );
}

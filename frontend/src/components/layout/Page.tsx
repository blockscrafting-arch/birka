import { ReactNode } from "react";

type PageProps = {
  children: ReactNode;
};

export function Page({ children }: PageProps) {
  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-slate-50 via-white to-slate-50 p-4 pb-24">
      {children}
    </div>
  );
}

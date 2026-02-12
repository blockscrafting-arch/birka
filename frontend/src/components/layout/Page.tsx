import { ReactNode, useEffect } from "react";

type PageProps = {
  children: ReactNode;
  /** Заголовок страницы (устанавливает document.title для вкладки браузера). */
  title?: string;
};

export function Page({ children, title }: PageProps) {
  useEffect(() => {
    if (!title) return;
    const prev = document.title;
    document.title = title;
    return () => {
      document.title = prev;
    };
  }, [title]);

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-slate-50 via-white to-slate-50 p-4 pb-24">
      {children}
    </div>
  );
}

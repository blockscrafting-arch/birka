import { ReactNode, useEffect } from "react";

type PageProps = {
  children: ReactNode;
  /** Заголовок страницы (устанавливает document.title для вкладки браузера). */
  title?: string;
  /** Убрать паддинги (для полноэкранных интерфейсов, например чат AI). */
  noPadding?: boolean;
};

export function Page({ children, title, noPadding }: PageProps) {
  useEffect(() => {
    if (!title) return;
    const prev = document.title;
    document.title = title;
    return () => {
      document.title = prev;
    };
  }, [title]);

  return (
    <div
      className={`flex h-screen max-h-screen min-h-0 flex-col overflow-hidden bg-gradient-to-b from-slate-50 via-white to-slate-50 ${noPadding ? "" : "p-4 pb-24"}`}
    >
      {children}
    </div>
  );
}

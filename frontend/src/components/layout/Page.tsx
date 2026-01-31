import { ReactNode } from "react";

type PageProps = {
  children: ReactNode;
};

export function Page({ children }: PageProps) {
  return <div className="min-h-screen p-4">{children}</div>;
}

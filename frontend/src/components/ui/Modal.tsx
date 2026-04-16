import { ReactNode } from "react";

type ModalProps = {
  title?: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
};

export function Modal({ title, open, onClose, children }: ModalProps) {
  if (!open) {
    return null;
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur">
      <div className="mx-4 w-full max-h-[85vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-card sm:mx-auto sm:max-w-md">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800">{title ?? "Окно"}</h2>
          <button
            type="button"
            className="rounded text-sm text-slate-600 hover:text-slate-800 focus-visible:ring-2 focus-visible:ring-birka-500 focus-visible:ring-offset-2 outline-none"
            onClick={onClose}
          >
            Закрыть
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

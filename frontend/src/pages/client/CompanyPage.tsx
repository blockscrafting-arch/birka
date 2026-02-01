import { useState } from "react";

import { useCompanies } from "../../hooks/useCompanies";
import { apiClient } from "../../services/api";
import { Company } from "../../types";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { CompanyForm } from "./CompanyForm";

export function CompanyPage() {
  const [page, setPage] = useState(1);
  const limit = 20;
  const { items, total, isLoading, error, create, update } = useCompanies(page, limit);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Company | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  const companies = items;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  const handleCreate = async (payload: { inn: string; name?: string; bank_bik?: string; bank_account?: string }) => {
    setPageError(null);
    try {
      await create.mutateAsync(payload);
      setOpen(false);
      setPage(1);
      setToast({ message: "Компания создана" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось создать компанию");
    }
  };

  const handleUpdate = async (payload: { inn: string; name?: string; bank_bik?: string; bank_account?: string }) => {
    if (!editing) return;
    setPageError(null);
    try {
      await update.mutateAsync({ id: editing.id, ...payload });
      setEditing(null);
      setToast({ message: "Изменения сохранены" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось обновить компанию");
    }
  };

  const handleContract = async (companyId: number) => {
    setPageError(null);
    setBusyId(companyId);
    try {
      const { blob, filename } = await apiClient.apiFile(`/companies/${companyId}/contract`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename ?? `contract_${companyId}.pdf`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось скачать договор");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button variant="primary" onClick={() => setOpen(true)}>
          Добавить компанию
        </Button>
        {pageError ? <div className="text-sm text-rose-300">{pageError}</div> : null}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-rose-300">Не удалось загрузить компании</div> : null}
      {!isLoading && companies.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
          Пока нет компаний. Добавьте первую, чтобы начать работу.
        </div>
      ) : null}

      <div className="space-y-3">
        {companies.map((company) => (
          <div key={company.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
            <div className="text-base font-semibold text-slate-100">{company.name}</div>
            <div className="mt-1 text-xs text-slate-400">ИНН: {company.inn}</div>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => setEditing(company)}>
                Редактировать
              </Button>
              <Button
                variant="ghost"
                disabled={busyId === company.id}
                onClick={() => handleContract(company.id)}
              >
                {busyId === company.id ? "Скачивание..." : "Скачать договор"}
              </Button>
            </div>
          </div>
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />

      <Modal title="Новая компания" open={open} onClose={() => setOpen(false)}>
        <CompanyForm isSubmitting={create.isPending} onSubmit={handleCreate} submitLabel="Создать" />
      </Modal>

      <Modal title="Редактирование компании" open={Boolean(editing)} onClose={() => setEditing(null)}>
        <CompanyForm
          initial={
            editing
              ? {
                  inn: editing.inn,
                  name: editing.name,
                  bank_bik: editing.bank_bik ?? undefined,
                  bank_account: editing.bank_account ?? undefined,
                }
              : undefined
          }
          isSubmitting={update.isPending}
          onSubmit={handleUpdate}
          submitLabel="Сохранить"
        />
      </Modal>
    </div>
  );
}

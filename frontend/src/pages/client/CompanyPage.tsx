import { useState } from "react";

import { useCompanies } from "../../hooks/useCompanies";
import { useCompanyAPIKeys } from "../../hooks/useCompanyAPIKeys";
import { apiClient } from "../../services/api";
import { Company } from "../../types";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
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
  const [apiKeysCompanyId, setApiKeysCompanyId] = useState<number | null>(null);
  const [apiKeysForm, setApiKeysForm] = useState({
    wb_api_key: "",
    ozon_client_id: "",
    ozon_api_key: "",
  });
  const [apiKeysError, setApiKeysError] = useState<string | null>(null);
  const [guideSending, setGuideSending] = useState(false);
  const { data: apiKeysData, isLoading: apiKeysLoading, update: updateApiKeys } = useCompanyAPIKeys(apiKeysCompanyId);

  const companies = items;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  const handleCreate = async (payload: {
    inn: string;
    name?: string;
    bank_bik?: string;
    bank_account?: string;
    bank_name?: string;
    bank_corr_account?: string;
  }) => {
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

  const handleUpdate = async (payload: {
    inn: string;
    name?: string;
    bank_bik?: string;
    bank_account?: string;
    bank_name?: string;
    bank_corr_account?: string;
  }) => {
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

  const handleOpenApiKeys = (companyId: number) => {
    setApiKeysCompanyId(companyId);
    setApiKeysForm({ wb_api_key: "", ozon_client_id: "", ozon_api_key: "" });
  };

  const handleSaveApiKeys = async () => {
    if (apiKeysCompanyId == null) return;
    setPageError(null);
    try {
      const payload: { wb_api_key?: string; ozon_client_id?: string; ozon_api_key?: string } = {};
      if (apiKeysForm.wb_api_key.trim()) payload.wb_api_key = apiKeysForm.wb_api_key.trim();
      if (apiKeysForm.ozon_client_id.trim()) payload.ozon_client_id = apiKeysForm.ozon_client_id.trim();
      if (apiKeysForm.ozon_api_key.trim()) payload.ozon_api_key = apiKeysForm.ozon_api_key.trim();
      await updateApiKeys.mutateAsync(payload);
      setToast({ message: "Ключи сохранены" });
      setApiKeysCompanyId(null);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось сохранить ключи");
      setToast({ message: err instanceof Error ? err.message : "Ошибка", variant: "error" });
    }
  };

  const handleContract = async (companyId: number) => {
    setPageError(null);
    setBusyId(companyId);
    try {
      await apiClient.api(`/companies/${companyId}/contract/send`, { method: "POST" });
      setToast({ message: "Файл отправлен в чат с ботом" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось отправить договор");
      setToast({ message: "Не удалось отправить договор", variant: "error" });
    } finally {
      setBusyId(null);
    }
  };

  const handleSendGuide = async () => {
    setApiKeysError(null);
    setGuideSending(true);
    try {
      await apiClient.api("/companies/api-keys-guide/send", { method: "POST" });
      setToast({ message: "Инструкция отправлена в чат с ботом" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Не удалось отправить инструкцию";
      setApiKeysError(msg);
      setToast({ message: msg, variant: "error" });
    } finally {
      setGuideSending(false);
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button variant="primary" onClick={() => setOpen(true)}>
          Добавить компанию
        </Button>
        {pageError ? <div className="text-sm text-rose-500">{pageError}</div> : null}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-rose-500">Не удалось загрузить компании</div> : null}
      {!isLoading && companies.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
          Пока нет компаний. Добавьте первую, чтобы начать работу.
        </div>
      ) : null}

      <div className="space-y-3">
        {companies.map((company) => (
          <div key={company.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
            <div className="text-base font-semibold text-slate-900">{company.name}</div>
            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-slate-500">
              <span>ИНН: {company.inn}</span>
              {company.kpp && <span>КПП: {company.kpp}</span>}
              {company.ogrn && <span>ОГРН: {company.ogrn}</span>}
            </div>
            {company.legal_address && (
              <div className="mt-1 text-xs text-slate-600">{company.legal_address}</div>
            )}
            {(company.okved || company.okved_name) && (
              <div className="mt-0.5 text-xs text-slate-500">
                ОКВЭД: {[company.okved, company.okved_name].filter(Boolean).join(" — ")}
              </div>
            )}
            {company.bank_name && (
              <div className="mt-0.5 text-xs text-slate-500">Банк: {company.bank_name}</div>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => setEditing(company)}>
                Редактировать
              </Button>
              <Button variant="secondary" onClick={() => handleOpenApiKeys(company.id)}>
                API-ключи (WB / Ozon)
              </Button>
              <Button
                variant="ghost"
                disabled={busyId === company.id}
                onClick={() => handleContract(company.id)}
              >
                {busyId === company.id ? "Отправка..." : "Отправить договор в Telegram"}
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
                  kpp: editing.kpp ?? undefined,
                  ogrn: editing.ogrn ?? undefined,
                  legal_address: editing.legal_address ?? undefined,
                  okved: editing.okved ?? undefined,
                  okved_name: editing.okved_name ?? undefined,
                  bank_name: editing.bank_name ?? undefined,
                  bank_corr_account: editing.bank_corr_account ?? undefined,
                }
              : undefined
          }
          isSubmitting={update.isPending}
          onSubmit={handleUpdate}
          submitLabel="Сохранить"
        />
      </Modal>

      <Modal
        title="API-ключи WB / Ozon"
        open={apiKeysCompanyId != null}
        onClose={() => { setApiKeysCompanyId(null); setApiKeysError(null); }}
      >
        <div className="space-y-3">
          {apiKeysError ? (
            <div className="rounded bg-rose-50 p-2 text-sm text-rose-700">{apiKeysError}</div>
          ) : null}
          {apiKeysLoading ? (
            <div className="text-sm text-slate-500">Загрузка...</div>
          ) : (
            <>
              <Button
                variant="ghost"
                disabled={guideSending}
                onClick={handleSendGuide}
              >
                {guideSending ? "Отправка..." : "Где взять ключи?"}
              </Button>
              <Input
                label="Ключ Wildberries"
                type="password"
                placeholder={apiKeysData?.wb_api_key ?? "Не задан"}
                value={apiKeysForm.wb_api_key}
                onChange={(e) => setApiKeysForm((p) => ({ ...p, wb_api_key: e.target.value }))}
              />
              <Input
                label="Client ID Ozon"
                type="password"
                placeholder={apiKeysData?.ozon_client_id ?? "Не задан"}
                value={apiKeysForm.ozon_client_id}
                onChange={(e) => setApiKeysForm((p) => ({ ...p, ozon_client_id: e.target.value }))}
              />
              <Input
                label="API Key Ozon"
                type="password"
                placeholder={apiKeysData?.ozon_api_key ?? "Не задан"}
                value={apiKeysForm.ozon_api_key}
                onChange={(e) => setApiKeysForm((p) => ({ ...p, ozon_api_key: e.target.value }))}
              />
              <p className="text-xs text-slate-500">
                Оставьте поле пустым, чтобы не менять. Чтобы очистить ключ, отправьте пустое значение и сохраните.
                Ключи хранятся на сервере и используются для отгрузок WB/Ozon.
              </p>
              <Button
                variant="primary"
                disabled={updateApiKeys.isPending}
                onClick={handleSaveApiKeys}
              >
                {updateApiKeys.isPending ? "Сохранение..." : "Сохранить"}
              </Button>
            </>
          )}
        </div>
      </Modal>
    </div>
  );
}

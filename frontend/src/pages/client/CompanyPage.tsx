import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useCompanies } from "../../hooks/useCompanies";
import { useCompanyAPIKeys } from "../../hooks/useCompanyAPIKeys";
import { apiClient } from "../../services/api";
import { Company } from "../../types";
import { CompanyForm } from "./CompanyForm";

function CompanyAPIKeysForm({
  companyId,
  onSuccess,
  onDelete,
  onError,
}: {
  companyId: number;
  onSuccess: () => void;
  onDelete: () => void;
  onError: (message: string) => void;
}) {
  const { data: keysStatus, setKeys, deleteKeys } = useCompanyAPIKeys(companyId);
  const [wbKey, setWbKey] = useState("");
  const [ozonClientId, setOzonClientId] = useState("");
  const [ozonKey, setOzonKey] = useState("");

  const hasAny = keysStatus?.has_wb || keysStatus?.has_ozon_client_id || keysStatus?.has_ozon_api_key;

  const handleSave = async () => {
    onError("");
    const payload: { wb_api_key?: string; ozon_client_id?: string; ozon_api_key?: string } = {};
    if (wbKey.trim()) payload.wb_api_key = wbKey.trim();
    if (ozonClientId.trim()) payload.ozon_client_id = ozonClientId.trim();
    if (ozonKey.trim()) payload.ozon_api_key = ozonKey.trim();
    if (Object.keys(payload).length === 0) {
      onError("Введите хотя бы один ключ для сохранения");
      return;
    }
    try {
      await setKeys.mutateAsync(payload);
      setWbKey("");
      setOzonClientId("");
      setOzonKey("");
      onSuccess();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Не удалось сохранить ключи");
    }
  };

  const handleDelete = async () => {
    onError("");
    try {
      await deleteKeys.mutateAsync();
      setWbKey("");
      setOzonClientId("");
      setOzonKey("");
      onDelete();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Не удалось удалить ключи");
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-400">
        WB: {keysStatus?.has_wb ? "ключ установлен" : "не задан"} · Ozon:{" "}
        {keysStatus?.has_ozon_client_id && keysStatus?.has_ozon_api_key ? "ключи установлены" : "не заданы"}
      </p>
      <Input
        type="password"
        label="WB API-ключ"
        placeholder={keysStatus?.has_wb ? "Оставьте пустым, чтобы не менять" : "Введите ключ"}
        value={wbKey}
        onChange={(e) => setWbKey(e.target.value)}
      />
      <Input
        label="Ozon Client-ID"
        placeholder={keysStatus?.has_ozon_client_id ? "Оставьте пустым, чтобы не менять" : "Введите Client-ID"}
        value={ozonClientId}
        onChange={(e) => setOzonClientId(e.target.value)}
      />
      <Input
        type="password"
        label="Ozon API-ключ"
        placeholder={keysStatus?.has_ozon_api_key ? "Оставьте пустым, чтобы не менять" : "Введите ключ"}
        value={ozonKey}
        onChange={(e) => setOzonKey(e.target.value)}
      />
      <div className="flex flex-wrap gap-2">
        <Button onClick={handleSave} disabled={setKeys.isPending}>
          {setKeys.isPending ? "Сохранение..." : "Сохранить"}
        </Button>
        {hasAny ? (
          <Button variant="ghost" onClick={handleDelete} disabled={deleteKeys.isPending}>
            {deleteKeys.isPending ? "Удаление..." : "Удалить ключи"}
          </Button>
        ) : null}
      </div>
    </div>
  );
}

export function CompanyPage() {
  const { data, isLoading, error, create, update } = useCompanies();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Company | null>(null);
  const [apiKeysCompanyId, setApiKeysCompanyId] = useState<number | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  const companies = data ?? [];

  const handleCreate = async (payload: { inn: string; name?: string; bank_bik?: string; bank_account?: string }) => {
    setPageError(null);
    try {
      await create.mutateAsync(payload);
      setOpen(false);
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
              <Button variant="secondary" onClick={() => setApiKeysCompanyId(company.id)}>
                API-ключи маркетплейсов
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

      <Modal
        title="API-ключи маркетплейсов"
        open={apiKeysCompanyId != null}
        onClose={() => setApiKeysCompanyId(null)}
      >
        {apiKeysCompanyId != null ? (
          <CompanyAPIKeysForm
            companyId={apiKeysCompanyId}
            onSuccess={() => setToast({ message: "Ключи сохранены" })}
            onDelete={() => {
              setToast({ message: "Ключи удалены" });
              setApiKeysCompanyId(null);
            }}
            onError={(msg) => setPageError(msg)}
          />
        ) : null}
      </Modal>

      <Modal title="Новая компания" open={open} onClose={() => setOpen(false)}>
        <CompanyForm isSubmitting={create.isPending} onSubmit={handleCreate} submitLabel="Создать" />
      </Modal>

      <Modal title="Редактирование компании" open={Boolean(editing)} onClose={() => setEditing(null)}>
        <CompanyForm
          initial={editing ? { inn: editing.inn, name: editing.name } : undefined}
          isSubmitting={update.isPending}
          onSubmit={handleUpdate}
          submitLabel="Сохранить"
        />
      </Modal>
    </div>
  );
}

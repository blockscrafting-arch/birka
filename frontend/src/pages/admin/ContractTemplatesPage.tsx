import { useRef, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { ProgressBar } from "../../components/ui/ProgressBar";
import {
  downloadContractTemplate,
  useContractTemplates,
  useDeleteContractTemplate,
  useUpdateContractTemplate,
} from "../../hooks/useContractTemplates";
import { useUploadStore } from "../../stores/uploadStore";

export function ContractTemplatesPage() {
  const { items: templates, isLoading, error } = useContractTemplates();
  const update = useUpdateContractTemplate();
  const remove = useDeleteContractTemplate();
  const [name, setName] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const jobs = useUploadStore((s) => s.jobs);
  const startTemplateUpload = useUploadStore((s) => s.startTemplateUpload);
  const dismissJob = useUploadStore((s) => s.dismissJob);
  const clearDone = useUploadStore((s) => s.clearDone);

  const templateJobs = jobs.filter((j) => j.type === "template");

  const handleUpload = () => {
    if (!name.trim() || !file) return;
    startTemplateUpload(file, name.trim(), isDefault);
    setName("");
    setIsDefault(false);
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSetDefault = (id: number) => {
    update.mutate({ id, is_default: true });
  };

  const handleDownload = (id: number, fileName: string | null) => {
    downloadContractTemplate(id, fileName || "template");
  };

  const placeholders: { key: string; label: string }[] = [
    { key: "company_name", label: "Название компании" },
    { key: "inn", label: "ИНН" },
    { key: "kpp", label: "КПП" },
    { key: "ogrn", label: "ОГРН" },
    { key: "director", label: "Руководитель" },
    { key: "legal_address", label: "Юридический адрес" },
    { key: "bank_name", label: "Банк" },
    { key: "bank_bik", label: "БИК" },
    { key: "bank_account", label: "Расчётный счёт" },
    { key: "bank_corr_account", label: "Корр. счёт" },
    { key: "contract_number", label: "Номер договора" },
    { key: "contract_date", label: "Дата договора" },
    { key: "service_description", label: "Описание услуг" },
  ];

  return (
    <div className="space-y-4">
      <div className="text-lg font-semibold text-slate-900">Шаблоны договоров</div>
      <p className="text-sm text-slate-600">
        Загрузите DOCX или RTF. В тексте шаблона укажите плейсхолдеры в двойных фигурных скобках — при генерации подставятся данные компании и будет выдан PDF.
      </p>
      <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
        Для шаблонов с подстановками рекомендуется DOCX; RTF конвертируется в DOCX при генерации.
      </p>
      <details className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 text-sm">
        <summary className="cursor-pointer font-medium text-slate-700">Список плейсхолдеров</summary>
        <ul className="mt-2 grid gap-1 text-slate-600 sm:grid-cols-2">
          {placeholders.map(({ key, label }) => (
            <li key={key}>
              <code className="rounded bg-white px-1.5 py-0.5 font-mono text-xs">{`{{${key}}}`}</code>
              <span className="ml-2">{label}</span>
            </li>
          ))}
        </ul>
      </details>

      {isLoading ? <div className="text-sm text-slate-600">Загрузка шаблонов...</div> : null}
      {error ? <div className="text-sm text-rose-500">Ошибка загрузки шаблонов</div> : null}

      <div className="space-y-2">
        {templates.map((template) => (
          <div
            key={template.id}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-slate-900">{template.name}</div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  {template.is_default ? (
                    <span className="rounded bg-birka-100 px-1.5 py-0.5 text-birka-700">
                      По умолчанию
                    </span>
                  ) : null}
                  {template.file_type ? (
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">
                      {template.file_type.toUpperCase()}
                    </span>
                  ) : (
                    <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700">
                      HTML
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {template.file_type ? (
                  <Button
                    variant="secondary"
                    onClick={() => handleDownload(template.id, template.file_name)}
                  >
                    Скачать
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    onClick={() => setPreviewTemplate(template)}
                    disabled={!template.html_content}
                  >
                    Просмотр
                  </Button>
                )}
                {!template.is_default && (
                  <Button
                    variant="secondary"
                    onClick={() => handleSetDefault(template.id)}
                    disabled={update.isPending}
                  >
                    Сделать по умолчанию
                  </Button>
                )}
                <Button
                  variant="secondary"
                  onClick={() => remove.mutate(template.id)}
                  disabled={remove.isPending}
                >
                  Удалить
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <Modal
        title={previewTemplate ? `Просмотр: ${previewTemplate.name}` : ""}
        open={previewTemplate !== null}
        onClose={() => setPreviewTemplate(null)}
      >
        {previewTemplate?.html_content ? (
          <iframe
            title="HTML шаблон"
            srcDoc={`<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:system-ui,sans-serif;padding:1rem;max-width:800px;margin:0 auto;}</style></head><body>${previewTemplate.html_content}</body></html>`}
            className="h-[60vh] w-full rounded border border-slate-200"
            sandbox="allow-same-origin"
          />
        ) : (
          <p className="text-sm text-slate-500">Нет содержимого для просмотра.</p>
        )}
      </Modal>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
        <div className="text-sm font-semibold text-slate-900">Загрузить шаблон</div>
        <div className="mt-3 space-y-3">
          <Input
            label="Название"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Например: Договор 2025"
          />
          <div>
            <label className="mb-1 block text-sm text-slate-700">Файл (DOCX или RTF)</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".docx,.rtf"
              className="block w-full text-sm text-slate-600 file:mr-2 file:rounded-lg file:border-0 file:bg-birka-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-birka-700 hover:file:bg-birka-100"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            {file ? (
              <p className="mt-1 text-xs text-slate-500">{file.name}</p>
            ) : null}
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
            />
            Сделать шаблоном по умолчанию
          </label>
          <p className="text-xs text-slate-500">
            После загрузки сервер проверяет, что файл доступен по публичной ссылке. Если проверка не пройдёт, загрузка отменится: убедитесь, что в настройках бэкенда заданы FILE_PUBLIC_BASE_URL и S3 bucket с публичным доступом на чтение.
          </p>
          <Button
            onClick={handleUpload}
            disabled={!name.trim() || !file}
          >
            Загрузить
          </Button>
          {templateJobs
            .filter((j) => j.status === "uploading")
            .map((j) => (
              <ProgressBar
                key={j.id}
                value={j.progress}
                label={j.name ? `${j.name} (${j.fileName})` : j.fileName}
                className="w-full"
              />
            ))}
          {templateJobs
            .filter((j) => j.status === "error")
            .map((j) => (
              <div
                key={j.id}
                className="flex items-center justify-between gap-2 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700"
              >
                <span className="min-w-0 truncate" title={`${j.fileName}: ${j.error}`}>{j.fileName}: {j.error}</span>
                <Button variant="ghost" onClick={() => dismissJob(j.id)}>
                  Скрыть
                </Button>
              </div>
            ))}
          {templateJobs.some((j) => j.status === "done") && (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <span>Загрузки завершены.</span>
              <Button variant="ghost" onClick={clearDone}>
                Очистить
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

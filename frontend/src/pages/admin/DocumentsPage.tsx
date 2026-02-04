/** Страница админки: документы в RAG для AI. Загрузки идут через store и не сбрасываются при смене вкладок. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Page } from "../../components/layout/Page";
import { ProgressBar } from "../../components/ui/ProgressBar";
import { apiClient } from "../../services/api";
import { useUploadStore } from "../../stores/uploadStore";

type DocumentItem = {
  source_file: string;
  chunks_count: number;
  document_type: string;
  version: number;
};

function useAdminDocuments() {
  const query = useQuery({
    queryKey: ["admin", "documents"],
    queryFn: () => apiClient.api<DocumentItem[]>("/admin/documents"),
  });
  return {
    ...query,
    items: query.data ?? [],
  };
}

export function DocumentsPage() {
  const queryClient = useQueryClient();
  const { items: documents, isLoading, error } = useAdminDocuments();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [seedLoading, setSeedLoading] = useState(false);
  const [seedError, setSeedError] = useState<string | null>(null);
  const [syncPriceLoading, setSyncPriceLoading] = useState(false);
  const [syncPriceError, setSyncPriceError] = useState<string | null>(null);

  const jobs = useUploadStore((s) => s.jobs);
  const startDocumentUpload = useUploadStore((s) => s.startDocumentUpload);
  const dismissJob = useUploadStore((s) => s.dismissJob);
  const clearDone = useUploadStore((s) => s.clearDone);

  const documentJobs = jobs.filter((j) => j.type === "document");
  const uploadingCount = documentJobs.filter((j) => j.status === "uploading").length;

  const deleteMutation = useMutation({
    mutationFn: (sourceFile: string) =>
      apiClient.api<{ status: string }>(
        `/admin/documents/${encodeURIComponent(sourceFile)}`,
        { method: "DELETE" }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "documents"] });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    startDocumentUpload(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSeed = async () => {
    setSeedError(null);
    setSeedLoading(true);
    try {
      await apiClient.api<{ status?: string }>("/admin/rag/seed", {
        method: "POST",
        body: JSON.stringify({}),
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "documents"] });
    } catch (err) {
      setSeedError(err instanceof Error ? err.message : "Ошибка заполнения RAG");
    } finally {
      setSeedLoading(false);
    }
  };

  const handleSyncPrice = async () => {
    setSyncPriceError(null);
    setSyncPriceLoading(true);
    try {
      await apiClient.api<{ status?: string; chunks_added?: number }>("/admin/rag/sync-services", {
        method: "POST",
        body: JSON.stringify({}),
      });
      queryClient.invalidateQueries({ queryKey: ["admin", "documents"] });
    } catch (err) {
      setSyncPriceError(err instanceof Error ? err.message : "Ошибка синхронизации прайса");
    } finally {
      setSyncPriceLoading(false);
    }
  };

  return (
    <Page title="Документы для AI">
      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-lg font-semibold text-slate-900">Документы в RAG</div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".docx,.txt,.rtf"
              className="hidden"
              onChange={handleFileChange}
            />
            <Button
              variant="primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingCount > 0}
            >
              {uploadingCount > 0 ? `Загрузка… (${uploadingCount})` : "Загрузить DOCX/TXT/RTF"}
            </Button>
            {documentJobs.map(
              (j) =>
                j.status === "uploading" && (
                  <ProgressBar
                    key={j.id}
                    value={j.progress}
                    label={j.fileName}
                    className="w-full max-w-xs"
                  />
                )
            )}
            <Button
              variant="secondary"
              onClick={handleSyncPrice}
              disabled={syncPriceLoading}
            >
              {syncPriceLoading ? "Синхронизация…" : "Синхронизировать прайс"}
            </Button>
            <Button
              variant="secondary"
              onClick={handleSeed}
              disabled={seedLoading}
            >
              {seedLoading ? "Заполняем…" : "Заполнить RAG (документы из папки)"}
            </Button>
          </div>
        </div>

        {syncPriceError && (
          <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {syncPriceError}
          </div>
        )}

        {documentJobs
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
        {documentJobs.some((j) => j.status === "done") && (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <span>Загрузки завершены.</span>
            <Button variant="ghost" onClick={clearDone}>
              Очистить
            </Button>
          </div>
        )}
        {seedError && (
          <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {seedError}
          </div>
        )}

        {isLoading && <div className="text-sm text-slate-600">Загрузка списка…</div>}
        {error && (
          <div className="text-sm text-rose-500">
            Ошибка загрузки документов
          </div>
        )}

        {!isLoading && !error && documents.length === 0 && (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-sm text-slate-600">
            Нет документов. Загрузите DOCX/TXT/RTF или нажмите «Заполнить RAG».
          </div>
        )}

        {!isLoading && documents.length > 0 && (
          <ul className="space-y-2">
            {documents.map((doc) => (
              <li
                key={doc.source_file}
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white p-4 shadow-soft"
              >
                <div>
                  <div className="font-medium text-slate-900">{doc.source_file}</div>
                  <div className="text-xs text-slate-500">
                    {doc.chunks_count} чанков · {doc.document_type || "—"} · v{doc.version}
                  </div>
                </div>
                <Button
                  variant="secondary"
                  onClick={() => deleteMutation.mutate(doc.source_file)}
                  disabled={deleteMutation.isPending}
                >
                  Удалить
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Page>
  );
}

import { create } from "zustand";
import { apiClient } from "../services/api";

export type UploadJob = {
  id: string;
  type: "document" | "template";
  fileName: string;
  progress: number;
  status: "uploading" | "done" | "error";
  error?: string;
  name?: string;
  isDefault?: boolean;
};

type UploadStore = {
  jobs: UploadJob[];
  invalidateDocuments: (() => void) | null;
  invalidateTemplates: (() => void) | null;
  setInvalidateDocuments: (fn: (() => void) | null) => void;
  setInvalidateTemplates: (fn: (() => void) | null) => void;
  startDocumentUpload: (file: File) => string;
  startTemplateUpload: (file: File, name: string, isDefault: boolean) => string;
  updateProgress: (id: string, percent: number) => void;
  dismissJob: (id: string) => void;
  clearDone: () => void;
};

function genId(): string {
  return `upload-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export const useUploadStore = create<UploadStore>((set, get) => ({
  jobs: [],
  invalidateDocuments: null,
  invalidateTemplates: null,

  setInvalidateDocuments: (fn) => set({ invalidateDocuments: fn }),
  setInvalidateTemplates: (fn) => set({ invalidateTemplates: fn }),

  updateProgress: (id, percent) => {
    set((s) => ({
      jobs: s.jobs.map((j) => (j.id === id ? { ...j, progress: percent } : j)),
    }));
  },

  dismissJob: (id) => {
    set((s) => ({ jobs: s.jobs.filter((j) => j.id !== id) }));
  },

  clearDone: () => {
    set((s) => ({ jobs: s.jobs.filter((j) => j.status === "uploading") }));
  },

  startDocumentUpload: (file: File) => {
    const id = genId();
    const job: UploadJob = {
      id,
      type: "document",
      fileName: file.name,
      progress: 0,
      status: "uploading",
    };
    set((s) => ({ jobs: [...s.jobs, job] }));

    const form = new FormData();
    form.append("file", file);
    apiClient
      .apiFormWithProgress<{ source_file: string; chunks_added: number }>(
        "/admin/documents",
        form,
        (percent) => get().updateProgress(id, percent)
      )
      .then(() => {
        set((s) => ({
          jobs: s.jobs.map((j) => (j.id === id ? { ...j, status: "done" as const, progress: 100 } : j)),
        }));
        get().invalidateDocuments?.();
      })
      .catch((err: Error) => {
        set((s) => ({
          jobs: s.jobs.map((j) =>
            j.id === id ? { ...j, status: "error" as const, error: err.message } : j
          ),
        }));
      });
    return id;
  },

  startTemplateUpload: (file: File, name: string, isDefault: boolean) => {
    const id = genId();
    const job: UploadJob = {
      id,
      type: "template",
      fileName: file.name,
      progress: 0,
      status: "uploading",
      name,
      isDefault,
    };
    set((s) => ({ jobs: [...s.jobs, job] }));

    const form = new FormData();
    form.append("file", file);
    form.append("name", name);
    form.append("is_default", String(isDefault));
    apiClient
      .apiFormWithProgress<unknown>("/admin/contract-templates/upload", form, (percent) =>
        get().updateProgress(id, percent)
      )
      .then(() => {
        set((s) => ({
          jobs: s.jobs.map((j) => (j.id === id ? { ...j, status: "done" as const, progress: 100 } : j)),
        }));
        get().invalidateTemplates?.();
      })
      .catch((err: Error) => {
        set((s) => ({
          jobs: s.jobs.map((j) =>
            j.id === id ? { ...j, status: "error" as const, error: err.message } : j
          ),
        }));
      });
    return id;
  },
}));

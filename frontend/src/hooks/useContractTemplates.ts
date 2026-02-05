import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";

export type ContractTemplate = {
  id: number;
  name: string;
  html_content: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  file_name: string | null;
  file_type: string | null;
};

export function useContractTemplates() {
  const query = useQuery({
    queryKey: ["contract-templates"],
    queryFn: () => apiClient.api<ContractTemplate[]>("/admin/contract-templates"),
  });
  return {
    ...query,
    items: query.data ?? [],
  };
}

type UploadPayload = {
  file: File;
  name: string;
  is_default: boolean;
  onProgress?: (percent: number) => void;
};

export function useUploadContractTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, name, is_default, onProgress }: UploadPayload) => {
      const form = new FormData();
      form.append("file", file);
      form.append("name", name);
      form.append("is_default", String(is_default));
      return apiClient.apiFormWithProgress<ContractTemplate>(
        "/admin/contract-templates/upload",
        form,
        onProgress
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contract-templates"] });
    },
  });
}

type UpdatePayload = { id: number; name?: string; is_default?: boolean };

export function useUpdateContractTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: UpdatePayload) =>
      apiClient.api<ContractTemplate>(`/admin/contract-templates/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contract-templates"] });
    },
  });
}

export function useDeleteContractTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiClient.api<{ status: string }>(`/admin/contract-templates/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contract-templates"] });
    },
  });
}

/** Send template file to current user in Telegram chat with the bot. */
export async function sendContractTemplateToTelegram(templateId: number): Promise<void> {
  await apiClient.api(`/admin/contract-templates/${templateId}/send`, { method: "POST" });
}

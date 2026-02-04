import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { Service, ServiceCalculateResponse } from "../types";

const SERVICES_KEY = "services";
const CATEGORIES_KEY = "services-categories";

export function useServices(options?: {
  category?: string;
  includeInactive?: boolean;
  search?: string;
}) {
  const params = new URLSearchParams();
  if (options?.category?.trim()) params.set("category", options.category.trim());
  if (options?.includeInactive) params.set("include_inactive", "true");
  const searchTrimmed = options?.search?.trim();
  if (searchTrimmed) params.set("q", searchTrimmed);
  const queryString = params.toString();
  const query = useQuery({
    queryKey: [
      SERVICES_KEY,
      options?.category ?? "",
      options?.includeInactive ?? false,
      options?.search ?? "",
    ],
    queryFn: () => {
      const path = queryString ? `/services?${queryString}` : "/services";
      return apiClient.api<Service[]>(path);
    },
  });
  return { ...query, items: query.data ?? [] };
}

export function useServiceCategories() {
  const query = useQuery({
    queryKey: [CATEGORIES_KEY],
    queryFn: () => apiClient.api<string[]>("/services/categories"),
  });
  return { ...query, categories: query.data ?? [] };
}

export function useCalculateServices() {
  return useMutation({
    mutationFn: (items: { service_id: number; quantity: number }[]) =>
      apiClient.api<ServiceCalculateResponse>("/services/calculate", {
        method: "POST",
        body: JSON.stringify({ items }),
      }),
  });
}

export function useCreateService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      category: string;
      name: string;
      price: number;
      unit?: string;
      comment?: string | null;
      is_active?: boolean;
      sort_order?: number;
    }) =>
      apiClient.api<Service>("/services", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SERVICES_KEY] });
      queryClient.invalidateQueries({ queryKey: [CATEGORIES_KEY] });
    },
  });
}

export function useUpdateService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      id: number;
      category?: string;
      name?: string;
      price?: number;
      unit?: string;
      comment?: string | null;
      is_active?: boolean;
      sort_order?: number;
    }) => {
      const { id, ...body } = payload;
      return apiClient.api<Service>(`/services/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SERVICES_KEY] });
      queryClient.invalidateQueries({ queryKey: [CATEGORIES_KEY] });
    },
  });
}

export function useDeleteService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiClient.api(`/services/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SERVICES_KEY] });
      queryClient.invalidateQueries({ queryKey: [CATEGORIES_KEY] });
    },
  });
}

export function useImportServices() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return apiClient.apiForm<{ created: number; updated: number }>("/services/import", form);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SERVICES_KEY] });
      queryClient.invalidateQueries({ queryKey: [CATEGORIES_KEY] });
    },
  });
}

export function useReorderServices() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (items: { id: number; sort_order: number }[]) =>
      apiClient.api<Service[]>("/services/reorder", {
        method: "PATCH",
        body: JSON.stringify({ items }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SERVICES_KEY] });
      queryClient.invalidateQueries({ queryKey: [CATEGORIES_KEY] });
    },
  });
}

export function useExportServices() {
  return useMutation({
    mutationFn: async () => {
      const { downloadFile } = await import("../services/api");
      await downloadFile("/services/export", "services.xlsx");
    },
  });
}

export function useExportServicesPdf() {
  return useMutation({
    mutationFn: async () => {
      const { downloadFile } = await import("../services/api");
      await downloadFile("/services/pdf", "prajs-birka.pdf");
    },
  });
}

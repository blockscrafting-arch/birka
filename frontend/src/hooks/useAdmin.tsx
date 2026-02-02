import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { AdminUser, ContractTemplate, Destination } from "../types";

export function useAdminUsers(search?: string) {
  const query = useQuery({
    queryKey: ["admin-users", search ?? ""],
    queryFn: () => {
      const params = search?.trim() ? `?search=${encodeURIComponent(search.trim())}` : "";
      return apiClient.api<AdminUser[]>(`/admin/users${params}`);
    },
  });

  return { ...query, items: query.data ?? [] };
}

export function useUpdateUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { id: number; role: string }) =>
      apiClient.api(`/admin/users/${payload.id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: payload.role }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    },
  });
}

export function useContractTemplates() {
  const query = useQuery({
    queryKey: ["contract-templates"],
    queryFn: () => apiClient.api<ContractTemplate[]>("/admin/contract-templates"),
  });
  return { ...query, items: query.data ?? [] };
}

export function useCreateContractTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; html_content: string; is_default: boolean }) =>
      apiClient.api<ContractTemplate>("/admin/contract-templates", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contract-templates"] });
    },
  });
}

export function useUpdateContractTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      id: number;
      name?: string;
      html_content?: string;
      is_default?: boolean;
    }) =>
      apiClient.api<ContractTemplate>(`/admin/contract-templates/${payload.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: payload.name,
          html_content: payload.html_content,
          is_default: payload.is_default,
        }),
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
      apiClient.api(`/admin/contract-templates/${id}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contract-templates"] });
    },
  });
}

export function useAdminDestinations() {
  const query = useQuery({
    queryKey: ["admin-destinations"],
    queryFn: () => apiClient.api<Destination[]>("/destinations?active_only=false"),
  });
  return { ...query, items: query.data ?? [] };
}

export function useCreateDestination() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string }) =>
      apiClient.api<Destination>("/destinations", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-destinations"] });
      queryClient.invalidateQueries({ queryKey: ["destinations"] });
    },
  });
}

export function useUpdateDestination() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { id: number; name?: string; is_active?: boolean }) =>
      apiClient.api<Destination>(`/destinations/${payload.id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: payload.name, is_active: payload.is_active }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-destinations"] });
      queryClient.invalidateQueries({ queryKey: ["destinations"] });
    },
  });
}

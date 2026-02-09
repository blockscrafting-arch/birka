import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";

export type AdminUser = {
  id: number;
  telegram_id: number;
  telegram_username: string | null;
  first_name: string | null;
  last_name: string | null;
  role: string;
  created_at: string;
};

export type AdminUserListResponse = {
  items: AdminUser[];
  total: number;
  page: number;
  limit: number;
};

export function useAdminUsers(search?: string, page = 1) {
  const query = useQuery({
    queryKey: ["admin", "users", search ?? "", page],
    queryFn: () => {
      const params = new URLSearchParams();
      if (search?.trim()) params.set("search", search.trim());
      params.set("page", String(page));
      params.set("limit", "20");
      return apiClient.api<AdminUserListResponse>(`/admin/users?${params.toString()}`);
    },
  });
  const data = query.data;
  return {
    ...query,
    items: data?.items ?? [],
    total: data?.total ?? 0,
    page: data?.page ?? 1,
    limit: data?.limit ?? 20,
  };
}

type RoleUpdatePayload = { id: number; role: string };

export function useUpdateUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role }: RoleUpdatePayload) =>
      apiClient.api<{ status: string }>(`/admin/users/${id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
}

export type Destination = {
  id: number;
  name: string;
  is_active: boolean;
};

export function useAdminDestinations() {
  const query = useQuery({
    queryKey: ["admin", "destinations"],
    queryFn: () =>
      apiClient.api<Destination[]>("/destinations?active_only=false"),
  });
  return {
    ...query,
    items: query.data ?? [],
  };
}

type CreateDestinationPayload = { name: string };

export function useCreateDestination() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateDestinationPayload) =>
      apiClient.api<Destination>("/destinations", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "destinations"] });
    },
  });
}

type UpdateDestinationPayload = { id: number; name?: string; is_active?: boolean };

export function useUpdateDestination() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: UpdateDestinationPayload) =>
      apiClient.api<Destination>(`/destinations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "destinations"] });
    },
  });
}

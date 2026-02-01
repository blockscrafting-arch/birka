import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { ShippingRequest } from "../types";

type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  limit: number;
};

type ShippingCreate = {
  company_id: number;
  destination_type: string;
  destination_comment?: string;
};

export function useShipping(companyId?: number, page = 1, limit = 20) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["shipping", companyId, page, limit],
    queryFn: () =>
      apiClient.api<Paginated<ShippingRequest>>(`/shipping?company_id=${companyId}&page=${page}&limit=${limit}`),
    enabled: Boolean(companyId),
  });

  const create = useMutation({
    mutationFn: (payload: ShippingCreate) =>
      apiClient.api<ShippingRequest>("/shipping", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shipping"] });
    },
  });

  const updateStatus = useMutation({
    mutationFn: (payload: { id: number; status: string }) =>
      apiClient.api<ShippingRequest>(`/shipping/${payload.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: payload.status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shipping"] });
    },
  });

  return {
    ...query,
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    limit: query.data?.limit ?? limit,
    create,
    updateStatus,
  };
}

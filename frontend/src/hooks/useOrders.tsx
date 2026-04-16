import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { Order } from "../types";

type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  limit: number;
};

type OrderCreate = {
  company_id: number;
  destination?: string;
  items: { product_id: number; planned_qty: number; destination?: string }[];
  services?: { service_id: number; quantity: number }[];
};

export function useOrders(
  companyId?: number,
  page = 1,
  limit = 20,
  status?: string,
  search?: string
) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["orders", companyId, page, limit, status, search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (companyId != null) params.set("company_id", String(companyId));
      params.set("page", String(page));
      params.set("limit", String(limit));
      if (status) params.set("status", status);
      if (search && search.trim()) params.set("search", search.trim());
      return apiClient.api<Paginated<Order>>(`/orders?${params.toString()}`);
    },
    enabled: true,
  });

  const create = useMutation({
    mutationFn: (payload: OrderCreate) =>
      apiClient.api<Order>("/orders", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  const updateStatus = useMutation({
    mutationFn: (payload: { id: number; status: string }) =>
      apiClient.api<Order>(`/orders/${payload.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: payload.status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });

  const importExcel = useMutation({
    mutationFn: (payload: { companyId: number; file: File }) => {
      const formData = new FormData();
      formData.append("file", payload.file);
      return apiClient.apiForm<Order>(
        `/orders/import?company_id=${payload.companyId}`,
        formData,
        { method: "POST" }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
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
    importExcel,
  };
}

export type PackingRecord = {
  id: number;
  product_id: number;
  product_name: string;
  pallet_number: number | null;
  box_number: number | null;
  quantity: number;
  warehouse: string | null;
  box_barcode: string | null;
  materials_used: string | null;
  time_spent_minutes: number | null;
  created_at: string | null;
};

export function useOrderPackingRecords(orderId: number | undefined) {
  return useQuery({
    queryKey: ["order-packing-records", orderId],
    queryFn: () => apiClient.api<PackingRecord[]>(`/orders/${orderId}/packing-records`),
    enabled: Boolean(orderId),
  });
}

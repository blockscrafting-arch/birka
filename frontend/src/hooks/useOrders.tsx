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
  items: { product_id: number; planned_qty: number }[];
};

export function useOrders(companyId?: number, page = 1, limit = 20) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["orders", companyId, page, limit],
    queryFn: () =>
      apiClient.api<Paginated<Order>>(`/orders?company_id=${companyId}&page=${page}&limit=${limit}`),
    enabled: Boolean(companyId),
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

  return {
    ...query,
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    limit: query.data?.limit ?? limit,
    create,
  };
}

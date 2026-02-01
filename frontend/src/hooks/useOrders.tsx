import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { Order } from "../types";

type OrderCreate = {
  company_id: number;
  destination?: string;
  items: { product_id: number; planned_qty: number }[];
};

export function useOrders(companyId?: number) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["orders", companyId],
    queryFn: () => apiClient.api<Order[]>(`/orders?company_id=${companyId}`),
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

  return { ...query, create };
}

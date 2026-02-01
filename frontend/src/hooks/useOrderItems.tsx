import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { OrderItem } from "../types";

export function useOrderItems(orderId?: number) {
  return useQuery({
    queryKey: ["order-items", orderId],
    queryFn: () => apiClient.api<OrderItem[]>(`/orders/${orderId}/items`),
    enabled: Boolean(orderId),
  });
}

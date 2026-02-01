import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { OrderPhoto } from "../types";

export function useOrderPhotos(orderId?: number) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["order-photos", orderId],
    queryFn: () => apiClient.api<OrderPhoto[]>(`/orders/${orderId}/photos`),
    enabled: Boolean(orderId),
  });

  const upload = useMutation({
    mutationFn: (payload: { orderId: number; file: File; photo_type?: string; product_id?: number }) => {
      const formData = new FormData();
      formData.append("file", payload.file);
      const params = new URLSearchParams();
      if (payload.photo_type) {
        params.set("photo_type", payload.photo_type);
      }
      if (payload.product_id) {
        params.set("product_id", String(payload.product_id));
      }
      const suffix = params.toString() ? `?${params.toString()}` : "";
      return apiClient.apiForm<{ key: string }>(`/orders/${payload.orderId}/photo${suffix}`, formData);
    },
    onSuccess: (_, payload) => {
      queryClient.invalidateQueries({ queryKey: ["order-photos", payload.orderId] });
    },
  });

  return { ...query, upload };
}

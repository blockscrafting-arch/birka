import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../services/api";

export function useProductDefectPhotos(productId?: number) {
  return useQuery({
    queryKey: ["product-defect-photos", productId],
    queryFn: () => apiClient.api<string[]>(`/products/${productId}/defect-photos`),
    enabled: Boolean(productId),
  });
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { Product } from "../types";

type ProductCreate = {
  company_id: number;
  name: string;
  barcode?: string;
};

export function useProducts(companyId?: number) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["products", companyId],
    queryFn: () => apiClient.api<Product[]>(`/products?company_id=${companyId}`),
    enabled: Boolean(companyId),
  });

  const create = useMutation({
    mutationFn: (payload: ProductCreate) =>
      apiClient.api<Product>("/products", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });

  return { ...query, create };
}

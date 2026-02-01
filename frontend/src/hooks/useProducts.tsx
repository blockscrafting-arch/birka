import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { Product } from "../types";

type ProductCreate = {
  company_id: number;
  name: string;
  brand?: string;
  size?: string;
  color?: string;
  barcode?: string;
  wb_article?: string;
  wb_url?: string;
  packing_instructions?: string;
};

type ProductUpdate = Partial<Omit<ProductCreate, "company_id">> & { id: number };

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

  const update = useMutation({
    mutationFn: ({ id, ...payload }: ProductUpdate) =>
      apiClient.api<Product>(`/products/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });

  const uploadPhoto = useMutation({
    mutationFn: (payload: { productId: number; file: File }) => {
      const formData = new FormData();
      formData.append("file", payload.file);
      return apiClient.apiForm<{ key: string }>(`/products/${payload.productId}/photo`, formData);
    },
  });

  const importExcel = useMutation({
    mutationFn: (payload: { companyId: number; file: File }) => {
      const formData = new FormData();
      formData.append("file", payload.file);
      return apiClient.apiForm<{ imported: number }>(`/products/import?company_id=${payload.companyId}`, formData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });

  return { ...query, create, update, uploadPhoto, importExcel };
}

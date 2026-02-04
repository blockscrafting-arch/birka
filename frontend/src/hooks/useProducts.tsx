import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { Product } from "../types";

type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  limit: number;
};

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
  supplier_name?: string;
};

type ProductUpdate = Partial<Omit<ProductCreate, "company_id">> & { id: number };

export type ImportResult = {
  imported: number;
  updated: number;
  skipped: { barcode: string; name: string; reason: string }[];
};

export function useProducts(companyId?: number, page = 1, limit = 20, search?: string) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["products", companyId, page, limit, search],
    queryFn: () => {
      const searchParam = search ? `&search=${encodeURIComponent(search)}` : "";
      return apiClient.api<Paginated<Product>>(
        `/products?company_id=${companyId}&page=${page}&limit=${limit}${searchParam}`
      );
    },
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
      return apiClient.apiForm<ImportResult>(
        `/products/import?company_id=${payload.companyId}`,
        formData
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });

  return {
    ...query,
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    limit: query.data?.limit ?? limit,
    create,
    update,
    uploadPhoto,
    importExcel,
  };
}

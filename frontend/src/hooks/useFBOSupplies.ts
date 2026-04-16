import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import type { FBOSupply } from "../types";

export type { FBOSupply };

type Paginated<T> = { items: T[]; total: number; page: number; limit: number };

export function useFBOSupplies(companyId?: number, page = 1, limit = 20) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["fbo", "supplies", companyId, page, limit],
    queryFn: () =>
      apiClient.api<Paginated<FBOSupply>>(
        `/fbo/supplies?company_id=${companyId}&page=${page}&limit=${limit}`
      ),
    enabled: Boolean(companyId),
  });

  const create = useMutation({
    mutationFn: (payload: {
      company_id: number;
      marketplace: string;
      warehouse_name?: string;
      boxes?: { box_number: number; items: { product_id: number; quantity: number }[] }[];
    }) =>
      apiClient.api<FBOSupply>("/fbo/supplies", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo"] });
    },
  });

  const sync = useMutation({
    mutationFn: (supplyId: number) =>
      apiClient.api<FBOSupply>(`/fbo/supplies/${supplyId}/sync`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo"] });
    },
  });

  const remove = useMutation({
    mutationFn: (supplyId: number) =>
      apiClient.api<{ deleted: boolean }>(`/fbo/supplies/${supplyId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo"] });
    },
  });

  const importBarcodes = useMutation({
    mutationFn: (payload: { supplyId: number; barcodes: Record<number, string> }) =>
      apiClient.api<FBOSupply>(`/fbo/supplies/${payload.supplyId}/import-barcodes`, {
        method: "POST",
        body: JSON.stringify({ barcodes: payload.barcodes }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo"] });
    },
  });

  const downloadLabels = (supplyId: number) =>
    apiClient.apiFile(`/fbo/supplies/${supplyId}/labels`);

  return {
    ...query,
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    limit: query.data?.limit ?? limit,
    create,
    sync,
    remove,
    importBarcodes,
    downloadLabels,
  };
}

export function useFBOSupply(supplyId: number | null) {
  return useQuery({
    queryKey: ["fbo", "supply", supplyId],
    queryFn: () => apiClient.api<FBOSupply>(`/fbo/supplies/${supplyId}`),
    enabled: Boolean(supplyId),
  });
}

export type FBOSupplyCreatePayload = {
  company_id: number;
  order_id?: number;
  marketplace: string;
  box_count?: number;
};

export function useFBOCreate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: FBOSupplyCreatePayload) =>
      apiClient.api<FBOSupply>("/fbo/supplies", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo"] });
    },
  });
}

export function useFBOSyncBarcodes(supplyId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiClient.api<FBOSupply>(`/fbo/supplies/${supplyId}/sync`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo", "supply", supplyId] });
      queryClient.invalidateQueries({ queryKey: ["fbo"] });
    },
  });
}

export function useFBOImportBarcodes(supplyId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (barcodes: string[]) =>
      apiClient.api<FBOSupply>(`/fbo/supplies/${supplyId}/import-barcodes`, {
        method: "POST",
        body: JSON.stringify({ barcodes }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo", "supply", supplyId] });
      queryClient.invalidateQueries({ queryKey: ["fbo"] });
    },
  });
}

export type BoxSticker = {
  trbx_id: string;
  barcode: string | null;
  file_base64: string;
  content_type: string;
};

export type BoxStickersResponse = { stickers: BoxSticker[] };

export function useFBOBoxStickers(supplyId: number | null) {
  return useMutation({
    mutationFn: (fmt?: string) =>
      apiClient.api<BoxStickersResponse>(
        `/fbo/supplies/${supplyId}/box-stickers${fmt ? `?fmt=${fmt}` : ""}`,
        { method: "POST" }
      ),
  });
}

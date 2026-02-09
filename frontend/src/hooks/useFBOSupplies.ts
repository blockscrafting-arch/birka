import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";

export type FBOSupplyItem = {
  id: number;
  box_id: number;
  product_id: number;
  quantity: number;
  barcode: string | null;
};

export type FBOSupplyBox = {
  id: number;
  supply_id: number;
  box_number: number;
  barcode: string | null;
  sticker_s3_key: string | null;
  external_box_id: string | null;
  items: FBOSupplyItem[];
};

export type FBOSupply = {
  id: number;
  company_id: number;
  marketplace: string;
  external_supply_id: string | null;
  warehouse_name: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  boxes: FBOSupplyBox[];
};

type BoxCreate = {
  box_number: number;
  items: { product_id: number; quantity: number; barcode?: string | null }[];
};

type SupplyCreatePayload = {
  company_id: number;
  marketplace: "wb" | "ozon";
  warehouse_name?: string | null;
  boxes: BoxCreate[];
};

export function useFBOSupplies(companyId: number | null) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["fbo-supplies", companyId],
    queryFn: () =>
      apiClient.api<FBOSupply[]>(`/fbo/supplies?company_id=${companyId}`),
    enabled: companyId != null,
  });

  const create = useMutation({
    mutationFn: (payload: SupplyCreatePayload) =>
      apiClient.api<FBOSupply>("/fbo/supplies", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo-supplies"] });
    },
  });

  const sync = useMutation({
    mutationFn: (supplyId: number) =>
      apiClient.api<FBOSupply>(`/fbo/supplies/${supplyId}/sync`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo-supplies"] });
    },
  });

  const remove = useMutation({
    mutationFn: (supplyId: number) =>
      apiClient.api(`/fbo/supplies/${supplyId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo-supplies"] });
    },
  });

  const importBarcodes = useMutation({
    mutationFn: ({
      supplyId,
      barcodes,
    }: {
      supplyId: number;
      barcodes: Record<number, string>;
    }) =>
      apiClient.api<FBOSupply>(`/fbo/supplies/${supplyId}/import-barcodes`, {
        method: "POST",
        body: JSON.stringify({ barcodes }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fbo-supplies"] });
    },
  });

  const downloadLabels = async (
    supplyId: number,
  ): Promise<{ blob: Blob; filename: string | null }> => {
    return apiClient.apiFile(`/fbo/supplies/${supplyId}/labels`);
  };

  return {
    data: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    create,
    sync,
    remove,
    importBarcodes,
    downloadLabels,
  };
}

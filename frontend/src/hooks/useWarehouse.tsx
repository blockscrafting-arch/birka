import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";

export function useWarehouse() {
  const queryClient = useQueryClient();
  const completeReceiving = useMutation({
    mutationFn: (payload: {
      order_id: number;
      items: {
        order_item_id: number;
        received_qty: number;
        defect_qty: number;
        adjustment_qty: number;
        adjustment_note?: string;
      }[];
    }) =>
      apiClient.api("/warehouse/receiving/complete", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["order-items"] });
    },
  });

  const createPacking = useMutation({
    mutationFn: (payload: {
      order_id: number;
      product_id: number;
      employee_code: string;
      quantity: number;
      pallet_number?: string;
      box_number?: string;
      warehouse?: string;
      materials_used?: string;
      time_spent_minutes?: number;
      box_barcode?: string;
    }) =>
      apiClient.api("/warehouse/packing/record", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["order-items"] });
    },
  });

  const validateBarcode = useMutation({
    mutationFn: (payload: { barcode: string }) =>
      apiClient.api<{
        valid: boolean;
        message: string;
        product?: {
          id: number;
          name: string;
          brand?: string | null;
          size?: string | null;
          color?: string | null;
          wb_article?: string | null;
          barcode?: string | null;
        };
      }>("/warehouse/barcode/validate", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  });

  const completeOrder = useMutation({
    mutationFn: (orderId: number) =>
      apiClient.api(`/warehouse/order/${orderId}/complete`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["order-items"] });
    },
  });

  return { completeReceiving, createPacking, validateBarcode, completeOrder };
}

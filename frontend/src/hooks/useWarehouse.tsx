import { useMutation } from "@tanstack/react-query";

import { apiClient } from "../services/api";

export function useWarehouse() {
  const completeReceiving = useMutation({
    mutationFn: (payload: { order_id: number; items: { order_item_id: number; received_qty: number; defect_qty: number }[] }) =>
      apiClient.api("/warehouse/receiving/complete", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
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
  });

  const validateBarcode = useMutation({
    mutationFn: (payload: { barcode: string }) =>
      apiClient.api<{ valid: boolean; message: string }>("/warehouse/barcode/validate", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  });

  return { completeReceiving, createPacking, validateBarcode };
}

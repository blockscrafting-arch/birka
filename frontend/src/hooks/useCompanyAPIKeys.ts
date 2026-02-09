import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";

export type CompanyAPIKeysStatus = {
  has_wb: boolean;
  has_ozon_client_id: boolean;
  has_ozon_api_key: boolean;
};

export type CompanyAPIKeysSetPayload = {
  wb_api_key?: string | null;
  ozon_client_id?: string | null;
  ozon_api_key?: string | null;
};

export function useCompanyAPIKeys(companyId: number | null) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["company-api-keys", companyId],
    queryFn: () =>
      apiClient.api<CompanyAPIKeysStatus>(`/companies/${companyId}/api-keys`),
    enabled: companyId != null,
  });

  const setKeys = useMutation({
    mutationFn: (payload: CompanyAPIKeysSetPayload) =>
      apiClient.api<CompanyAPIKeysStatus>(`/companies/${companyId}/api-keys`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-api-keys", companyId] });
    },
  });

  const deleteKeys = useMutation({
    mutationFn: () =>
      apiClient.api(`/companies/${companyId}/api-keys`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-api-keys", companyId] });
    },
  });

  return {
    data: query.data,
    isLoading: query.isLoading,
    error: query.error,
    setKeys,
    deleteKeys,
  };
}

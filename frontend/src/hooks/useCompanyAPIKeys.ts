import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";

export type CompanyAPIKeysOut = {
  company_id: number;
  wb_api_key: string | null;
  ozon_client_id: string | null;
  ozon_api_key: string | null;
};

export type CompanyAPIKeysUpdate = {
  wb_api_key?: string;
  ozon_client_id?: string;
  ozon_api_key?: string;
};

export function useCompanyAPIKeys(companyId: number | null) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["company-api-keys", companyId],
    queryFn: () =>
      apiClient.api<CompanyAPIKeysOut>(`/companies/${companyId}/api-keys`),
    enabled: companyId != null,
  });

  const update = useMutation({
    mutationFn: (payload: CompanyAPIKeysUpdate) =>
      apiClient.api<CompanyAPIKeysOut>(`/companies/${companyId}/api-keys`, {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-api-keys", companyId] });
    },
  });

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    error: query.error,
    update,
  };
}

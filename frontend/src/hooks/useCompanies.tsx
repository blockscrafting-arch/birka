import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { Company } from "../types";

type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  limit: number;
};

type CompanyCreate = {
  inn: string;
  name?: string;
  bank_bik?: string;
  bank_account?: string;
  bank_name?: string;
  bank_corr_account?: string;
};

type CompanyUpdate = Partial<CompanyCreate> & {
  id: number;
};

export function useCompanies(page = 1, limit = 20) {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["companies", page, limit],
    queryFn: () => apiClient.api<Paginated<Company>>(`/companies?page=${page}&limit=${limit}`),
  });

  const create = useMutation({
    mutationFn: (payload: CompanyCreate) => apiClient.api<Company>("/companies", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["companies"] });
    },
  });

  const update = useMutation({
    mutationFn: ({ id, ...payload }: CompanyUpdate) =>
      apiClient.api<Company>(`/companies/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["companies"] });
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
  };
}

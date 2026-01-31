import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { Company } from "../types";

type CompanyCreate = {
  inn: string;
  name?: string;
  bank_bik?: string;
  bank_account?: string;
};

export function useCompanies() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["companies"],
    queryFn: () => apiClient.api<Company[]>("/companies"),
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

  return { ...query, create };
}

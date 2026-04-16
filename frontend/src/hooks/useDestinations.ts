import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { Destination } from "../types";

/**
 * Fetch list of active destinations for order form.
 */
export function useDestinations(activeOnly = true) {
  const query = useQuery({
    queryKey: ["destinations", activeOnly],
    queryFn: () =>
      apiClient.api<Destination[]>(`/destinations?active_only=${activeOnly}`),
  });
  return {
    ...query,
    items: query.data ?? [],
  };
}

import { createContext, ReactNode, useContext } from "react";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../services/api";
import { CurrentUser } from "../types";

type UserContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
  error: Error | null;
  refresh: () => void;
};

const UserContext = createContext<UserContextValue>({
  user: null,
  isLoading: false,
  error: null,
  refresh: () => undefined,
});

type UserProviderProps = {
  children: ReactNode;
};

export function UserProvider({ children }: UserProviderProps) {
  const query = useQuery({
    queryKey: ["current-user"],
    queryFn: () => apiClient.api<CurrentUser>("/auth/me"),
    retry: false,
  });

  return (
    <UserContext.Provider
      value={{
        user: query.data ?? null,
        isLoading: query.isLoading,
        error: (query.error as Error | null) ?? null,
        refresh: () => query.refetch(),
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}

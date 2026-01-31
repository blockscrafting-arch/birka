import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useCompanies } from "../hooks/useCompanies";

function CompaniesView() {
  const { data } = useCompanies();
  return <div>{data ? data.length : 0}</div>;
}

describe("useCompanies", () => {
  it("loads companies list", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 1, inn: "1", name: "Test" }],
    } as Response);

    const client = new QueryClient();
    render(
      <QueryClientProvider client={client}>
        <CompaniesView />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("1")).toBeInTheDocument();
    });
  });
});

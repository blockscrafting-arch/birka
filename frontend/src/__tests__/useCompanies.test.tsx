import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useCompanies } from "../hooks/useCompanies";

function CompaniesView() {
  const { items } = useCompanies();
  return <div>{items.length}</div>;
}

describe("useCompanies", () => {
  it("loads companies list", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({ items: [{ id: 1, inn: "1", name: "Test" }], total: 1, page: 1, limit: 20 }),
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

import { describe, expect, it, vi } from "vitest";

import { apiClient } from "../services/api";

describe("apiClient", () => {
  it("sends session token header", async () => {
    localStorage.setItem("birka_session_token", "token-123");
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    } as Response);

    await apiClient.api("/companies");
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    const options = call[1] as RequestInit;
    const headers = options.headers as Record<string, string>;
    expect(headers["X-Session-Token"]).toBe("token-123");
  });

  it("sends initData header when no session", async () => {
    localStorage.removeItem("birka_session_token");
    (window as any).Telegram = { WebApp: { initData: "init-data" } };
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    } as Response);

    await apiClient.api("/companies");
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    const options = call[1] as RequestInit;
    const headers = options.headers as Record<string, string>;
    expect(headers["X-Telegram-Init-Data"]).toBe("init-data");
  });
});

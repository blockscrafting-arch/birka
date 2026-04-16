import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "../services/api";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("apiClient", () => {
  it("sends session token header", async () => {
    localStorage.setItem("birka_session_token", "token-123");
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    } as Response);

    await apiClient.api("/companies");
    const call = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    const options = call[1] as RequestInit;
    const headers = options.headers as Record<string, string>;
    expect(headers["X-Session-Token"]).toBe("token-123");
  });

  it("sends initData header when no session", async () => {
    localStorage.removeItem("birka_session_token");
    window.Telegram = { WebApp: { initData: "init-data" } as never };
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    } as Response);

    await apiClient.api("/companies");
    const call = (globalThis.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0];
    const options = call[1] as RequestInit;
    const headers = options.headers as Record<string, string>;
    expect(headers["X-Telegram-Init-Data"]).toBe("init-data");
  });

  // ── Фаза 9: расширение ──────────────────────────────────────────────────────

  it("clears token and throws on 401", async () => {
    localStorage.setItem("birka_session_token", "old-token");
    window.Telegram = { WebApp: { initData: "valid-init-data", showAlert: vi.fn() } as never };

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Unauthorized" }),
    } as Response);

    await expect(apiClient.api("/companies")).rejects.toThrow();
    expect(localStorage.getItem("birka_session_token")).toBeNull();
  });

  it("clears token and does not retry when no initData on 401", async () => {
    localStorage.setItem("birka_session_token", "old-token");
    window.Telegram = { WebApp: { initData: undefined, showAlert: vi.fn() } as never };

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Unauthorized" }),
    } as Response);

    await expect(apiClient.api("/companies")).rejects.toThrow();
    expect(localStorage.getItem("birka_session_token")).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("retries on 502 and succeeds", async () => {
    localStorage.setItem("birka_session_token", "token-abc");
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: false, status: 502, json: async () => ({}) } as Response)
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [] }) } as Response);

    const result = await apiClient.api<{ items: unknown[] }>("/orders");
    expect(result).toEqual({ items: [] });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not retry on 400 — throws immediately", async () => {
    localStorage.setItem("birka_session_token", "token-abc");
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Bad request" }),
    } as Response);

    await expect(apiClient.api("/orders")).rejects.toThrow("Bad request");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("uses custom error detail message from 400 response", async () => {
    localStorage.setItem("birka_session_token", "token-abc");
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Кастомная ошибка" }),
    } as Response);

    await expect(apiClient.api("/test")).rejects.toThrow("Кастомная ошибка");
  });

  it("throws generic error when response body is not JSON", async () => {
    localStorage.setItem("birka_session_token", "token-abc");
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => { throw new Error("not json"); },
    } as unknown as Response);

    await expect(apiClient.api("/test")).rejects.toThrow();
  });
});

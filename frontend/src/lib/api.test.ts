import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("health parses json", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          status: "ok",
          mock_mode: true,
          features: ["text_generation"],
        }),
      }),
    );
    const h = await api.health();
    expect(h.status).toBe("ok");
    expect(h.mock_mode).toBe(true);
  });

  it("throws with status on error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Server Error",
        json: async () => ({ detail: "boom" }),
      }),
    );
    await expect(api.health()).rejects.toThrow(/500/);
  });

  it("image posts prompt body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ data_url: "data:image/svg+xml,x", mock: true }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const r = await api.image("hello");
    expect(r.mock).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/image/generate",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ prompt: "hello" }),
      }),
    );
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetchJson } from "../lib/query/api";

const originalFetch = globalThis.fetch;
const originalApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

function mockJsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();

  if (originalApiBaseUrl === undefined) {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  } else {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalApiBaseUrl;
  }
});

describe("apiFetchJson", () => {
  it("sends browser credentials to protected API routes by default", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test/";
    const fetchMock = vi.fn(async () => mockJsonResponse({ ok: true }));
    globalThis.fetch = fetchMock;

    await expect(apiFetchJson("/protected/me")).resolves.toEqual({ ok: true });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/protected/me",
      expect.objectContaining({
        credentials: "include",
        headers: expect.objectContaining({
          Accept: "application/json",
        }),
      }),
    );
  });

  it("allows callers to override credentials when needed", async () => {
    const fetchMock = vi.fn(async () => mockJsonResponse({ ok: true }));
    globalThis.fetch = fetchMock;

    await apiFetchJson("/public", { credentials: "omit" });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/public",
      expect.objectContaining({
        credentials: "omit",
      }),
    );
  });
});

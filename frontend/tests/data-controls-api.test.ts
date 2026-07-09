import { afterEach, describe, expect, it, vi } from "vitest";

import {
  connectGarmin,
  deleteAccountData,
  deleteSyncedData,
  disconnectGarmin,
  triggerManualSync,
} from "@/lib/api/dataControls";

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

describe("data control API client", () => {
  it("connects Garmin with JSON credentials and optional MFA code", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test";
    const responseBody = {
      id: "connection-1",
      source: "garmin",
      status: "active",
      provider_subject_id: "provider-1",
      display_name: "Runner Example",
      requires_mfa: false,
      message: null,
    };
    const fetchMock = vi.fn(async () => mockJsonResponse(responseBody));
    globalThis.fetch = fetchMock;

    await expect(
      connectGarmin({
        username: "runner@example.test",
        password: "garmin-password",
        mfa_code: "123456",
        is_cn: true,
      }),
    ).resolves.toEqual(responseBody);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/connections/garmin",
      expect.objectContaining({
        credentials: "include",
        method: "POST",
        headers: expect.objectContaining({
          Accept: "application/json",
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({
          username: "runner@example.test",
          password: "garmin-password",
          is_cn: true,
          mfa_code: "123456",
        }),
      }),
    );
  });

  it("omits an empty Garmin MFA code", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test";
    const fetchMock = vi.fn(async () =>
      mockJsonResponse({
        id: null,
        source: "garmin",
        status: "mfa_required",
        provider_subject_id: null,
        display_name: null,
        requires_mfa: true,
        message: "Garmin requires a multi-factor authentication code.",
      }),
    );
    globalThis.fetch = fetchMock;

    await connectGarmin({
      username: "runner@example.test",
      password: "garmin-password",
      mfa_code: "",
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/connections/garmin",
      expect.objectContaining({
        body: JSON.stringify({
          username: "runner@example.test",
          password: "garmin-password",
          is_cn: false,
        }),
      }),
    );
  });

  it("triggers manual sync with JSON request body", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test";
    const responseBody = {
      id: "sync-run-1",
      source_connection_id: "source-1",
      status: "succeeded",
      sync_type: "manual",
      window_start: "2026-07-03T00:00:00Z",
      window_end: "2026-07-09T23:59:59Z",
      records_seen: 5,
      records_imported: 4,
      error_code: null,
      started_at: "2026-07-09T10:00:00Z",
      completed_at: "2026-07-09T10:01:00Z",
    };
    const fetchMock = vi.fn(async () => mockJsonResponse(responseBody));
    globalThis.fetch = fetchMock;

    await expect(
      triggerManualSync({
        source: "garmin",
        start_date: "2026-07-03",
        end_date: "2026-07-09",
      }),
    ).resolves.toEqual(responseBody);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/sync/manual",
      expect.objectContaining({
        credentials: "include",
        method: "POST",
        headers: expect.objectContaining({
          Accept: "application/json",
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({
          source: "garmin",
          start_date: "2026-07-03",
          end_date: "2026-07-09",
        }),
      }),
    );
  });

  it("calls Garmin disconnect and lifecycle delete endpoints", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test";
    const fetchMock = vi.fn(async () => mockJsonResponse({ ok: true }));
    globalThis.fetch = fetchMock;

    await disconnectGarmin();
    await deleteSyncedData({ source: "garmin" });
    await deleteSyncedData();
    await deleteAccountData();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api.test/connections/garmin",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://api.test/users/me/data?source=garmin",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://api.test/users/me/data",
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "http://api.test/users/me",
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

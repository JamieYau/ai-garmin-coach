import { afterEach, describe, expect, it, vi } from "vitest";

import { getApiErrorMessage } from "@/lib/api/errors";
import {
  fetchDashboardOverview,
  fetchLatestCoachInsight,
  fetchRecentActivities,
  fetchRecoveryMetrics,
  fetchSleepTrend,
} from "@/lib/api/dashboard";
import { ApiError } from "@/lib/query/api";

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

describe("dashboard API client", () => {
  it("fetches the dashboard overview from the backend API", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test/";
    const responseBody = {
      activity: {
        activity_count_7d: 1,
        duration_seconds_7d: 1800,
        distance_meters_7d: "5000.00",
        latest_activity_date: "2026-07-07",
      },
      recovery: {
        metric_date: "2026-07-07",
        steps: 12000,
        active_seconds: 3600,
        resting_heart_rate: 48,
        hrv_ms: "62.50",
        body_battery_latest: 76,
        stress_average: "22.40",
      },
      sleep: {
        sleep_date: "2026-07-07",
        total_sleep_seconds: 28800,
        sleep_score: 84,
        average_hrv_ms: "64.10",
      },
      latest_insight: null,
      sync: {
        connected_sources: 1,
        active_sources: 1,
        has_demo_data: false,
        latest_sync_status: "succeeded",
        latest_sync_completed_at: "2026-07-07T10:30:00",
        latest_sync_error_code: null,
      },
    };
    const fetchMock = vi.fn(async () => mockJsonResponse(responseBody));
    globalThis.fetch = fetchMock;

    await expect(fetchDashboardOverview()).resolves.toEqual(responseBody);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/dashboard/overview",
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("fetches dashboard detail endpoints with typed query parameters", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test";
    const fetchMock = vi.fn(async () => mockJsonResponse({ ok: true }));
    globalThis.fetch = fetchMock;

    await fetchRecentActivities({ limit: 5 });
    await fetchSleepTrend({ days: 30 });
    await fetchRecoveryMetrics({ days: 7 });
    await fetchLatestCoachInsight();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api.test/dashboard/activities/recent?limit=5",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://api.test/dashboard/sleep/trend?days=30",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://api.test/dashboard/recovery/metrics?days=7",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      "http://api.test/dashboard/coach/latest",
      expect.any(Object),
    );
  });

  it("omits optional query params so backend defaults apply", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://api.test";
    const fetchMock = vi.fn(async () => mockJsonResponse({ ok: true }));
    globalThis.fetch = fetchMock;

    await fetchRecentActivities();
    await fetchSleepTrend();
    await fetchRecoveryMetrics();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://api.test/dashboard/activities/recent",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "http://api.test/dashboard/sleep/trend",
      expect.any(Object),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "http://api.test/dashboard/recovery/metrics",
      expect.any(Object),
    );
  });
});

describe("API error helpers", () => {
  it("maps authentication and server errors to user-facing messages", () => {
    expect(getApiErrorMessage(new ApiError("Unauthorized", 401))).toBe(
      "Sign in again to view your dashboard data.",
    );
    expect(getApiErrorMessage(new ApiError("Server error", 503))).toBe(
      "The API is temporarily unavailable.",
    );
  });

  it("falls back for unknown thrown values", () => {
    expect(getApiErrorMessage(null)).toBe(
      "The dashboard data could not be loaded.",
    );
  });

  it("maps network failures to an API availability message", () => {
    expect(getApiErrorMessage(new TypeError("Failed to fetch"))).toBe(
      "The API is unavailable. Start the backend and try again.",
    );
  });
});

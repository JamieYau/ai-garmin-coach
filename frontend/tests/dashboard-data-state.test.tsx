import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  classifyDashboardDataState,
  DashboardDataStateBanner,
} from "@/components/dashboard/DashboardDataState";
import type { DashboardOverviewResponse } from "@/lib/api/dashboard";

const baseOverview: DashboardOverviewResponse = {
  activity: {
    activity_count_7d: 2,
    duration_seconds_7d: 5400,
    distance_meters_7d: "16000.00",
    latest_activity_date: "2026-07-07",
  },
  recovery: {
    metric_date: "2026-07-07",
    steps: 9000,
    active_seconds: 3600,
    resting_heart_rate: 49,
    hrv_ms: "62.20",
    body_battery_latest: 74,
    stress_average: "23.40",
  },
  sleep: {
    sleep_date: "2026-07-07",
    total_sleep_seconds: 28200,
    sleep_score: 84,
    average_hrv_ms: "63.10",
  },
  latest_insight: {
    id: "insight-1",
    insight_date: "2026-07-07",
    insight_type: "daily",
    title: "Keep aerobic volume steady",
    summary: "Recovery supports controlled training.",
    recommendation: "Keep the next workout easy.",
    generated_at: "2026-07-07T10:30:00Z",
  },
  sync: {
    connected_sources: 1,
    active_sources: 1,
    has_demo_data: false,
    latest_sync_status: "succeeded",
    latest_sync_completed_at: "2026-07-07T09:15:00Z",
    latest_sync_error_code: null,
  },
};

function overviewWith(
  overrides: Partial<DashboardOverviewResponse>,
): DashboardOverviewResponse {
  return {
    ...baseOverview,
    ...overrides,
    activity: {
      ...baseOverview.activity,
      ...overrides.activity,
    },
    recovery: {
      ...baseOverview.recovery,
      ...overrides.recovery,
    },
    sleep: {
      ...baseOverview.sleep,
      ...overrides.sleep,
    },
    sync: {
      ...baseOverview.sync,
      ...overrides.sync,
    },
  };
}

describe("dashboard data state", () => {
  it("classifies no-data, demo, running, failed, stale, and ready states", () => {
    expect(
      classifyDashboardDataState(
        overviewWith({
          sync: {
            connected_sources: 0,
            active_sources: 0,
            has_demo_data: false,
            latest_sync_status: null,
            latest_sync_completed_at: null,
            latest_sync_error_code: null,
          },
        }),
      ),
    ).toBe("no-data");

    expect(
      classifyDashboardDataState(
        overviewWith({ sync: { ...baseOverview.sync, has_demo_data: true } }),
      ),
    ).toBe("demo-data");

    expect(
      classifyDashboardDataState(
        overviewWith({
          sync: { ...baseOverview.sync, latest_sync_status: "running" },
        }),
      ),
    ).toBe("sync-in-progress");

    expect(
      classifyDashboardDataState(
        overviewWith({
          sync: {
            ...baseOverview.sync,
            latest_sync_status: "failed",
            latest_sync_error_code: "garmin_connection_retryable",
          },
        }),
      ),
    ).toBe("sync-failed");

    expect(
      classifyDashboardDataState(
        overviewWith({
          activity: {
            activity_count_7d: 0,
            duration_seconds_7d: 0,
            distance_meters_7d: null,
            latest_activity_date: null,
          },
          recovery: {
            metric_date: null,
            steps: null,
            active_seconds: null,
            resting_heart_rate: null,
            hrv_ms: null,
            body_battery_latest: null,
            stress_average: null,
          },
          sleep: {
            sleep_date: null,
            total_sleep_seconds: null,
            sleep_score: null,
            average_hrv_ms: null,
          },
          latest_insight: null,
        }),
      ),
    ).toBe("connected-no-recent-records");

    expect(classifyDashboardDataState(baseOverview)).toBe("ready");
  });

  it("renders state banner copy and hides the ready state", () => {
    expect(
      renderToStaticMarkup(<DashboardDataStateBanner state="ready" />),
    ).toBe("");

    const demoMarkup = renderToStaticMarkup(
      <DashboardDataStateBanner state="demo-data" />,
    );
    expect(demoMarkup).toContain("Demo data is showing");
    expect(demoMarkup).toContain("local seeded demo records");
    expect(demoMarkup).toContain("p-3 sm:gap-3 sm:p-4");
    expect(demoMarkup).toContain("min-w-0");

    const failedMarkup = renderToStaticMarkup(
      <DashboardDataStateBanner state="sync-failed" />,
    );
    expect(failedMarkup).toContain("Latest sync failed");
    expect(failedMarkup).toContain("Existing data may be stale");
  });
});

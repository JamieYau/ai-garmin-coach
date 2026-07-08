import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DashboardSources } from "@/components/dashboard/DashboardSources";
import type { DashboardOverviewResponse } from "@/lib/api/dashboard";

const connectedOverview: DashboardOverviewResponse = {
  activity: {
    activity_count_7d: 3,
    duration_seconds_7d: 13200,
    distance_meters_7d: "42195.00",
    latest_activity_date: "2026-07-07",
  },
  recovery: {
    metric_date: "2026-07-07",
    steps: 12450,
    active_seconds: 5400,
    resting_heart_rate: 48,
    hrv_ms: "64.20",
    body_battery_latest: 82,
    stress_average: "21.50",
  },
  sleep: {
    sleep_date: "2026-07-07",
    total_sleep_seconds: 28680,
    sleep_score: 88,
    average_hrv_ms: "66.70",
  },
  latest_insight: {
    id: "insight-1",
    insight_date: "2026-07-07",
    insight_type: "daily",
    title: "Hold aerobic volume steady",
    summary: "Recovery is strong enough for a controlled aerobic session.",
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

const disconnectedOverview: DashboardOverviewResponse = {
  ...connectedOverview,
  latest_insight: null,
  sync: {
    connected_sources: 0,
    active_sources: 0,
    has_demo_data: false,
    latest_sync_status: null,
    latest_sync_completed_at: null,
    latest_sync_error_code: null,
  },
};

describe("DashboardSources", () => {
  it("renders connection counts, sync health, and coverage context", () => {
    const markup = renderToStaticMarkup(
      <DashboardSources overview={connectedOverview} />,
    );

    expect(markup).toContain("Data source status");
    expect(markup).toContain("Connected");
    expect(markup).toContain("Active");
    expect(markup).toContain("Succeeded");
    expect(markup).toContain("Ready");
    expect(markup).toContain("Sync status");
    expect(markup).toContain("1/1");
    expect(markup).toContain("No issue recorded");
    expect(markup).toContain("Dashboard data coverage");
    expect(markup).toContain("3 in the last 7 days");
    expect(markup).toContain("Latest 2026-07-07");
  });

  it("renders a disconnected source state", () => {
    const markup = renderToStaticMarkup(
      <DashboardSources overview={disconnectedOverview} />,
    );

    expect(markup).toContain("No data sources connected");
    expect(markup).toContain("Connect Garmin");
    expect(markup).toContain("Not connected");
    expect(markup).toContain("Not synced");
  });
});

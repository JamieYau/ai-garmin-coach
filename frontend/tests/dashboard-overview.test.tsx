import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DashboardOverview } from "@/components/dashboard/DashboardOverview";
import type { DashboardOverviewResponse } from "@/lib/api/dashboard";

const seededOverview: DashboardOverviewResponse = {
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
    recommendation:
      "Keep the next workout easy and avoid stacking intensity after the long run.",
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

describe("DashboardOverview", () => {
  it("renders seeded metrics and latest coach insight", () => {
    const markup = renderToStaticMarkup(
      <DashboardOverview overview={seededOverview} />,
    );

    expect(markup).toContain("Coaching overview");
    expect(markup).toContain("3h 40m");
    expect(markup).toContain("3 activities, 42 km");
    expect(markup).toContain("82/100");
    expect(markup).toContain("HRV 64.2 ms");
    expect(markup).toContain("7h 58m");
    expect(markup).toContain("88/100 sleep score");
    expect(markup).toContain("Hold aerobic volume steady");
    expect(markup).toContain("Keep the next workout easy");
    expect(markup).toContain("1/1 active");
    expect(markup).toContain("sm:grid-cols-2");
    expect(markup).toContain("lg:grid-cols-3");
    expect(markup).toContain("min-w-0");
  });
});

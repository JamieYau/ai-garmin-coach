import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DashboardSleepRecovery } from "@/components/dashboard/DashboardSleepRecovery";
import type {
  DashboardRecoveryMetricsResponse,
  DashboardSleepTrendResponse,
} from "@/lib/api/dashboard";

const seededSleep: DashboardSleepTrendResponse = {
  days: 14,
  sleep_sessions: [
    {
      id: "sleep-1",
      sleep_date: "2026-07-06",
      started_at: "2026-07-05T22:35:00Z",
      ended_at: "2026-07-06T06:20:00Z",
      total_sleep_seconds: 27900,
      deep_sleep_seconds: 4200,
      rem_sleep_seconds: 5400,
      light_sleep_seconds: 16500,
      awake_seconds: 1800,
      sleep_score: 82,
      average_spo2: "97.20",
      average_hrv_ms: "61.40",
      average_respiration: "13.10",
    },
    {
      id: "sleep-2",
      sleep_date: "2026-07-07",
      started_at: "2026-07-06T22:50:00Z",
      ended_at: "2026-07-07T06:42:00Z",
      total_sleep_seconds: 28320,
      deep_sleep_seconds: 4500,
      rem_sleep_seconds: 6000,
      light_sleep_seconds: 16200,
      awake_seconds: 1620,
      sleep_score: 88,
      average_spo2: "97.60",
      average_hrv_ms: "66.70",
      average_respiration: "12.80",
    },
  ],
};

const seededRecovery: DashboardRecoveryMetricsResponse = {
  days: 14,
  metrics: [
    {
      metric_date: "2026-07-06",
      steps: 9400,
      active_seconds: 4200,
      highly_active_seconds: 1200,
      resting_heart_rate: 49,
      hrv_ms: "62.30",
      stress_average: "24.50",
      body_battery_min: 35,
      body_battery_max: 86,
      body_battery_latest: 74,
    },
    {
      metric_date: "2026-07-07",
      steps: 12450,
      active_seconds: 5400,
      highly_active_seconds: 1800,
      resting_heart_rate: 48,
      hrv_ms: "64.20",
      stress_average: "21.50",
      body_battery_min: 42,
      body_battery_max: 91,
      body_battery_latest: 82,
    },
  ],
};

const emptySleep: DashboardSleepTrendResponse = {
  days: 14,
  sleep_sessions: [],
};

const emptyRecovery: DashboardRecoveryMetricsResponse = {
  days: 14,
  metrics: [],
};

describe("DashboardSleepRecovery", () => {
  it("renders sleep, recovery, charts, and daily context", () => {
    const markup = renderToStaticMarkup(
      <DashboardSleepRecovery sleep={seededSleep} recovery={seededRecovery} />,
    );

    expect(markup).toContain("Sleep and recovery");
    expect(markup).toContain("7h 52m");
    expect(markup).toContain("85/100");
    expect(markup).toContain("63.3 ms");
    expect(markup).toContain("82/100");
    expect(markup).toContain("Sleep trend");
    expect(markup).toContain("Recovery trend");
    expect(markup).toContain("Daily recovery log");
    expect(markup).toContain("64.2 ms");
    expect(markup).toContain("48 bpm");
    expect(markup).toContain("12,450");
    expect(markup).toContain("Latest daily context");
    expect(markup).toContain("sm:grid-cols-2");
    expect(markup).toContain(
      "Swipe horizontally to view all recovery details.",
    );
    expect(markup).toContain("grid min-w-0 gap-3");
    expect(markup).toContain("h-72 w-full");
  });

  it("renders an empty sleep and recovery state", () => {
    const markup = renderToStaticMarkup(
      <DashboardSleepRecovery sleep={emptySleep} recovery={emptyRecovery} />,
    );

    expect(markup).toContain("No sleep or recovery data yet");
    expect(markup).toContain("Complete a Garmin sync");
  });
});

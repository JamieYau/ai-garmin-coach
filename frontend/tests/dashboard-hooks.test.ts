import { describe, expect, it } from "vitest";

import { dashboardQueryKeys } from "@/hooks/useDashboard";

describe("dashboard query keys", () => {
  it("uses stable keys for dashboard query hooks", () => {
    expect(dashboardQueryKeys.overview()).toEqual(["dashboard", "overview"]);
    expect(dashboardQueryKeys.recentActivities()).toEqual([
      "dashboard",
      "activities",
      "recent",
      10,
    ]);
    expect(dashboardQueryKeys.recentActivities(5)).toEqual([
      "dashboard",
      "activities",
      "recent",
      5,
    ]);
    expect(dashboardQueryKeys.sleepTrend(30)).toEqual([
      "dashboard",
      "sleep",
      "trend",
      30,
    ]);
    expect(dashboardQueryKeys.recoveryMetrics(7)).toEqual([
      "dashboard",
      "recovery",
      "metrics",
      7,
    ]);
    expect(dashboardQueryKeys.latestCoachInsight()).toEqual([
      "dashboard",
      "coach",
      "latest",
    ]);
  });
});

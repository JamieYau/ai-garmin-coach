import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DashboardActivities } from "@/components/dashboard/DashboardActivities";
import type { DashboardActivityDetail } from "@/lib/api/dashboard";

const seededActivities: DashboardActivityDetail[] = [
  {
    id: "activity-1",
    activity_type: "running",
    name: "Morning aerobic run",
    activity_date: "2026-07-08",
    started_at: "2026-07-08T06:30:00Z",
    duration_seconds: 2700,
    moving_duration_seconds: 2640,
    distance_meters: "8800.00",
    calories: 640,
    average_heart_rate: 143,
    training_load: "78.40",
  },
  {
    id: "activity-2",
    activity_type: "cycling",
    name: "Easy spin",
    activity_date: "2026-07-06",
    started_at: "2026-07-06T17:15:00Z",
    duration_seconds: 3600,
    moving_duration_seconds: 3420,
    distance_meters: "24500.00",
    calories: 520,
    average_heart_rate: 118,
    training_load: "44.10",
  },
];

describe("DashboardActivities", () => {
  it("renders activity totals, chart, activity mix, and recent rows", () => {
    const markup = renderToStaticMarkup(
      <DashboardActivities activities={seededActivities} />,
    );

    expect(markup).toContain("Training activity");
    expect(markup).toContain("2");
    expect(markup).toContain("1h 45m");
    expect(markup).toContain("33 km");
    expect(markup).toContain("131 bpm");
    expect(markup).toContain("Recent distance");
    expect(markup).toContain("Activity mix");
    expect(markup).toContain("Running");
    expect(markup).toContain("Cycling");
    expect(markup).toContain("Morning aerobic run");
    expect(markup).toContain("Easy spin");
    expect(markup).toContain("5:00/km");
    expect(markup).toContain("78");
  });

  it("renders an empty activity state", () => {
    const markup = renderToStaticMarkup(
      <DashboardActivities activities={[]} />,
    );

    expect(markup).toContain("No activities yet");
    expect(markup).toContain("Complete a Garmin sync");
  });
});

import { describe, expect, it } from "vitest";

import { buildDemoDataset } from "../scripts/seed-demo-data.mjs";

describe("demo seed data", () => {
  it("builds dashboard-ready demo records", () => {
    const dataset = buildDemoDataset();

    expect(dataset.activities).toHaveLength(5);
    expect(dataset.dailyMetrics).toHaveLength(14);
    expect(dataset.sleepSessions).toHaveLength(10);
    expect(dataset.activities[0]).toMatchObject({
      sourceActivityId: "demo-run-aerobic",
      type: "running",
      distanceMeters: "9100.00",
    });
    expect(dataset.activities.some((activity) => activity.trainingLoad)).toBe(
      true,
    );
    expect(dataset.dailyMetrics.at(-1)).toMatchObject({
      bodyBatteryLatest: expect.any(Number),
      hrvMs: expect.any(String),
    });
    expect(dataset.sleepSessions.at(-1)).toMatchObject({
      sleepScore: expect.any(Number),
      averageHrvMs: expect.any(String),
    });
  });
});

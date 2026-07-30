import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DashboardCoachInsight } from "@/components/dashboard/DashboardCoachInsight";
import type { DashboardInsightDetail } from "@/lib/api/dashboard";

const seededInsight: DashboardInsightDetail = {
  id: "insight-1",
  insight_date: "2026-07-08",
  insight_type: "daily_recovery",
  title: "Hold aerobic volume steady",
  summary: "Recovery is strong enough for controlled aerobic training.",
  recommendation:
    "Run easy for 45 minutes and avoid stacking intensity before sleep improves.",
  generated_at: "2026-07-08T10:30:00Z",
  schema_version: "coach.v1",
  model_provider: "local",
  model_name: "deterministic-coach",
  prompt_version: "daily-v1",
  output: {
    readiness: "moderate",
    confidence: "0.82",
    risk_flags: ["sleep_debt"],
    actions: [
      "Keep the next run conversational",
      "Add mobility after training",
    ],
    supporting_metrics: {
      hrv_ms: 61.4,
      sleep_score: 76,
      training_load_7d: 342,
    },
  },
};

describe("DashboardCoachInsight", () => {
  it("renders the latest insight detail, structured output, and metadata", () => {
    const markup = renderToStaticMarkup(
      <DashboardCoachInsight insight={seededInsight} />,
    );

    expect(markup).toContain("Coach insight");
    expect(markup).toContain("Hold aerobic volume steady");
    expect(markup).toContain("Daily Recovery");
    expect(markup).toContain("Moderate");
    expect(markup).toContain("0.82");
    expect(markup).toContain("sleep_debt");
    expect(markup).toContain("Run easy for 45 minutes");
    expect(markup).toContain("Keep the next run conversational");
    expect(markup).toContain("Supporting metrics");
    expect(markup).toContain("Hrv Ms");
    expect(markup).toContain("61.4");
    expect(markup).toContain("deterministic-coach");
    expect(markup).toContain("daily-v1");
    expect(markup).toContain("sm:grid-cols-2");
    expect(markup).toContain("min-w-0");
  });

  it("renders an empty coach insight state", () => {
    const markup = renderToStaticMarkup(
      <DashboardCoachInsight insight={null} />,
    );

    expect(markup).toContain("No coach insight yet");
    expect(markup).toContain("Complete a Garmin sync");
  });
});

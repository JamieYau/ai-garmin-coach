import { apiFetchJson } from "@/lib/query/api";

export type IsoDateString = string;
export type IsoDateTimeString = string;
export type DecimalString = string;

export type DashboardActivitySummary = {
  activity_count_7d: number;
  duration_seconds_7d: number;
  distance_meters_7d: DecimalString | null;
  latest_activity_date: IsoDateString | null;
};

export type DashboardActivityDetail = {
  id: string;
  activity_type: string;
  name: string | null;
  activity_date: IsoDateString;
  started_at: IsoDateTimeString;
  duration_seconds: number;
  moving_duration_seconds: number | null;
  distance_meters: DecimalString | null;
  calories: number | null;
  average_heart_rate: number | null;
  training_load: DecimalString | null;
};

export type DashboardRecoverySummary = {
  metric_date: IsoDateString | null;
  steps: number | null;
  active_seconds: number | null;
  resting_heart_rate: number | null;
  hrv_ms: DecimalString | null;
  body_battery_latest: number | null;
  stress_average: DecimalString | null;
};

export type DashboardRecoveryMetricPoint = {
  metric_date: IsoDateString;
  steps: number | null;
  active_seconds: number | null;
  highly_active_seconds: number | null;
  resting_heart_rate: number | null;
  hrv_ms: DecimalString | null;
  stress_average: DecimalString | null;
  body_battery_min: number | null;
  body_battery_max: number | null;
  body_battery_latest: number | null;
};

export type DashboardSleepSummary = {
  sleep_date: IsoDateString | null;
  total_sleep_seconds: number | null;
  sleep_score: number | null;
  average_hrv_ms: DecimalString | null;
};

export type DashboardSleepTrendPoint = {
  id: string;
  sleep_date: IsoDateString;
  started_at: IsoDateTimeString;
  ended_at: IsoDateTimeString;
  total_sleep_seconds: number;
  deep_sleep_seconds: number | null;
  rem_sleep_seconds: number | null;
  light_sleep_seconds: number | null;
  awake_seconds: number | null;
  sleep_score: number | null;
  average_spo2: DecimalString | null;
  average_hrv_ms: DecimalString | null;
  average_respiration: DecimalString | null;
};

export type DashboardInsightSummary = {
  id: string;
  insight_date: IsoDateString;
  insight_type: string;
  title: string;
  summary: string;
  recommendation: string | null;
  generated_at: IsoDateTimeString;
};

export type DashboardInsightDetail = DashboardInsightSummary & {
  schema_version: string;
  model_provider: string | null;
  model_name: string | null;
  prompt_version: string | null;
  output: Record<string, unknown>;
};

export type DashboardSyncSummary = {
  connected_sources: number;
  active_sources: number;
  latest_sync_status: string | null;
  latest_sync_completed_at: IsoDateTimeString | null;
  latest_sync_error_code: string | null;
};

export type DashboardOverviewResponse = {
  activity: DashboardActivitySummary;
  recovery: DashboardRecoverySummary;
  sleep: DashboardSleepSummary;
  latest_insight: DashboardInsightSummary | null;
  sync: DashboardSyncSummary;
};

export type DashboardRecentActivitiesResponse = {
  activities: DashboardActivityDetail[];
};

export type DashboardSleepTrendResponse = {
  days: number;
  sleep_sessions: DashboardSleepTrendPoint[];
};

export type DashboardRecoveryMetricsResponse = {
  days: number;
  metrics: DashboardRecoveryMetricPoint[];
};

function withSearchParams(
  path: string,
  params: Record<string, string | number | undefined>,
) {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) {
      searchParams.set(key, String(value));
    }
  }

  const query = searchParams.toString();
  return query ? `${path}?${query}` : path;
}

export function fetchDashboardOverview() {
  return apiFetchJson<DashboardOverviewResponse>("/dashboard/overview");
}

export function fetchRecentActivities(options: { limit?: number } = {}) {
  return apiFetchJson<DashboardRecentActivitiesResponse>(
    withSearchParams("/dashboard/activities/recent", {
      limit: options.limit,
    }),
  );
}

export function fetchSleepTrend(options: { days?: number } = {}) {
  return apiFetchJson<DashboardSleepTrendResponse>(
    withSearchParams("/dashboard/sleep/trend", {
      days: options.days,
    }),
  );
}

export function fetchRecoveryMetrics(options: { days?: number } = {}) {
  return apiFetchJson<DashboardRecoveryMetricsResponse>(
    withSearchParams("/dashboard/recovery/metrics", {
      days: options.days,
    }),
  );
}

export function fetchLatestCoachInsight() {
  return apiFetchJson<DashboardInsightDetail | null>("/dashboard/coach/latest");
}

"use client";

import { useQuery, type UseQueryOptions } from "@tanstack/react-query";

import {
  fetchDashboardOverview,
  fetchLatestCoachInsight,
  fetchRecentActivities,
  fetchRecoveryMetrics,
  fetchSleepTrend,
  type DashboardInsightDetail,
  type DashboardOverviewResponse,
  type DashboardRecentActivitiesResponse,
  type DashboardRecoveryMetricsResponse,
  type DashboardSleepTrendResponse,
} from "@/lib/api/dashboard";

type DashboardQueryOptions<TData> = Omit<
  UseQueryOptions<TData, Error>,
  "queryKey" | "queryFn"
>;

export const dashboardQueryKeys = {
  all: ["dashboard"] as const,
  overview: () => [...dashboardQueryKeys.all, "overview"] as const,
  recentActivities: (limit = 10) =>
    [...dashboardQueryKeys.all, "activities", "recent", limit] as const,
  sleepTrend: (days = 14) =>
    [...dashboardQueryKeys.all, "sleep", "trend", days] as const,
  recoveryMetrics: (days = 14) =>
    [...dashboardQueryKeys.all, "recovery", "metrics", days] as const,
  latestCoachInsight: () =>
    [...dashboardQueryKeys.all, "coach", "latest"] as const,
};

export function useDashboardOverviewQuery(
  options?: DashboardQueryOptions<DashboardOverviewResponse>,
) {
  return useQuery({
    queryKey: dashboardQueryKeys.overview(),
    queryFn: fetchDashboardOverview,
    ...options,
  });
}

export function useRecentActivitiesQuery(
  params: { limit?: number } = {},
  options?: DashboardQueryOptions<DashboardRecentActivitiesResponse>,
) {
  const limit = params.limit ?? 10;

  return useQuery({
    queryKey: dashboardQueryKeys.recentActivities(limit),
    queryFn: () => fetchRecentActivities({ limit }),
    ...options,
  });
}

export function useSleepTrendQuery(
  params: { days?: number } = {},
  options?: DashboardQueryOptions<DashboardSleepTrendResponse>,
) {
  const days = params.days ?? 14;

  return useQuery({
    queryKey: dashboardQueryKeys.sleepTrend(days),
    queryFn: () => fetchSleepTrend({ days }),
    ...options,
  });
}

export function useRecoveryMetricsQuery(
  params: { days?: number } = {},
  options?: DashboardQueryOptions<DashboardRecoveryMetricsResponse>,
) {
  const days = params.days ?? 14;

  return useQuery({
    queryKey: dashboardQueryKeys.recoveryMetrics(days),
    queryFn: () => fetchRecoveryMetrics({ days }),
    ...options,
  });
}

export function useLatestCoachInsightQuery(
  options?: DashboardQueryOptions<DashboardInsightDetail | null>,
) {
  return useQuery({
    queryKey: dashboardQueryKeys.latestCoachInsight(),
    queryFn: fetchLatestCoachInsight,
    ...options,
  });
}

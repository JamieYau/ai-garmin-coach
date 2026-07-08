"use client";

import { DashboardCoachInsight } from "@/components/dashboard/DashboardCoachInsight";
import { ErrorState, Skeleton } from "@/components/states";
import { useLatestCoachInsightQuery } from "@/hooks/useDashboard";
import { getApiErrorMessage } from "@/lib/api/errors";

function DashboardCoachInsightSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6 sm:px-8 lg:px-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
        <div className="w-full max-w-2xl">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="mt-3 h-9 w-72 max-w-full" />
          <Skeleton className="mt-3 h-4 w-full" />
          <Skeleton className="mt-2 h-4 w-3/4" />
        </div>
        <Skeleton className="h-7 w-36" />
      </header>

      <section
        className="grid gap-4 md:grid-cols-4"
        aria-label="Loading coach insight summary"
      >
        {["readiness", "confidence", "risk-flags", "generated"].map((item) => (
          <div
            key={item}
            className="rounded-lg border border-border bg-card p-5 shadow-sm"
          >
            <div className="flex items-center justify-between gap-3">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="size-5" />
            </div>
            <Skeleton className="mt-5 h-8 w-28" />
            <Skeleton className="mt-3 h-4 w-32 max-w-full" />
          </div>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </section>
    </div>
  );
}

export function DashboardCoachInsightClient() {
  const insightQuery = useLatestCoachInsightQuery();

  if (insightQuery.isPending) {
    return <DashboardCoachInsightSkeleton />;
  }

  if (insightQuery.isError) {
    return (
      <div className="mx-auto w-full max-w-7xl px-6 py-6 sm:px-8 lg:px-10">
        <ErrorState
          title="Coach insight failed to load"
          description={getApiErrorMessage(insightQuery.error)}
          actionLabel="Try again"
          onAction={() => void insightQuery.refetch()}
        />
      </div>
    );
  }

  return <DashboardCoachInsight insight={insightQuery.data} />;
}

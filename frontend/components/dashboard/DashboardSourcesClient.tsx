"use client";

import { DashboardSources } from "@/components/dashboard/DashboardSources";
import { ErrorState, Skeleton } from "@/components/states";
import { useDashboardOverviewQuery } from "@/hooks/useDashboard";
import { getApiErrorMessage } from "@/lib/api/errors";

function DashboardSourcesSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6 sm:px-8 lg:px-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
        <div className="w-full max-w-2xl">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="mt-3 h-9 w-80 max-w-full" />
          <Skeleton className="mt-3 h-4 w-full" />
          <Skeleton className="mt-2 h-4 w-3/4" />
        </div>
        <Skeleton className="h-7 w-36" />
      </header>

      <section
        className="grid gap-4 md:grid-cols-4"
        aria-label="Loading source connection summary"
      >
        {["connected", "active", "sync", "health"].map((item) => (
          <div
            key={item}
            className="rounded-lg border border-border bg-card p-5 shadow-sm"
          >
            <div className="flex items-center justify-between gap-3">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="size-5" />
            </div>
            <Skeleton className="mt-5 h-8 w-28" />
            <Skeleton className="mt-3 h-4 w-36 max-w-full" />
          </div>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </section>
    </div>
  );
}

export function DashboardSourcesClient() {
  const overviewQuery = useDashboardOverviewQuery();

  if (overviewQuery.isPending) {
    return <DashboardSourcesSkeleton />;
  }

  if (overviewQuery.isError) {
    return (
      <div className="mx-auto w-full max-w-7xl px-6 py-6 sm:px-8 lg:px-10">
        <ErrorState
          title="Source status failed to load"
          description={getApiErrorMessage(overviewQuery.error)}
          actionLabel="Try again"
          onAction={() => void overviewQuery.refetch()}
        />
      </div>
    );
  }

  return <DashboardSources overview={overviewQuery.data} />;
}

import { Activity, Bed, Brain, HeartPulse, RefreshCw } from "lucide-react";

import { EmptyState } from "@/components/states";
import { Badge } from "@/components/ui/badge";

const metrics = [
  {
    label: "Training load",
    value: "Awaiting sync",
    detail: "No activity data connected",
    icon: Activity,
  },
  {
    label: "Recovery",
    value: "Pending",
    detail: "Sleep and HRV required",
    icon: HeartPulse,
  },
  {
    label: "Sleep",
    value: "Pending",
    detail: "Latest session not imported",
    icon: Bed,
  },
];

export default function DashboardPage() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6 sm:px-8 lg:px-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
        <div>
          <Badge variant="secondary">Dashboard</Badge>
          <h1 className="mt-3 text-3xl font-semibold tracking-normal">
            Coaching overview
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Garmin metrics, recovery context, and AI recommendations will land
            here as the ingestion and coaching phases come online.
          </p>
        </div>
        <button
          type="button"
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-border px-4 text-sm font-medium transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <RefreshCw className="size-4" aria-hidden="true" />
          Sync
        </button>
      </header>

      <section
        id="metrics"
        className="grid gap-4 md:grid-cols-3"
        aria-label="Training metrics"
      >
        {metrics.map((metric) => {
          const Icon = metric.icon;

          return (
            <article
              key={metric.label}
              className="rounded-lg border border-border bg-card p-5 shadow-sm"
            >
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-medium text-muted-foreground">
                  {metric.label}
                </h2>
                <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
              </div>
              <p className="mt-5 text-2xl font-semibold">{metric.value}</p>
              <p className="mt-2 text-sm text-muted-foreground">{metric.detail}</p>
            </article>
          );
        })}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <article
          id="coach"
          className="rounded-lg border border-border bg-card p-5 shadow-sm"
        >
          <div className="flex items-center gap-3">
            <Brain className="size-5 text-muted-foreground" aria-hidden="true" />
            <h2 className="text-base font-semibold">Coach recommendation</h2>
          </div>
          <EmptyState
            className="mt-4 min-h-48"
            icon={Brain}
            title="No coach insight yet"
            description="Connect Garmin and complete the first sync to generate structured training guidance from recent activities, sleep, and recovery data."
          />
        </article>

        <article
          id="sync"
          className="rounded-lg border border-border bg-card p-5 shadow-sm"
        >
          <h2 className="text-base font-semibold">Sync status</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex items-center justify-between gap-4">
              <dt className="text-muted-foreground">Garmin connection</dt>
              <dd className="font-medium">Not connected</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-muted-foreground">Last sync</dt>
              <dd className="font-medium">Never</dd>
            </div>
            <div className="flex items-center justify-between gap-4">
              <dt className="text-muted-foreground">Insight job</dt>
              <dd className="font-medium">Waiting</dd>
            </div>
          </dl>
        </article>
      </section>
    </div>
  );
}

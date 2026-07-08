import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  DatabaseZap,
  Plug,
  RefreshCw,
  ShieldCheck,
  ShieldQuestion,
} from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardOverviewResponse } from "@/lib/api/dashboard";
import { cn } from "@/lib/utils";

type DashboardSourcesProps = {
  overview: DashboardOverviewResponse;
};

type SourceMetricCardProps = {
  label: string;
  value: string;
  detail: string;
  icon: typeof Plug;
};

const dateTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

function formatDateTime(value: string | null) {
  if (!value) {
    return "Never";
  }

  return dateTimeFormatter.format(new Date(value));
}

function formatStatus(value: string | null) {
  if (!value) {
    return "Not synced";
  }

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function statusVariant(status: string | null) {
  if (status === "succeeded") {
    return "secondary" as const;
  }

  if (status === "failed") {
    return "destructive" as const;
  }

  return "outline" as const;
}

function connectionHealth(sync: DashboardOverviewResponse["sync"]) {
  if (sync.connected_sources === 0) {
    return {
      label: "Not connected",
      detail: "Connect Garmin to start importing training and recovery data.",
      icon: ShieldQuestion,
    };
  }

  if (sync.active_sources === 0) {
    return {
      label: "Needs attention",
      detail: "All connected sources are inactive or need reconnection.",
      icon: AlertTriangle,
    };
  }

  if (sync.latest_sync_status === "failed") {
    return {
      label: "Sync issue",
      detail:
        "The latest sync failed. Review the error code before relying on new data.",
      icon: AlertTriangle,
    };
  }

  return {
    label: "Ready",
    detail: "At least one data source is active for dashboard updates.",
    icon: ShieldCheck,
  };
}

function SourceMetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: SourceMetricCardProps) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3 space-y-0">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        <Icon className="size-5 text-muted-foreground" aria-hidden="true" />
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold">{value}</p>
        <p className="mt-2 text-sm leading-5 text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}

function DetailRow({
  label,
  value,
  icon: Icon,
}: Readonly<{
  label: string;
  value: string;
  icon: typeof Plug;
}>) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-2">
      <dt className="flex items-center gap-2 text-sm text-muted-foreground">
        <Icon className="size-4" aria-hidden="true" />
        {label}
      </dt>
      <dd className="text-right text-sm font-medium">{value}</dd>
    </div>
  );
}

export function DashboardSources({ overview }: DashboardSourcesProps) {
  const { sync } = overview;
  const health = connectionHealth(sync);
  const HealthIcon = health.icon;
  const inactiveSources = Math.max(
    sync.connected_sources - sync.active_sources,
    0,
  );

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6 sm:px-8 lg:px-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
        <div>
          <Badge variant="secondary">Sources</Badge>
          <h1 className="mt-3 text-3xl font-semibold tracking-normal">
            Data source status
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Connection coverage and latest sync health for the data feeding
            training, recovery, sleep, and coaching views.
          </p>
        </div>
        <Link
          href="/dashboard"
          className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
        >
          Overview
        </Link>
      </header>

      <section
        className="grid gap-4 md:grid-cols-4"
        aria-label="Source connection summary"
      >
        <SourceMetricCard
          label="Connected"
          value={sync.connected_sources.toLocaleString("en-GB")}
          detail="Sources with saved connection records"
          icon={Plug}
        />
        <SourceMetricCard
          label="Active"
          value={sync.active_sources.toLocaleString("en-GB")}
          detail={
            inactiveSources
              ? `${inactiveSources} source${inactiveSources === 1 ? "" : "s"} inactive`
              : "All connected sources are active"
          }
          icon={CheckCircle2}
        />
        <SourceMetricCard
          label="Latest sync"
          value={formatStatus(sync.latest_sync_status)}
          detail={formatDateTime(sync.latest_sync_completed_at)}
          icon={RefreshCw}
        />
        <SourceMetricCard
          label="Health"
          value={health.label}
          detail={health.detail}
          icon={HealthIcon}
        />
      </section>

      {sync.connected_sources === 0 ? (
        <EmptyState
          className="min-h-96"
          icon={DatabaseZap}
          title="No data sources connected"
          description="Connect Garmin to start syncing activity, sleep, recovery, and biometric records."
        />
      ) : (
        <section className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr]">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <CardTitle>Sync status</CardTitle>
                <Badge variant={statusVariant(sync.latest_sync_status)}>
                  {formatStatus(sync.latest_sync_status)}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3">
                <DetailRow
                  icon={Clock3}
                  label="Last completed"
                  value={formatDateTime(sync.latest_sync_completed_at)}
                />
                <DetailRow
                  icon={CheckCircle2}
                  label="Active sources"
                  value={`${sync.active_sources}/${sync.connected_sources}`}
                />
                <DetailRow
                  icon={AlertTriangle}
                  label="Latest issue"
                  value={sync.latest_sync_error_code ?? "No issue recorded"}
                />
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center gap-3 space-y-0">
              <DatabaseZap
                className="size-5 text-muted-foreground"
                aria-hidden="true"
              />
              <CardTitle>Dashboard data coverage</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border border-border px-3 py-2">
                  <p className="text-sm text-muted-foreground">Activities</p>
                  <p className="mt-1 text-sm font-medium">
                    {overview.activity.activity_count_7d.toLocaleString(
                      "en-GB",
                    )}{" "}
                    in the last 7 days
                  </p>
                </div>
                <div className="rounded-md border border-border px-3 py-2">
                  <p className="text-sm text-muted-foreground">Recovery</p>
                  <p className="mt-1 text-sm font-medium">
                    {overview.recovery.metric_date
                      ? `Latest ${overview.recovery.metric_date}`
                      : "No daily metric"}
                  </p>
                </div>
                <div className="rounded-md border border-border px-3 py-2">
                  <p className="text-sm text-muted-foreground">Sleep</p>
                  <p className="mt-1 text-sm font-medium">
                    {overview.sleep.sleep_date
                      ? `Latest ${overview.sleep.sleep_date}`
                      : "No sleep session"}
                  </p>
                </div>
                <div className="rounded-md border border-border px-3 py-2">
                  <p className="text-sm text-muted-foreground">Coach</p>
                  <p className="mt-1 text-sm font-medium">
                    {overview.latest_insight
                      ? `Latest ${overview.latest_insight.insight_date}`
                      : "No coach insight"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  );
}

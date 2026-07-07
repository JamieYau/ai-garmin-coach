import {
  Activity,
  Bed,
  Brain,
  CalendarClock,
  CheckCircle2,
  Clock3,
  Footprints,
  HeartPulse,
  RefreshCw,
  Route,
  ShieldAlert,
  Zap,
} from "lucide-react";

import { EmptyState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DashboardOverviewResponse } from "@/lib/api/dashboard";

type DashboardOverviewProps = {
  overview: DashboardOverviewResponse;
};

type MetricCardProps = {
  label: string;
  value: string;
  detail: string;
  icon: typeof Activity;
};

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

function formatDate(value: string | null) {
  if (!value) {
    return "No recent data";
  }

  return dateFormatter.format(new Date(`${value}T00:00:00Z`));
}

function formatDateTime(value: string | null) {
  if (!value) {
    return "Never";
  }

  return dateTimeFormatter.format(new Date(value));
}

function formatDuration(seconds: number | null) {
  if (!seconds) {
    return "0m";
  }

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.round((seconds % 3600) / 60);

  if (hours === 0) {
    return `${minutes}m`;
  }

  return minutes === 0 ? `${hours}h` : `${hours}h ${minutes}m`;
}

function formatDistance(meters: string | null) {
  if (!meters) {
    return "0 km";
  }

  const kilometers = Number.parseFloat(meters) / 1000;
  return `${kilometers.toFixed(kilometers >= 10 ? 0 : 1)} km`;
}

function formatDecimal(value: string | null, suffix = "") {
  if (!value) {
    return "No data";
  }

  const parsed = Number.parseFloat(value);
  return `${parsed.toFixed(parsed % 1 === 0 ? 0 : 1)}${suffix}`;
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

function statusLabel(status: string | null) {
  if (!status) {
    return "Not synced";
  }

  return status.replaceAll("_", " ");
}

function MetricCard({ label, value, detail, icon: Icon }: MetricCardProps) {
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
        <p className="mt-2 text-sm leading-5 text-muted-foreground">
          {detail}
        </p>
      </CardContent>
    </Card>
  );
}

function DetailRow({
  icon: Icon,
  label,
  value,
}: Readonly<{
  icon: typeof Activity;
  label: string;
  value: string;
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

export function DashboardOverview({ overview }: DashboardOverviewProps) {
  const { activity, recovery, sleep, latest_insight: insight, sync } = overview;
  const activityDistance = formatDistance(activity.distance_meters_7d);
  const activityDuration = formatDuration(activity.duration_seconds_7d);
  const sleepDuration = formatDuration(sleep.total_sleep_seconds);
  const sleepScore = sleep.sleep_score ? `${sleep.sleep_score}/100` : "No score";
  const bodyBattery =
    recovery.body_battery_latest === null
      ? "No data"
      : `${recovery.body_battery_latest}/100`;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6 sm:px-8 lg:px-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
        <div>
          <Badge variant="secondary">Dashboard</Badge>
          <h1 className="mt-3 text-3xl font-semibold tracking-normal">
            Coaching overview
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Recent training load, recovery signals, sleep quality, and the
            latest AI coach recommendation from your Garmin data.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <RefreshCw className="size-4" aria-hidden="true" />
          Last sync {formatDateTime(sync.latest_sync_completed_at)}
        </div>
      </header>

      <section
        id="metrics"
        className="grid gap-4 md:grid-cols-3"
        aria-label="Training metrics"
      >
        <MetricCard
          label="7-day training"
          value={activityDuration}
          detail={`${activity.activity_count_7d} activities, ${activityDistance} since ${formatDate(activity.latest_activity_date)}`}
          icon={Activity}
        />
        <MetricCard
          label="Recovery"
          value={bodyBattery}
          detail={`HRV ${formatDecimal(recovery.hrv_ms, " ms")} and resting HR ${recovery.resting_heart_rate ?? "no data"}`}
          icon={HeartPulse}
        />
        <MetricCard
          label="Sleep"
          value={sleepDuration}
          detail={`${sleepScore} sleep score from ${formatDate(sleep.sleep_date)}`}
          icon={Bed}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card id="coach">
          <CardHeader className="flex-row items-center gap-3 space-y-0">
            <Brain className="size-5 text-muted-foreground" aria-hidden="true" />
            <CardTitle>Coach recommendation</CardTitle>
          </CardHeader>
          <CardContent>
            {insight ? (
              <div className="space-y-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-xl font-semibold">{insight.title}</h2>
                    <Badge variant="outline">{insight.insight_type}</Badge>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {insight.summary}
                  </p>
                </div>
                {insight.recommendation ? (
                  <div className="rounded-md border border-border bg-muted/40 p-4">
                    <p className="text-sm font-medium">Recommended next step</p>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {insight.recommendation}
                    </p>
                  </div>
                ) : null}
                <p className="text-xs text-muted-foreground">
                  Generated {formatDateTime(insight.generated_at)}
                </p>
              </div>
            ) : (
              <EmptyState
                className="min-h-48"
                icon={Brain}
                title="No coach insight yet"
                description="Complete a Garmin sync and daily insight run to see structured training guidance here."
              />
            )}
          </CardContent>
        </Card>

        <Card id="sync">
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>Training context</CardTitle>
              <Badge variant={statusVariant(sync.latest_sync_status)}>
                {statusLabel(sync.latest_sync_status)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3">
              <DetailRow
                icon={Route}
                label="Distance"
                value={activityDistance}
              />
              <DetailRow
                icon={Footprints}
                label="Steps"
                value={recovery.steps?.toLocaleString("en-GB") ?? "No data"}
              />
              <DetailRow
                icon={Zap}
                label="Stress"
                value={formatDecimal(recovery.stress_average)}
              />
              <DetailRow
                icon={Clock3}
                label="Active time"
                value={formatDuration(recovery.active_seconds)}
              />
              <DetailRow
                icon={CalendarClock}
                label="Sleep HRV"
                value={formatDecimal(sleep.average_hrv_ms, " ms")}
              />
              <DetailRow
                icon={CheckCircle2}
                label="Sources"
                value={`${sync.active_sources}/${sync.connected_sources} active`}
              />
              {sync.latest_sync_error_code ? (
                <DetailRow
                  icon={ShieldAlert}
                  label="Sync issue"
                  value={sync.latest_sync_error_code}
                />
              ) : null}
            </dl>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

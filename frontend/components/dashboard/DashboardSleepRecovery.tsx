import {
  Activity,
  BatteryCharging,
  Bed,
  CalendarClock,
  HeartPulse,
  Moon,
  ShieldCheck,
  Timer,
  Zap,
} from "lucide-react";
import Link from "next/link";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  DashboardRecoveryMetricPoint,
  DashboardRecoveryMetricsResponse,
  DashboardSleepTrendPoint,
  DashboardSleepTrendResponse,
} from "@/lib/api/dashboard";
import { cn } from "@/lib/utils";

type DashboardSleepRecoveryProps = {
  sleep: DashboardSleepTrendResponse;
  recovery: DashboardRecoveryMetricsResponse;
};

type RecoveryMetricCardProps = {
  label: string;
  value: string;
  detail: string;
  icon: typeof Bed;
};

const sleepChartConfig = {
  sleepHours: {
    label: "Sleep",
    color: "var(--chart-1)",
  },
  sleepScore: {
    label: "Score",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig;

const recoveryChartConfig = {
  hrv: {
    label: "HRV",
    color: "var(--chart-3)",
  },
  restingHeartRate: {
    label: "Resting HR",
    color: "var(--chart-4)",
  },
} satisfies ChartConfig;

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

function formatDate(value: string) {
  return dateFormatter.format(new Date(`${value}T00:00:00Z`));
}

function formatDateTime(value: string) {
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

function parseDecimal(value: string | null) {
  return value ? Number.parseFloat(value) : null;
}

function formatDecimal(value: string | null, suffix = "") {
  const parsed = parseDecimal(value);

  if (parsed === null) {
    return "No data";
  }

  return `${parsed.toFixed(parsed % 1 === 0 ? 0 : 1)}${suffix}`;
}

function average(values: number[]) {
  if (values.length === 0) {
    return null;
  }

  return values.reduce((total, value) => total + value, 0) / values.length;
}

function latestValue<T>(values: T[]) {
  return values.length ? values[values.length - 1] : null;
}

function RecoveryMetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: RecoveryMetricCardProps) {
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

function buildSleepChartData(sessions: DashboardSleepTrendPoint[]) {
  return sessions.map((session) => ({
    id: session.id,
    label: formatDate(session.sleep_date),
    sleepHours: Number((session.total_sleep_seconds / 3600).toFixed(1)),
    sleepScore: session.sleep_score,
  }));
}

function buildRecoveryChartData(metrics: DashboardRecoveryMetricPoint[]) {
  return metrics.map((metric) => ({
    label: formatDate(metric.metric_date),
    hrv: parseDecimal(metric.hrv_ms),
    restingHeartRate: metric.resting_heart_rate,
  }));
}

function summarizeSleep(sessions: DashboardSleepTrendPoint[]) {
  const latestSleep = latestValue(sessions);
  const averageSleepSeconds = average(
    sessions.map((session) => session.total_sleep_seconds),
  );
  const sleepScores = sessions
    .map((session) => session.sleep_score)
    .filter((value): value is number => value !== null);

  return {
    latestSleep,
    averageSleepSeconds,
    averageSleepScore: average(sleepScores),
  };
}

function summarizeRecovery(metrics: DashboardRecoveryMetricPoint[]) {
  const latestRecovery = latestValue(metrics);
  const hrvValues = metrics
    .map((metric) => parseDecimal(metric.hrv_ms))
    .filter((value): value is number => value !== null);

  return {
    latestRecovery,
    averageHrv: average(hrvValues),
  };
}

function hasNoSleepRecoveryData(
  sleepSessions: DashboardSleepTrendPoint[],
  metrics: DashboardRecoveryMetricPoint[],
) {
  return sleepSessions.length === 0 && metrics.length === 0;
}

function buildDailyRows(
  sleepSessions: DashboardSleepTrendPoint[],
  metrics: DashboardRecoveryMetricPoint[],
) {
  const sleepByDate = new Map(
    sleepSessions.map((session) => [session.sleep_date, session]),
  );
  const metricByDate = new Map(
    metrics.map((metric) => [metric.metric_date, metric]),
  );
  const dates = new Set([...sleepByDate.keys(), ...metricByDate.keys()]);

  return [...dates]
    .sort((left, right) => right.localeCompare(left))
    .map((date) => ({
      date,
      sleep: sleepByDate.get(date) ?? null,
      metric: metricByDate.get(date) ?? null,
    }));
}

export function DashboardSleepRecovery({
  sleep,
  recovery,
}: DashboardSleepRecoveryProps) {
  const sleepSessions = sleep.sleep_sessions;
  const recoveryMetrics = recovery.metrics;
  const sleepSummary = summarizeSleep(sleepSessions);
  const recoverySummary = summarizeRecovery(recoveryMetrics);
  const latestSleep = sleepSummary.latestSleep;
  const latestRecovery = recoverySummary.latestRecovery;
  const sleepChartData = buildSleepChartData(sleepSessions);
  const recoveryChartData = buildRecoveryChartData(recoveryMetrics);
  const dailyRows = buildDailyRows(sleepSessions, recoveryMetrics);

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-4 sm:gap-6 sm:px-8 sm:py-6 lg:px-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
        <div className="min-w-0">
          <Badge variant="secondary">Recovery</Badge>
          <h1 className="mt-3 text-3xl font-semibold tracking-normal">
            Sleep and recovery
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Recent Garmin sleep quality, HRV, resting heart rate, body battery,
            stress, and daily activity context.
          </p>
        </div>
        <Link
          href="/dashboard"
          className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
        >
          Overview
        </Link>
      </header>

      {hasNoSleepRecoveryData(sleepSessions, recoveryMetrics) ? (
        <EmptyState
          className="min-h-96"
          icon={Bed}
          title="No sleep or recovery data yet"
          description="Complete a Garmin sync to see sleep sessions, HRV, body battery, and daily recovery metrics here."
        />
      ) : (
        <>
          <section
            className="grid gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4"
            aria-label="Sleep and recovery totals"
          >
            <RecoveryMetricCard
              label="Latest sleep"
              value={
                latestSleep
                  ? formatDuration(latestSleep.total_sleep_seconds)
                  : "No data"
              }
              detail={
                latestSleep
                  ? `Avg ${formatDuration(sleepSummary.averageSleepSeconds)}`
                  : "No sleep sessions"
              }
              icon={Bed}
            />
            <RecoveryMetricCard
              label="Avg sleep score"
              value={
                sleepSummary.averageSleepScore === null
                  ? "No score"
                  : `${Math.round(sleepSummary.averageSleepScore)}/100`
              }
              detail={`${sleepSessions.length} sessions over ${sleep.days} days`}
              icon={Moon}
            />
            <RecoveryMetricCard
              label="Avg HRV"
              value={
                recoverySummary.averageHrv === null
                  ? "No data"
                  : `${recoverySummary.averageHrv.toFixed(1)} ms`
              }
              detail={
                latestRecovery
                  ? `Latest ${formatDecimal(latestRecovery.hrv_ms, " ms")}`
                  : "No recovery metrics"
              }
              icon={HeartPulse}
            />
            <RecoveryMetricCard
              label="Body battery"
              value={
                latestRecovery?.body_battery_latest === null ||
                latestRecovery?.body_battery_latest === undefined
                  ? "No data"
                  : `${latestRecovery.body_battery_latest}/100`
              }
              detail={
                latestRecovery
                  ? `Updated ${formatDate(latestRecovery.metric_date)}`
                  : "No daily metric"
              }
              icon={BatteryCharging}
            />
          </section>

          <section className="grid min-w-0 gap-3 sm:gap-4 lg:grid-cols-2">
            <Card className="min-w-0">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <Timer
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>Sleep trend</CardTitle>
              </CardHeader>
              <CardContent>
                {sleepChartData.length ? (
                  <ChartContainer
                    config={sleepChartConfig}
                    className="h-72 w-full"
                  >
                    <LineChart
                      accessibilityLayer
                      data={sleepChartData}
                      margin={{ left: 0, right: 12, top: 8, bottom: 8 }}
                    >
                      <CartesianGrid vertical={false} />
                      <XAxis
                        dataKey="label"
                        tickLine={false}
                        axisLine={false}
                        tickMargin={8}
                      />
                      <YAxis
                        width={34}
                        tickLine={false}
                        axisLine={false}
                        tickMargin={8}
                      />
                      <ChartTooltip
                        cursor={false}
                        content={<ChartTooltipContent />}
                      />
                      <Line
                        type="monotone"
                        dataKey="sleepHours"
                        stroke="var(--color-sleepHours)"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="sleepScore"
                        stroke="var(--color-sleepScore)"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ChartContainer>
                ) : (
                  <EmptyState
                    className="min-h-72"
                    icon={Bed}
                    title="No sleep sessions"
                    description="Sleep trend data will appear after Garmin sync stores sleep sessions."
                  />
                )}
              </CardContent>
            </Card>

            <Card className="min-w-0">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <ShieldCheck
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>Recovery trend</CardTitle>
              </CardHeader>
              <CardContent>
                {recoveryChartData.length ? (
                  <ChartContainer
                    config={recoveryChartConfig}
                    className="h-72 w-full"
                  >
                    <LineChart
                      accessibilityLayer
                      data={recoveryChartData}
                      margin={{ left: 0, right: 12, top: 8, bottom: 8 }}
                    >
                      <CartesianGrid vertical={false} />
                      <XAxis
                        dataKey="label"
                        tickLine={false}
                        axisLine={false}
                        tickMargin={8}
                      />
                      <YAxis
                        width={34}
                        tickLine={false}
                        axisLine={false}
                        tickMargin={8}
                      />
                      <ChartTooltip
                        cursor={false}
                        content={<ChartTooltipContent />}
                      />
                      <Line
                        type="monotone"
                        dataKey="hrv"
                        stroke="var(--color-hrv)"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="restingHeartRate"
                        stroke="var(--color-restingHeartRate)"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ChartContainer>
                ) : (
                  <EmptyState
                    className="min-h-72"
                    icon={HeartPulse}
                    title="No recovery metrics"
                    description="Daily HRV, resting heart rate, and body battery data will appear after sync."
                  />
                )}
              </CardContent>
            </Card>
          </section>

          <Card className="min-w-0">
            <CardHeader className="flex-row items-center gap-3 space-y-0">
              <CalendarClock
                className="size-5 text-muted-foreground"
                aria-hidden="true"
              />
              <CardTitle>Daily recovery log</CardTitle>
            </CardHeader>
            <CardContent>
              <Table
                className="min-w-[760px]"
                scrollHint="Swipe horizontally to view all recovery details."
              >
                <TableHeader>
                  <TableRow className="text-xs font-medium text-muted-foreground hover:bg-transparent">
                    <TableHead className="px-0">Date</TableHead>
                    <TableHead className="text-right">Sleep</TableHead>
                    <TableHead className="text-right">Score</TableHead>
                    <TableHead className="text-right">HRV</TableHead>
                    <TableHead className="text-right">Resting HR</TableHead>
                    <TableHead className="text-right">Stress</TableHead>
                    <TableHead className="px-0 text-right">Steps</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dailyRows.map(({ date, sleep: session, metric }) => {
                    return (
                      <TableRow key={date}>
                        <TableCell className="px-0 py-4">
                          <div className="flex flex-col gap-1">
                            <span className="font-medium">
                              {formatDate(date)}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {session
                                ? `${formatDateTime(session.started_at)} to ${formatDateTime(session.ended_at)}`
                                : "No sleep session"}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="py-4 text-right font-medium">
                          {session
                            ? formatDuration(session.total_sleep_seconds)
                            : "No data"}
                        </TableCell>
                        <TableCell className="py-4 text-right">
                          {session?.sleep_score === null ||
                          session?.sleep_score === undefined
                            ? "No score"
                            : `${session.sleep_score}/100`}
                        </TableCell>
                        <TableCell className="py-4 text-right">
                          {formatDecimal(
                            session?.average_hrv_ms ?? metric?.hrv_ms ?? null,
                            " ms",
                          )}
                        </TableCell>
                        <TableCell className="py-4 text-right">
                          {metric?.resting_heart_rate
                            ? `${metric.resting_heart_rate} bpm`
                            : "No data"}
                        </TableCell>
                        <TableCell className="py-4 text-right">
                          {formatDecimal(metric?.stress_average ?? null)}
                        </TableCell>
                        <TableCell className="px-0 py-4 text-right">
                          <div className="inline-flex items-center justify-end gap-1.5">
                            <Activity
                              className="size-3.5 text-muted-foreground"
                              aria-hidden="true"
                            />
                            {metric?.steps?.toLocaleString("en-GB") ??
                              "No data"}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {latestRecovery ? (
            <Card>
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <Zap
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>Latest daily context</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-md border border-border px-3 py-2">
                    <p className="text-sm text-muted-foreground">Active time</p>
                    <p className="mt-1 text-sm font-medium">
                      {formatDuration(latestRecovery.active_seconds)}
                    </p>
                  </div>
                  <div className="rounded-md border border-border px-3 py-2">
                    <p className="text-sm text-muted-foreground">
                      Highly active
                    </p>
                    <p className="mt-1 text-sm font-medium">
                      {formatDuration(latestRecovery.highly_active_seconds)}
                    </p>
                  </div>
                  <div className="rounded-md border border-border px-3 py-2">
                    <p className="text-sm text-muted-foreground">
                      Body battery range
                    </p>
                    <p className="mt-1 text-sm font-medium">
                      {latestRecovery.body_battery_min === null ||
                      latestRecovery.body_battery_max === null
                        ? "No data"
                        : `${latestRecovery.body_battery_min}-${latestRecovery.body_battery_max}`}
                    </p>
                  </div>
                  <div className="rounded-md border border-border px-3 py-2">
                    <p className="text-sm text-muted-foreground">
                      Resting heart rate
                    </p>
                    <p className="mt-1 text-sm font-medium">
                      {latestRecovery.resting_heart_rate
                        ? `${latestRecovery.resting_heart_rate} bpm`
                        : "No data"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : null}
        </>
      )}
    </div>
  );
}

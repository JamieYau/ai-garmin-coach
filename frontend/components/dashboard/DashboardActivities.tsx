import {
  Activity,
  BarChart3,
  CalendarClock,
  Flame,
  Gauge,
  HeartPulse,
  Route,
  Timer,
} from "lucide-react";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { DashboardActivityDetail } from "@/lib/api/dashboard";

type DashboardActivitiesProps = {
  activities: DashboardActivityDetail[];
};

type ActivityMetricCardProps = {
  label: string;
  value: string;
  detail: string;
  icon: typeof Activity;
};

const activityChartConfig = {
  distance: {
    label: "Distance",
    color: "var(--chart-1)",
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

function formatActivityType(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

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

function formatDistance(meters: string | null) {
  const parsed = parseDecimal(meters);

  if (!parsed) {
    return "0 km";
  }

  const kilometers = parsed / 1000;
  return `${kilometers.toFixed(kilometers >= 10 ? 0 : 1)} km`;
}

function formatTrainingLoad(value: string | null) {
  const parsed = parseDecimal(value);
  return parsed ? parsed.toFixed(0) : "No data";
}

function formatPace(activity: DashboardActivityDetail) {
  const distanceMeters = parseDecimal(activity.distance_meters);
  const durationSeconds =
    activity.moving_duration_seconds ?? activity.duration_seconds;

  if (!distanceMeters || !durationSeconds) {
    return "No pace";
  }

  const secondsPerKilometer = durationSeconds / (distanceMeters / 1000);
  const minutes = Math.floor(secondsPerKilometer / 60);
  const seconds = Math.round(secondsPerKilometer % 60)
    .toString()
    .padStart(2, "0");

  return `${minutes}:${seconds}/km`;
}

function ActivityMetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: ActivityMetricCardProps) {
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

function summarizeActivities(activities: DashboardActivityDetail[]) {
  const totalDurationSeconds = activities.reduce(
    (total, activity) => total + activity.duration_seconds,
    0,
  );
  const totalDistanceMeters = activities.reduce(
    (total, activity) => total + (parseDecimal(activity.distance_meters) ?? 0),
    0,
  );
  const totalTrainingLoad = activities.reduce(
    (total, activity) => total + (parseDecimal(activity.training_load) ?? 0),
    0,
  );
  const heartRates = activities
    .map((activity) => activity.average_heart_rate)
    .filter((value): value is number => value !== null);
  const averageHeartRate = heartRates.length
    ? Math.round(
        heartRates.reduce((total, value) => total + value, 0) /
          heartRates.length,
      )
    : null;

  return {
    totalDurationSeconds,
    totalDistanceMeters,
    totalTrainingLoad,
    averageHeartRate,
  };
}

function buildTypeBreakdown(activities: DashboardActivityDetail[]) {
  const grouped = new Map<string, { count: number; durationSeconds: number }>();

  for (const activity of activities) {
    const label = formatActivityType(activity.activity_type);
    const current = grouped.get(label) ?? { count: 0, durationSeconds: 0 };
    grouped.set(label, {
      count: current.count + 1,
      durationSeconds: current.durationSeconds + activity.duration_seconds,
    });
  }

  return [...grouped.entries()]
    .map(([label, value]) => ({ label, ...value }))
    .sort((a, b) => b.durationSeconds - a.durationSeconds);
}

function buildChartData(activities: DashboardActivityDetail[]) {
  return activities
    .slice(0, 10)
    .reverse()
    .map((activity) => ({
      id: activity.id,
      label: formatDate(activity.activity_date),
      name: activity.name ?? formatActivityType(activity.activity_type),
      distance: Number(
        ((parseDecimal(activity.distance_meters) ?? 0) / 1000).toFixed(2),
      ),
    }));
}

export function DashboardActivities({ activities }: DashboardActivitiesProps) {
  const summary = summarizeActivities(activities);
  const typeBreakdown = buildTypeBreakdown(activities);
  const chartData = buildChartData(activities);
  const latestActivity = activities[0];

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6 sm:px-8 lg:px-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
        <div>
          <Badge variant="secondary">Activities</Badge>
          <h1 className="mt-3 text-3xl font-semibold tracking-normal">
            Training activity
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Recent Garmin activities summarized by duration, distance, training
            load, heart rate, and activity type.
          </p>
        </div>
        <Button variant="outline" size="sm" render={<Link href="/dashboard" />}>
          Overview
        </Button>
      </header>

      {activities.length === 0 ? (
        <EmptyState
          className="min-h-96"
          icon={Activity}
          title="No activities yet"
          description="Complete a Garmin sync to see recent training activities here."
        />
      ) : (
        <>
          <section
            className="grid gap-4 md:grid-cols-4"
            aria-label="Activity totals"
          >
            <ActivityMetricCard
              label="Activities"
              value={activities.length.toLocaleString("en-GB")}
              detail={
                summary.totalTrainingLoad
                  ? `${summary.totalTrainingLoad.toFixed(0)} total load`
                  : latestActivity
                    ? `Latest ${formatDate(latestActivity.activity_date)}`
                    : "No recent activity"
              }
              icon={Activity}
            />
            <ActivityMetricCard
              label="Duration"
              value={formatDuration(summary.totalDurationSeconds)}
              detail="Across recent activities"
              icon={Timer}
            />
            <ActivityMetricCard
              label="Distance"
              value={formatDistance(summary.totalDistanceMeters.toFixed(2))}
              detail="Recorded moving distance"
              icon={Route}
            />
            <ActivityMetricCard
              label="Avg heart rate"
              value={
                summary.averageHeartRate
                  ? `${summary.averageHeartRate} bpm`
                  : "No data"
              }
              detail="Activities with HR data"
              icon={HeartPulse}
            />
          </section>

          <section className="grid gap-4 lg:grid-cols-[1.35fr_0.65fr]">
            <Card>
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <BarChart3
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>Recent distance</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartContainer
                  config={activityChartConfig}
                  className="h-72 w-full"
                >
                  <BarChart
                    accessibilityLayer
                    data={chartData}
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
                      unit=" km"
                    />
                    <ChartTooltip
                      cursor={false}
                      content={<ChartTooltipContent hideLabel />}
                    />
                    <Bar dataKey="distance" radius={[4, 4, 0, 0]}>
                      {chartData.map((item) => (
                        <Cell key={item.id} fill="var(--color-distance)" />
                      ))}
                    </Bar>
                  </BarChart>
                </ChartContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <Gauge
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>Activity mix</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {typeBreakdown.map((item) => (
                    <div
                      key={item.label}
                      className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-medium">{item.label}</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {item.count}{" "}
                          {item.count === 1 ? "activity" : "activities"}
                        </p>
                      </div>
                      <p className="text-right text-sm font-medium">
                        {formatDuration(item.durationSeconds)}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </section>

          <Card>
            <CardHeader className="flex-row items-center gap-3 space-y-0">
              <CalendarClock
                className="size-5 text-muted-foreground"
                aria-hidden="true"
              />
              <CardTitle>Recent activities</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                      <th className="py-3 pr-4">Activity</th>
                      <th className="px-4 py-3">When</th>
                      <th className="px-4 py-3 text-right">Duration</th>
                      <th className="px-4 py-3 text-right">Distance</th>
                      <th className="px-4 py-3 text-right">Pace</th>
                      <th className="px-4 py-3 text-right">Avg HR</th>
                      <th className="py-3 pl-4 text-right">Load</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activities.map((activity) => (
                      <tr
                        key={activity.id}
                        className="border-b border-border/70 last:border-0"
                      >
                        <td className="py-4 pr-4">
                          <div className="flex flex-col gap-1">
                            <span className="font-medium">
                              {activity.name ??
                                formatActivityType(activity.activity_type)}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {formatActivityType(activity.activity_type)}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-muted-foreground">
                          {formatDateTime(activity.started_at)}
                        </td>
                        <td className="px-4 py-4 text-right font-medium">
                          {formatDuration(activity.duration_seconds)}
                        </td>
                        <td className="px-4 py-4 text-right">
                          {formatDistance(activity.distance_meters)}
                        </td>
                        <td className="px-4 py-4 text-right">
                          {formatPace(activity)}
                        </td>
                        <td className="px-4 py-4 text-right">
                          {activity.average_heart_rate
                            ? `${activity.average_heart_rate} bpm`
                            : "No data"}
                        </td>
                        <td className="py-4 pl-4 text-right">
                          <div className="inline-flex items-center justify-end gap-1.5">
                            <Flame
                              className="size-3.5 text-muted-foreground"
                              aria-hidden="true"
                            />
                            {formatTrainingLoad(activity.training_load)}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

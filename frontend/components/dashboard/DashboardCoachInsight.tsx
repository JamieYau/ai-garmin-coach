import {
  AlertTriangle,
  Brain,
  CalendarClock,
  CheckCircle2,
  FileJson,
  Gauge,
  Lightbulb,
  ListChecks,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardInsightDetail } from "@/lib/api/dashboard";
import { cn } from "@/lib/utils";

type DashboardCoachInsightProps = {
  insight: DashboardInsightDetail | null;
};

type CoachMetricCardProps = {
  label: string;
  value: string;
  detail: string;
  icon: typeof Brain;
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

function formatDate(value: string) {
  return dateFormatter.format(new Date(`${value}T00:00:00Z`));
}

function formatDateTime(value: string) {
  return dateTimeFormatter.format(new Date(value));
}

function formatInsightType(value: string) {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function outputString(
  output: Record<string, unknown>,
  keys: string[],
): string | null {
  for (const key of keys) {
    const value = output[key];

    if (typeof value === "string" && value.trim().length > 0) {
      return value;
    }

    if (typeof value === "number" && Number.isFinite(value)) {
      return String(value);
    }
  }

  return null;
}

function outputStringList(
  output: Record<string, unknown>,
  keys: string[],
): string[] {
  for (const key of keys) {
    const value = output[key];

    if (Array.isArray(value)) {
      return value
        .filter((item): item is string => typeof item === "string")
        .filter((item) => item.trim().length > 0);
    }
  }

  return [];
}

function outputRecord(
  output: Record<string, unknown>,
  keys: string[],
): Record<string, unknown> | null {
  for (const key of keys) {
    const value = output[key];

    if (
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      Object.keys(value).length > 0
    ) {
      return value as Record<string, unknown>;
    }
  }

  return null;
}

function formatOutputValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "No data";
  }

  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString("en-GB")
      : value.toFixed(1);
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (Array.isArray(value)) {
    return value.map(formatOutputValue).join(", ");
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function CoachMetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: CoachMetricCardProps) {
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

export function DashboardCoachInsight({ insight }: DashboardCoachInsightProps) {
  const readiness = insight
    ? outputString(insight.output, ["readiness", "readiness_level"])
    : null;
  const confidence = insight
    ? outputString(insight.output, ["confidence", "confidence_score"])
    : null;
  const riskFlags = insight
    ? outputStringList(insight.output, ["risk_flags", "risks", "warnings"])
    : [];
  const actionItems = insight
    ? outputStringList(insight.output, [
        "actions",
        "next_actions",
        "recommendations",
      ])
    : [];
  const supportingMetrics = insight
    ? outputRecord(insight.output, ["supporting_metrics", "metrics"])
    : null;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-4 sm:gap-6 sm:px-8 sm:py-6 lg:px-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
        <div className="min-w-0">
          <Badge variant="secondary">Coach</Badge>
          <h1 className="mt-3 text-3xl font-semibold tracking-normal">
            Coach insight
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            The latest structured AI recommendation with readiness context, risk
            flags, supporting metrics, and generation metadata.
          </p>
        </div>
        <Link
          href="/dashboard"
          className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
        >
          Overview
        </Link>
      </header>

      {insight ? (
        <>
          <section
            className="grid gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-4"
            aria-label="Coach insight summary"
          >
            <CoachMetricCard
              label="Readiness"
              value={readiness ? formatInsightType(readiness) : "No data"}
              detail={`Insight date ${formatDate(insight.insight_date)}`}
              icon={Gauge}
            />
            <CoachMetricCard
              label="Confidence"
              value={confidence ?? "No data"}
              detail={`Schema ${insight.schema_version}`}
              icon={CheckCircle2}
            />
            <CoachMetricCard
              label="Risk flags"
              value={riskFlags.length.toLocaleString("en-GB")}
              detail={
                riskFlags.length
                  ? "Review before planning intensity"
                  : "No flags in latest output"
              }
              icon={AlertTriangle}
            />
            <CoachMetricCard
              label="Generated"
              value={formatDate(insight.insight_date)}
              detail={formatDateTime(insight.generated_at)}
              icon={CalendarClock}
            />
          </section>

          <section className="grid min-w-0 gap-3 sm:gap-4 lg:grid-cols-[1.25fr_0.75fr]">
            <Card className="min-w-0">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <Brain
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>{insight.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline">
                    {formatInsightType(insight.insight_type)}
                  </Badge>
                  {insight.model_name ? (
                    <Badge variant="secondary">{insight.model_name}</Badge>
                  ) : null}
                </div>
                <p className="mt-4 text-sm leading-6 text-muted-foreground">
                  {insight.summary}
                </p>

                {insight.recommendation ? (
                  <div className="mt-5 rounded-md border border-border bg-muted/40 p-4">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <Lightbulb
                        className="size-4 text-muted-foreground"
                        aria-hidden="true"
                      />
                      Recommended next step
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {insight.recommendation}
                    </p>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card className="min-w-0">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <Sparkles
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>Generation details</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-3">
                  <div className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-2">
                    <dt className="text-sm text-muted-foreground">Provider</dt>
                    <dd className="text-right text-sm font-medium">
                      {insight.model_provider ?? "Local"}
                    </dd>
                  </div>
                  <div className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-2">
                    <dt className="text-sm text-muted-foreground">Model</dt>
                    <dd className="text-right text-sm font-medium">
                      {insight.model_name ?? "Not recorded"}
                    </dd>
                  </div>
                  <div className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-2">
                    <dt className="text-sm text-muted-foreground">Prompt</dt>
                    <dd className="text-right text-sm font-medium">
                      {insight.prompt_version ?? "Not recorded"}
                    </dd>
                  </div>
                  <div className="flex items-center justify-between gap-4 rounded-md border border-border px-3 py-2">
                    <dt className="text-sm text-muted-foreground">Schema</dt>
                    <dd className="text-right text-sm font-medium">
                      {insight.schema_version}
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>
          </section>

          <section className="grid min-w-0 gap-3 sm:gap-4 lg:grid-cols-2">
            <Card className="min-w-0">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <ListChecks
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>Action items</CardTitle>
              </CardHeader>
              <CardContent>
                {actionItems.length ? (
                  <ul className="space-y-3">
                    {actionItems.map((item) => (
                      <li
                        key={item}
                        className="rounded-md border border-border px-3 py-2 text-sm leading-6"
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState
                    className="min-h-52"
                    icon={ListChecks}
                    title="No structured actions"
                    description="This insight only includes the main recommendation."
                  />
                )}
              </CardContent>
            </Card>

            <Card className="min-w-0">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <FileJson
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>Supporting metrics</CardTitle>
              </CardHeader>
              <CardContent>
                {supportingMetrics ? (
                  <dl className="grid gap-3 sm:grid-cols-2">
                    {Object.entries(supportingMetrics).map(([key, value]) => (
                      <div
                        key={key}
                        className="rounded-md border border-border px-3 py-2"
                      >
                        <dt className="text-sm text-muted-foreground">
                          {formatInsightType(key)}
                        </dt>
                        <dd className="mt-1 break-words text-sm font-medium">
                          {formatOutputValue(value)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                ) : (
                  <EmptyState
                    className="min-h-52"
                    icon={FileJson}
                    title="No supporting metrics"
                    description="Metric attribution will appear when the coach output includes it."
                  />
                )}
              </CardContent>
            </Card>
          </section>

          {riskFlags.length ? (
            <Card className="min-w-0">
              <CardHeader className="flex-row items-center gap-3 space-y-0">
                <AlertTriangle
                  className="size-5 text-muted-foreground"
                  aria-hidden="true"
                />
                <CardTitle>Risk flags</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {riskFlags.map((flag) => (
                    <Badge key={flag} variant="destructive">
                      {flag}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : null}
        </>
      ) : (
        <EmptyState
          className="min-h-96"
          icon={Brain}
          title="No coach insight yet"
          description="Complete a Garmin sync and daily insight run to see structured training guidance here."
        />
      )}
    </div>
  );
}

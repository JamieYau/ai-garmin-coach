import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  DatabaseZap,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import type { DashboardOverviewResponse } from "@/lib/api/dashboard";
import { cn } from "@/lib/utils";

export type DashboardDataStateKind =
  | "ready"
  | "no-data"
  | "demo-data"
  | "sync-in-progress"
  | "sync-failed"
  | "connected-no-recent-records";

type DashboardDataStateBannerProps = {
  state: DashboardDataStateKind;
  className?: string;
};

type DashboardRecordPresence = {
  hasActivities: boolean;
  hasRecovery: boolean;
  hasSleep: boolean;
  hasInsight: boolean;
};

type DashboardDataStateCopy = {
  title: string;
  description: string;
  badge: string;
  icon: LucideIcon;
  variant?: "default" | "destructive";
};

const stateCopy: Record<DashboardDataStateKind, DashboardDataStateCopy> = {
  ready: {
    title: "Dashboard data is current",
    description: "Recent sync and dashboard records are available.",
    badge: "Ready",
    icon: CheckCircle2,
  },
  "no-data": {
    title: "No data sources connected",
    description:
      "Connect Garmin to start importing activities, sleep, recovery metrics, and coach insights.",
    badge: "No data",
    icon: DatabaseZap,
  },
  "demo-data": {
    title: "Demo data is showing",
    description:
      "This dashboard is populated with local seeded demo records for development and preview workflows.",
    badge: "Demo",
    icon: Sparkles,
  },
  "sync-in-progress": {
    title: "Sync is in progress",
    description:
      "Garmin data is still being imported. Metrics may update as the sync completes.",
    badge: "Syncing",
    icon: RefreshCw,
  },
  "sync-failed": {
    title: "Latest sync failed",
    description:
      "The most recent sync did not complete. Existing data may be stale until the connection is healthy again.",
    badge: "Failed",
    icon: AlertTriangle,
    variant: "destructive",
  },
  "connected-no-recent-records": {
    title: "Connected, but no recent records",
    description:
      "A data source is active, but the dashboard has no recent activity, sleep, recovery, or coach records yet.",
    badge: "No recent records",
    icon: CircleDashed,
  },
};

export function classifyDashboardDataState(
  overview: DashboardOverviewResponse,
): DashboardDataStateKind {
  const presence = getDashboardRecordPresence(overview);

  if (overview.sync.connected_sources === 0) {
    return "no-data";
  }

  if (overview.sync.latest_sync_status === "failed") {
    return "sync-failed";
  }

  if (
    overview.sync.latest_sync_status === "running" ||
    overview.sync.latest_sync_status === "queued"
  ) {
    return "sync-in-progress";
  }

  if (overview.sync.has_demo_data) {
    return "demo-data";
  }

  if (
    overview.sync.active_sources > 0 &&
    !presence.hasActivities &&
    !presence.hasRecovery &&
    !presence.hasSleep &&
    !presence.hasInsight
  ) {
    return "connected-no-recent-records";
  }

  return "ready";
}

export function getDashboardRecordPresence(
  overview: DashboardOverviewResponse,
): DashboardRecordPresence {
  return {
    hasActivities: overview.activity.activity_count_7d > 0,
    hasRecovery: overview.recovery.metric_date !== null,
    hasSleep: overview.sleep.sleep_date !== null,
    hasInsight: overview.latest_insight !== null,
  };
}

export function DashboardDataStateBanner({
  state,
  className,
}: DashboardDataStateBannerProps) {
  if (state === "ready") {
    return null;
  }

  const copy = stateCopy[state];
  const Icon = copy.icon;

  return (
    <Alert
      variant={copy.variant}
      className={cn(
        "items-start gap-2 p-3 sm:gap-3 sm:p-4 has-data-[slot=alert-action]:pr-4",
        className,
      )}
    >
      <Icon
        className={cn("size-5", state === "sync-in-progress" && "animate-spin")}
        aria-hidden="true"
      />
      <div className="flex min-w-0 flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between sm:gap-2">
        <div>
          <AlertTitle>{copy.title}</AlertTitle>
          <AlertDescription>{copy.description}</AlertDescription>
        </div>
        <Badge
          variant={copy.variant === "destructive" ? "destructive" : "secondary"}
          className="w-fit shrink-0"
        >
          {copy.badge}
        </Badge>
      </div>
    </Alert>
  );
}

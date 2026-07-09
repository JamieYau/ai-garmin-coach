import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Unplug,
  X,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardOverviewResponse } from "@/lib/api/dashboard";
import type { ManualSyncResponse } from "@/lib/api/dataControls";

type ActionStatus = "idle" | "pending" | "success" | "error";

export type DashboardSourceControlsProps = {
  sync: DashboardOverviewResponse["sync"];
  manualSyncStatus?: ActionStatus;
  manualSyncResult?: ManualSyncResponse | null;
  manualSyncErrorMessage?: string | null;
  disconnectStatus?: ActionStatus;
  disconnectErrorMessage?: string | null;
  isDisconnectConfirming?: boolean;
  onManualSync: () => void;
  onDisconnectRequest: () => void;
  onDisconnectCancel: () => void;
  onDisconnectConfirm: () => void;
};

function manualSyncMessage(result: ManualSyncResponse | null | undefined) {
  if (!result) {
    return "Manual sync finished. Dashboard data is refreshing.";
  }

  const status = result.status.replaceAll("_", " ");
  return `Manual sync ${status}. Imported ${result.records_imported.toLocaleString(
    "en-GB",
  )} of ${result.records_seen.toLocaleString("en-GB")} records.`;
}

export function DashboardSourceControls({
  sync,
  manualSyncStatus = "idle",
  manualSyncResult,
  manualSyncErrorMessage,
  disconnectStatus = "idle",
  disconnectErrorMessage,
  isDisconnectConfirming = false,
  onManualSync,
  onDisconnectRequest,
  onDisconnectCancel,
  onDisconnectConfirm,
}: DashboardSourceControlsProps) {
  const hasConnectedSource = sync.connected_sources > 0;
  const hasActiveSource = sync.active_sources > 0;
  const latestSyncRunning = sync.latest_sync_status === "running";
  const isManualSyncPending = manualSyncStatus === "pending";
  const isDisconnectPending = disconnectStatus === "pending";
  const canManualSync =
    hasConnectedSource &&
    hasActiveSource &&
    !latestSyncRunning &&
    !isManualSyncPending &&
    !isDisconnectPending;
  const canDisconnect =
    hasConnectedSource && !isManualSyncPending && !isDisconnectPending;

  return (
    <Card>
      <CardHeader className="flex-col gap-3 space-y-0 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle>Source actions</CardTitle>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Start a bounded sync or disconnect Garmin from this app.
          </p>
        </div>
        <Badge variant={hasActiveSource ? "secondary" : "outline"}>
          {hasActiveSource ? "Garmin active" : "Garmin inactive"}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-md border border-border p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium">Manual sync</p>
                <p className="mt-1 text-sm leading-5 text-muted-foreground">
                  Import the latest Garmin activity, sleep, recovery, and
                  biometric records.
                </p>
              </div>
              <Button
                type="button"
                size="sm"
                onClick={onManualSync}
                disabled={!canManualSync}
              >
                {isManualSyncPending ? (
                  <Loader2 className="animate-spin" aria-hidden="true" />
                ) : (
                  <RefreshCw aria-hidden="true" />
                )}
                Sync
              </Button>
            </div>
            {!hasConnectedSource ? (
              <p className="mt-3 text-xs text-muted-foreground">
                Connect Garmin before syncing.
              </p>
            ) : null}
            {hasConnectedSource && !hasActiveSource ? (
              <p className="mt-3 text-xs text-muted-foreground">
                Reconnect Garmin before syncing.
              </p>
            ) : null}
            {latestSyncRunning ? (
              <p className="mt-3 text-xs text-muted-foreground">
                A sync is already running.
              </p>
            ) : null}
          </div>

          <div className="rounded-md border border-border p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium">Garmin connection</p>
                <p className="mt-1 text-sm leading-5 text-muted-foreground">
                  Stop future Garmin syncs and remove stored session material.
                </p>
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={onDisconnectRequest}
                disabled={!canDisconnect}
              >
                <Unplug aria-hidden="true" />
                Disconnect
              </Button>
            </div>
          </div>
        </div>

        {manualSyncStatus === "success" ? (
          <Alert>
            <CheckCircle2 aria-hidden="true" />
            <AlertTitle>Manual sync complete</AlertTitle>
            <AlertDescription>
              {manualSyncMessage(manualSyncResult)}
            </AlertDescription>
          </Alert>
        ) : null}

        {manualSyncStatus === "error" ? (
          <Alert variant="destructive">
            <AlertTriangle aria-hidden="true" />
            <AlertTitle>Manual sync failed</AlertTitle>
            <AlertDescription>
              {manualSyncErrorMessage ?? "Manual sync could not be started."}
            </AlertDescription>
          </Alert>
        ) : null}

        {disconnectStatus === "success" ? (
          <Alert>
            <CheckCircle2 aria-hidden="true" />
            <AlertTitle>Garmin disconnected</AlertTitle>
            <AlertDescription>
              Future syncs are disabled and dashboard data is refreshing.
            </AlertDescription>
          </Alert>
        ) : null}

        {disconnectStatus === "error" ? (
          <Alert variant="destructive">
            <AlertTriangle aria-hidden="true" />
            <AlertTitle>Disconnect failed</AlertTitle>
            <AlertDescription>
              {disconnectErrorMessage ?? "Garmin could not be disconnected."}
            </AlertDescription>
          </Alert>
        ) : null}

        {isDisconnectConfirming ? (
          <Alert variant="destructive">
            <AlertTriangle aria-hidden="true" />
            <AlertTitle>Disconnect Garmin?</AlertTitle>
            <AlertDescription>
              Future Garmin syncs will stop. Existing synced records stay in the
              dashboard until you delete synced data separately.
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="destructive"
                  onClick={onDisconnectConfirm}
                  disabled={isDisconnectPending}
                >
                  {isDisconnectPending ? (
                    <Loader2 className="animate-spin" aria-hidden="true" />
                  ) : (
                    <Unplug aria-hidden="true" />
                  )}
                  Confirm disconnect
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={onDisconnectCancel}
                  disabled={isDisconnectPending}
                >
                  <X aria-hidden="true" />
                  Cancel
                </Button>
              </div>
            </AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}

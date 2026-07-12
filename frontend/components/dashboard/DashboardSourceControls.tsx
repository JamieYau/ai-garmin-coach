"use client";

import { useState, type FormEvent } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  LockKeyhole,
  PlugZap,
  RefreshCw,
  Sparkles,
  Unplug,
  X,
} from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { DashboardOverviewResponse } from "@/lib/api/dashboard";
import type {
  GarminConnectionRequest,
  GarminConnectionResponse,
  ManualSyncResponse,
} from "@/lib/api/dataControls";

type ActionStatus = "idle" | "pending" | "success" | "error";

export type DashboardSourceControlsProps = {
  sync: DashboardOverviewResponse["sync"];
  connectStatus?: ActionStatus;
  connectResult?: GarminConnectionResponse | null;
  connectErrorMessage?: string | null;
  demoStatus?: ActionStatus;
  demoResult?: ManualSyncResponse | null;
  demoErrorMessage?: string | null;
  manualSyncStatus?: ActionStatus;
  manualSyncResult?: ManualSyncResponse | null;
  manualSyncErrorMessage?: string | null;
  disconnectStatus?: ActionStatus;
  disconnectErrorMessage?: string | null;
  isDisconnectConfirming?: boolean;
  onConnect: (request: GarminConnectionRequest) => void;
  onLoadDemoData?: () => void;
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
  connectStatus = "idle",
  connectResult,
  connectErrorMessage,
  demoStatus = "idle",
  demoResult,
  demoErrorMessage,
  manualSyncStatus = "idle",
  manualSyncResult,
  manualSyncErrorMessage,
  disconnectStatus = "idle",
  disconnectErrorMessage,
  isDisconnectConfirming = false,
  onConnect,
  onLoadDemoData = () => undefined,
  onManualSync,
  onDisconnectRequest,
  onDisconnectCancel,
  onDisconnectConfirm,
}: DashboardSourceControlsProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [useChinaRegion, setUseChinaRegion] = useState(false);
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  );
  const hasConnectedSource = sync.connected_sources > 0;
  const hasActiveSource = sync.active_sources > 0;
  const latestSyncRunning = sync.latest_sync_status === "running";
  const isConnectPending = connectStatus === "pending";
  const isDemoPending = demoStatus === "pending";
  const isManualSyncPending = manualSyncStatus === "pending";
  const isDisconnectPending = disconnectStatus === "pending";
  const connectionRequiresMfa =
    connectResult?.requires_mfa || connectResult?.status === "mfa_required";
  const canSubmitConnection =
    !isConnectPending &&
    !isDemoPending &&
    !isManualSyncPending &&
    !isDisconnectPending;
  const canManualSync =
    hasConnectedSource &&
    hasActiveSource &&
    !latestSyncRunning &&
    !isConnectPending &&
    !isDemoPending &&
    !isManualSyncPending &&
    !isDisconnectPending;
  const canDisconnect =
    hasConnectedSource &&
    !isConnectPending &&
    !isDemoPending &&
    !isManualSyncPending &&
    !isDisconnectPending;

  function handleConnectSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedUsername = username.trim();
    const trimmedMfaCode = mfaCode.trim();

    if (!trimmedUsername || !password) {
      setValidationMessage("Enter your Garmin username and password.");
      return;
    }

    if (connectionRequiresMfa && !trimmedMfaCode) {
      setValidationMessage("Enter the Garmin verification code.");
      return;
    }

    setValidationMessage(null);
    onConnect({
      username: trimmedUsername,
      password,
      mfa_code: trimmedMfaCode || undefined,
      is_cn: useChinaRegion,
    });
  }

  return (
    <Card>
      <CardHeader className="flex-col gap-3 space-y-0 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle>Source actions</CardTitle>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            Connect Garmin, start a bounded sync, or disconnect this app.
          </p>
        </div>
        <Badge variant={hasActiveSource ? "secondary" : "outline"}>
          {hasActiveSource ? "Garmin active" : "Garmin inactive"}
        </Badge>
      </CardHeader>
      <CardContent className="space-y-4">
        <form
          className="rounded-md border border-border p-3"
          onSubmit={handleConnectSubmit}
        >
          <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-start">
            <div>
              <p className="text-sm font-medium">Connect Garmin</p>
              <p className="mt-1 text-sm leading-5 text-muted-foreground">
                Use your Garmin credentials once to create an app session.
                Credentials are submitted to the API for connection setup and
                are not displayed after submission.
              </p>
            </div>
            {hasActiveSource ? (
              <Badge variant="secondary">Connected</Badge>
            ) : (
              <Badge variant="outline">Not connected</Badge>
            )}
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="garmin-username">Garmin username</Label>
              <Input
                id="garmin-username"
                name="username"
                type="email"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                disabled={!canSubmitConnection}
                aria-invalid={validationMessage ? true : undefined}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="garmin-password">Garmin password</Label>
              <Input
                id="garmin-password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={!canSubmitConnection}
                aria-invalid={validationMessage ? true : undefined}
              />
            </div>
          </div>

          {connectionRequiresMfa ? (
            <div className="mt-3 space-y-2">
              <Label htmlFor="garmin-mfa-code">Garmin verification code</Label>
              <Input
                id="garmin-mfa-code"
                name="mfa_code"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={mfaCode}
                onChange={(event) => setMfaCode(event.target.value)}
                disabled={!canSubmitConnection}
                aria-invalid={validationMessage ? true : undefined}
              />
            </div>
          ) : null}

          <div className="mt-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <input
                type="checkbox"
                className="size-4 rounded border-border"
                checked={useChinaRegion}
                onChange={(event) => setUseChinaRegion(event.target.checked)}
                disabled={!canSubmitConnection}
              />
              Use Garmin China region
            </label>
            <Button type="submit" disabled={!canSubmitConnection}>
              {isConnectPending ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : (
                <PlugZap aria-hidden="true" />
              )}
              {connectionRequiresMfa ? "Verify and connect" : "Connect Garmin"}
            </Button>
          </div>

          {validationMessage ? (
            <p className="mt-3 text-sm text-destructive">{validationMessage}</p>
          ) : null}

          {hasActiveSource ? (
            <p className="mt-3 text-xs text-muted-foreground">
              Submitting this form replaces the saved Garmin app session.
            </p>
          ) : null}
        </form>

        <div className="rounded-md border border-dashed border-border bg-muted/30 p-3">
          <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm font-medium">Explore with demo data</p>
              <p className="mt-1 text-sm leading-5 text-muted-foreground">
                Load a private set of realistic synthetic training and recovery
                records. No Garmin account or credentials are needed.
              </p>
            </div>
            <Button
              type="button"
              variant="outline"
              onClick={onLoadDemoData}
              disabled={!canSubmitConnection}
            >
              {isDemoPending ? (
                <Loader2 className="animate-spin" aria-hidden="true" />
              ) : (
                <Sparkles aria-hidden="true" />
              )}
              {sync.has_demo_data ? "Refresh demo data" : "Load demo data"}
            </Button>
          </div>
        </div>

        {demoStatus === "success" ? (
          <Alert>
            <CheckCircle2 aria-hidden="true" />
            <AlertTitle>Demo data loaded</AlertTitle>
            <AlertDescription>{manualSyncMessage(demoResult)}</AlertDescription>
          </Alert>
        ) : null}

        {demoStatus === "error" ? (
          <Alert variant="destructive">
            <AlertTriangle aria-hidden="true" />
            <AlertTitle>Demo data could not be loaded</AlertTitle>
            <AlertDescription>
              {demoErrorMessage ?? "Try again in a moment."}
            </AlertDescription>
          </Alert>
        ) : null}

        {connectStatus === "success" && connectionRequiresMfa ? (
          <Alert>
            <LockKeyhole aria-hidden="true" />
            <AlertTitle>Garmin verification required</AlertTitle>
            <AlertDescription>
              {connectResult?.message ??
                "Enter the verification code from Garmin to finish connecting."}
            </AlertDescription>
          </Alert>
        ) : null}

        {connectStatus === "success" && !connectionRequiresMfa ? (
          <Alert>
            <CheckCircle2 aria-hidden="true" />
            <AlertTitle>Garmin connected</AlertTitle>
            <AlertDescription>
              {connectResult?.display_name
                ? `${connectResult.display_name} is connected. Dashboard data is refreshing.`
                : "Garmin is connected. Dashboard data is refreshing."}
            </AlertDescription>
          </Alert>
        ) : null}

        {connectStatus === "error" ? (
          <Alert variant="destructive">
            <AlertTriangle aria-hidden="true" />
            <AlertTitle>Garmin connection failed</AlertTitle>
            <AlertDescription>
              {connectErrorMessage ?? "Garmin could not be connected."}
            </AlertDescription>
          </Alert>
        ) : null}

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

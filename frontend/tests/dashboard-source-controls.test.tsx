import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { DashboardSourceControls } from "@/components/dashboard/DashboardSourceControls";
import type { DashboardOverviewResponse } from "@/lib/api/dashboard";

const activeSync: DashboardOverviewResponse["sync"] = {
  connected_sources: 1,
  active_sources: 1,
  has_demo_data: false,
  latest_sync_status: "succeeded",
  latest_sync_completed_at: "2026-07-07T09:15:00Z",
  latest_sync_error_code: null,
};

const inactiveSync: DashboardOverviewResponse["sync"] = {
  ...activeSync,
  active_sources: 0,
};

const handlers = {
  onConnect: vi.fn(),
  onLoadDemoData: vi.fn(),
  onManualSync: vi.fn(),
  onDisconnectRequest: vi.fn(),
  onDisconnectCancel: vi.fn(),
  onDisconnectConfirm: vi.fn(),
};

describe("DashboardSourceControls", () => {
  it("renders manual sync and disconnect actions for active Garmin sources", () => {
    const markup = renderToStaticMarkup(
      <DashboardSourceControls sync={activeSync} {...handlers} />,
    );

    expect(markup).toContain("Source actions");
    expect(markup).toContain("Garmin active");
    expect(markup).toContain("Connect Garmin");
    expect(markup).toContain("Garmin username");
    expect(markup).toContain("Garmin password");
    expect(markup).toContain("not displayed after submission");
    expect(markup).toContain("Manual sync");
    expect(markup).toContain("Sync");
    expect(markup).toContain("Garmin connection");
    expect(markup).toContain("Disconnect");
  });

  it("renders inactive source guidance when Garmin cannot sync", () => {
    const markup = renderToStaticMarkup(
      <DashboardSourceControls sync={inactiveSync} {...handlers} />,
    );

    expect(markup).toContain("Garmin inactive");
    expect(markup).toContain("Reconnect Garmin before syncing.");
  });

  it("renders Garmin connection validation, success, and MFA states", () => {
    const validationMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={activeSync}
        connectErrorMessage="Enter your Garmin username and password."
        connectStatus="error"
        {...handlers}
      />,
    );
    const successMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={activeSync}
        connectStatus="success"
        connectResult={{
          id: "connection-1",
          source: "garmin",
          status: "active",
          provider_subject_id: "provider-1",
          display_name: "Runner Example",
          requires_mfa: false,
          message: null,
        }}
        {...handlers}
      />,
    );
    const mfaMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={inactiveSync}
        connectStatus="success"
        connectResult={{
          id: null,
          source: "garmin",
          status: "mfa_required",
          provider_subject_id: null,
          display_name: null,
          requires_mfa: true,
          message: "Garmin requires a multi-factor authentication code.",
        }}
        {...handlers}
      />,
    );

    expect(validationMarkup).toContain("Garmin connection failed");
    expect(validationMarkup).toContain("Enter your Garmin username");
    expect(successMarkup).toContain("Garmin connected");
    expect(successMarkup).toContain("Runner Example is connected");
    expect(mfaMarkup).toContain("Garmin verification required");
    expect(mfaMarkup).toContain("Garmin verification code");
    expect(mfaMarkup).toContain("Verify and connect");
  });

  it("renders Garmin connection rate-limit, invalid-credential, and generic failure states", () => {
    const rateLimitMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={inactiveSync}
        connectStatus="error"
        connectErrorMessage="Too many Garmin connection attempts. Wait a minute and try again."
        {...handlers}
      />,
    );
    const invalidCredentialMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={inactiveSync}
        connectStatus="error"
        connectErrorMessage="Garmin credentials were not accepted. Check the username and password, then try again."
        {...handlers}
      />,
    );
    const genericErrorMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={inactiveSync}
        connectStatus="error"
        connectErrorMessage="Garmin could not be connected."
        {...handlers}
      />,
    );

    expect(rateLimitMarkup).toContain("Too many Garmin connection attempts");
    expect(invalidCredentialMarkup).toContain(
      "Garmin credentials were not accepted",
    );
    expect(genericErrorMarkup).toContain("Garmin could not be connected");
  });

  it("renders manual sync success and rate-limit error states", () => {
    const successMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={activeSync}
        manualSyncStatus="success"
        manualSyncResult={{
          id: "sync-run-1",
          source_connection_id: "source-1",
          status: "succeeded",
          sync_type: "manual",
          window_start: "2026-07-03T00:00:00Z",
          window_end: "2026-07-09T23:59:59Z",
          records_seen: 5,
          records_imported: 4,
          error_code: null,
          started_at: "2026-07-09T10:00:00Z",
          completed_at: "2026-07-09T10:01:00Z",
        }}
        {...handlers}
      />,
    );
    const errorMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={activeSync}
        manualSyncStatus="error"
        manualSyncErrorMessage="Too many requests. Wait a minute and try again."
        {...handlers}
      />,
    );

    expect(successMarkup).toContain("Manual sync complete");
    expect(successMarkup).toContain("Imported 4 of 5 records");
    expect(errorMarkup).toContain("Manual sync failed");
    expect(errorMarkup).toContain("Too many requests");
  });

  it("renders a credential-free demo action and its result states", () => {
    const successMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={activeSync}
        demoStatus="success"
        demoResult={{
          id: "demo-sync-run-1",
          source_connection_id: "demo-source-1",
          status: "succeeded",
          sync_type: "backfill",
          window_start: "2026-07-01T00:00:00Z",
          window_end: "2026-07-14T23:59:59Z",
          records_seen: 50,
          records_imported: 50,
          error_code: null,
          started_at: "2026-07-14T10:00:00Z",
          completed_at: "2026-07-14T10:00:01Z",
        }}
        {...handlers}
      />,
    );
    const errorMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={activeSync}
        demoStatus="error"
        demoErrorMessage="Demo records are temporarily unavailable."
        {...handlers}
      />,
    );

    expect(successMarkup).toContain("Explore with demo data");
    expect(successMarkup).toContain(
      "No Garmin account or credentials are needed",
    );
    expect(successMarkup).toContain("Demo data loaded");
    expect(successMarkup).toContain("Imported 50 of 50 records");
    expect(errorMarkup).toContain("Demo data could not be loaded");
    expect(errorMarkup).toContain("Demo records are temporarily unavailable");
  });

  it("renders disconnect confirmation and success states", () => {
    const confirmMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={activeSync}
        isDisconnectConfirming
        {...handlers}
      />,
    );
    const successMarkup = renderToStaticMarkup(
      <DashboardSourceControls
        sync={activeSync}
        disconnectStatus="success"
        {...handlers}
      />,
    );

    expect(confirmMarkup).toContain("Disconnect Garmin?");
    expect(confirmMarkup).toContain("Confirm disconnect");
    expect(confirmMarkup).toContain("Existing synced records stay");
    expect(successMarkup).toContain("Garmin disconnected");
    expect(successMarkup).toContain("Future syncs are disabled");
  });
});

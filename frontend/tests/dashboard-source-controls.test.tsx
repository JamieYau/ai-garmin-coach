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

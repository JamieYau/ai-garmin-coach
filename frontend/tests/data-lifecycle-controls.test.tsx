import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { DataLifecycleControls } from "@/components/settings/DataLifecycleControls";
import type {
  DeleteAccountDataResponse,
  DeleteSyncedDataResponse,
} from "@/lib/api/dataControls";

type MockMutation<TData> = {
  isPending: boolean;
  isSuccess: boolean;
  isError: boolean;
  data: TData | undefined;
  error: Error | null;
  mutate: ReturnType<typeof vi.fn>;
};

const deleteSyncedDataMutation: MockMutation<DeleteSyncedDataResponse> = {
  isPending: false,
  isSuccess: false,
  isError: false,
  data: undefined,
  error: null,
  mutate: vi.fn(),
};

const deleteAccountDataMutation: MockMutation<DeleteAccountDataResponse> = {
  isPending: false,
  isSuccess: false,
  isError: false,
  data: undefined,
  error: null,
  mutate: vi.fn(),
};

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    refresh: vi.fn(),
  }),
}));

vi.mock("@/lib/auth/client", () => ({
  authClient: {
    signOut: vi.fn(),
  },
}));

vi.mock("@/hooks/useDataControls", () => ({
  useDeleteSyncedDataMutation: () => deleteSyncedDataMutation,
  useDeleteAccountDataMutation: () => deleteAccountDataMutation,
}));

describe("DataLifecycleControls", () => {
  it("renders destructive data lifecycle controls with explicit confirmation copy", () => {
    const markup = renderToStaticMarkup(<DataLifecycleControls />);

    expect(markup).toContain("Settings");
    expect(markup).toContain("Data lifecycle");
    expect(markup).toContain("Delete synced Garmin data");
    expect(markup).toContain("DELETE GARMIN DATA");
    expect(markup).toContain("Delete local account data");
    expect(markup).toContain("DELETE LOCAL ACCOUNT DATA");
    expect(markup).toContain("do not delete your Garmin account");
    expect(markup).toContain("disabled");
  });

  it("renders success states with deleted record counts", () => {
    deleteSyncedDataMutation.isSuccess = true;
    deleteSyncedDataMutation.data = {
      source: "garmin",
      activities_deleted: 1,
      daily_metrics_deleted: 1,
      sleep_sessions_deleted: 1,
      biometric_samples_deleted: 1,
      raw_observations_deleted: 1,
      sync_runs_deleted: 1,
      coach_insights_deleted: 1,
      total_deleted: 7,
    };
    deleteAccountDataMutation.isSuccess = true;
    deleteAccountDataMutation.data = {
      user_id: "user-1",
      deleted: true,
      source_connections_deleted: 1,
      synced_records_deleted: 7,
      total_deleted: 9,
    };

    const markup = renderToStaticMarkup(<DataLifecycleControls />);

    expect(markup).toContain("Synced Garmin data deleted");
    expect(markup).toContain("Deleted 7 local records");
    expect(markup).toContain("Local account data deleted");
    expect(markup).toContain("Deleted 9 local records");

    deleteSyncedDataMutation.isSuccess = false;
    deleteSyncedDataMutation.data = undefined;
    deleteAccountDataMutation.isSuccess = false;
    deleteAccountDataMutation.data = undefined;
  });

  it("renders API error messages for failed destructive actions", () => {
    deleteSyncedDataMutation.isError = true;
    deleteSyncedDataMutation.error = new Error("Source connection not found");
    deleteAccountDataMutation.isError = true;
    deleteAccountDataMutation.error = new Error("Authentication required");

    const markup = renderToStaticMarkup(<DataLifecycleControls />);

    expect(markup).toContain("Synced data deletion failed");
    expect(markup).toContain("Source connection not found");
    expect(markup).toContain("Local account data deletion failed");
    expect(markup).toContain("Authentication required");

    deleteSyncedDataMutation.isError = false;
    deleteSyncedDataMutation.error = null;
    deleteAccountDataMutation.isError = false;
    deleteAccountDataMutation.error = null;
  });
});

import { apiFetchJson } from "@/lib/query/api";

export type IsoDateString = string;
export type IsoDateTimeString = string;

export type ManualSyncRequest = {
  source?: string;
  start_date?: IsoDateString;
  end_date?: IsoDateString;
};

export type ManualSyncResponse = {
  id: string;
  source_connection_id: string;
  status: string;
  sync_type: string;
  window_start: IsoDateTimeString | null;
  window_end: IsoDateTimeString | null;
  records_seen: number;
  records_imported: number;
  error_code: string | null;
  started_at: IsoDateTimeString | null;
  completed_at: IsoDateTimeString | null;
};

export type DisconnectGarminResponse = {
  id: string;
  source: string;
  status: string;
};

export type DeleteSyncedDataResponse = {
  source: string | null;
  activities_deleted: number;
  daily_metrics_deleted: number;
  sleep_sessions_deleted: number;
  biometric_samples_deleted: number;
  raw_observations_deleted: number;
  sync_runs_deleted: number;
  coach_insights_deleted: number;
  total_deleted: number;
};

export type DeleteAccountDataResponse = {
  user_id: string;
  deleted: boolean;
  source_connections_deleted: number;
  synced_records_deleted: number;
  total_deleted: number;
};

export function triggerManualSync(request: ManualSyncRequest = {}) {
  return apiFetchJson<ManualSyncResponse>("/sync/manual", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
}

export function disconnectGarmin() {
  return apiFetchJson<DisconnectGarminResponse>("/connections/garmin", {
    method: "DELETE",
  });
}

export function deleteSyncedData(options: { source?: string } = {}) {
  const path = options.source
    ? `/users/me/data?source=${encodeURIComponent(options.source)}`
    : "/users/me/data";

  return apiFetchJson<DeleteSyncedDataResponse>(path, {
    method: "DELETE",
  });
}

export function deleteAccountData() {
  return apiFetchJson<DeleteAccountDataResponse>("/users/me", {
    method: "DELETE",
  });
}

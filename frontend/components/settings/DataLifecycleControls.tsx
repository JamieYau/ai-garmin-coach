"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useDeleteAccountDataMutation,
  useDeleteSyncedDataMutation,
} from "@/hooks/useDataControls";
import { authClient } from "@/lib/auth/client";
import { getApiErrorMessage, isApiError } from "@/lib/api/errors";

const DELETE_SYNCED_CONFIRMATION = "DELETE GARMIN DATA";
const DELETE_ACCOUNT_CONFIRMATION = "DELETE LOCAL ACCOUNT DATA";

function dataLifecycleErrorMessage(error: unknown, action: string) {
  if (isApiError(error) && error.status === 429) {
    return "Too many requests. Wait a minute and try again.";
  }

  return getApiErrorMessage(error, `${action} failed. Try again.`);
}

type DestructiveActionCardProps = {
  title: string;
  description: string;
  confirmationLabel: string;
  confirmationValue: string;
  confirmationPlaceholder: string;
  buttonLabel: string;
  pendingLabel: string;
  isPending: boolean;
  isDisabled?: boolean;
  onConfirm: () => void;
};

function DestructiveActionCard({
  title,
  description,
  confirmationLabel,
  confirmationValue,
  confirmationPlaceholder,
  buttonLabel,
  pendingLabel,
  isPending,
  isDisabled = false,
  onConfirm,
}: DestructiveActionCardProps) {
  const [typedConfirmation, setTypedConfirmation] = useState("");
  const canSubmit =
    typedConfirmation === confirmationValue && !isPending && !isDisabled;

  return (
    <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-2xl">
          <h3 className="text-sm font-semibold text-destructive">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        </div>
        <Trash2 className="size-5 text-destructive" aria-hidden="true" />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
        <div className="space-y-2">
          <Label>{confirmationLabel}</Label>
          <Input
            value={typedConfirmation}
            onChange={(event) => setTypedConfirmation(event.target.value)}
            placeholder={confirmationPlaceholder}
            disabled={isPending || isDisabled}
            aria-label={confirmationLabel}
          />
        </div>
        <Button
          type="button"
          variant="destructive"
          onClick={onConfirm}
          disabled={!canSubmit}
        >
          {isPending ? (
            <Loader2 className="animate-spin" aria-hidden="true" />
          ) : (
            <Trash2 aria-hidden="true" />
          )}
          {isPending ? pendingLabel : buttonLabel}
        </Button>
      </div>
    </div>
  );
}

export function DataLifecycleControls() {
  const router = useRouter();
  const deleteSyncedDataMutation = useDeleteSyncedDataMutation();
  const deleteAccountDataMutation = useDeleteAccountDataMutation({
    onSuccess: () => {
      void authClient.signOut({
        fetchOptions: {
          onSuccess: () => {
            router.push("/sign-in");
            router.refresh();
          },
        },
      });
    },
  });

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6 sm:px-8 lg:px-10">
      <header className="border-b border-border pb-6">
        <h1 className="text-3xl font-semibold tracking-normal">Settings</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
          Manage locally stored Garmin records and account data for this app.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Data lifecycle</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <AlertTriangle aria-hidden="true" />
            <AlertTitle>Destructive actions</AlertTitle>
            <AlertDescription>
              These controls only affect data stored by AI Garmin Coach. They do
              not delete your Garmin account or remove records from Garmin.
            </AlertDescription>
          </Alert>

          <DestructiveActionCard
            title="Delete synced Garmin data"
            description="Deletes your synced Garmin activities, daily metrics, sleep sessions, biometric samples, raw observations, sync history, and linked coach insights. Your Garmin connection record remains."
            confirmationLabel={`Type ${DELETE_SYNCED_CONFIRMATION} to confirm`}
            confirmationValue={DELETE_SYNCED_CONFIRMATION}
            confirmationPlaceholder={DELETE_SYNCED_CONFIRMATION}
            buttonLabel="Delete synced data"
            pendingLabel="Deleting data"
            isPending={deleteSyncedDataMutation.isPending}
            isDisabled={deleteAccountDataMutation.isPending}
            onConfirm={() =>
              deleteSyncedDataMutation.mutate({ source: "garmin" })
            }
          />

          {deleteSyncedDataMutation.isSuccess ? (
            <Alert>
              <CheckCircle2 aria-hidden="true" />
              <AlertTitle>Synced Garmin data deleted</AlertTitle>
              <AlertDescription>
                Deleted{" "}
                {deleteSyncedDataMutation.data.total_deleted.toLocaleString(
                  "en-GB",
                )}{" "}
                local records. Dashboard data is refreshing.
              </AlertDescription>
            </Alert>
          ) : null}

          {deleteSyncedDataMutation.isError ? (
            <Alert variant="destructive">
              <AlertTriangle aria-hidden="true" />
              <AlertTitle>Synced data deletion failed</AlertTitle>
              <AlertDescription>
                {dataLifecycleErrorMessage(
                  deleteSyncedDataMutation.error,
                  "Synced data deletion",
                )}
              </AlertDescription>
            </Alert>
          ) : null}

          <DestructiveActionCard
            title="Delete local account data"
            description="Deletes your local app profile, source connections, synced records, sync history, raw observations, and coach insights. Your Better Auth sign-in record may still exist, so the app signs you out after deletion."
            confirmationLabel={`Type ${DELETE_ACCOUNT_CONFIRMATION} to confirm`}
            confirmationValue={DELETE_ACCOUNT_CONFIRMATION}
            confirmationPlaceholder={DELETE_ACCOUNT_CONFIRMATION}
            buttonLabel="Delete local account data"
            pendingLabel="Deleting account data"
            isPending={deleteAccountDataMutation.isPending}
            isDisabled={deleteSyncedDataMutation.isPending}
            onConfirm={() => deleteAccountDataMutation.mutate()}
          />

          {deleteAccountDataMutation.isSuccess ? (
            <Alert>
              <CheckCircle2 aria-hidden="true" />
              <AlertTitle>Local account data deleted</AlertTitle>
              <AlertDescription>
                Deleted{" "}
                {deleteAccountDataMutation.data.total_deleted.toLocaleString(
                  "en-GB",
                )}{" "}
                local records. Signing out now.
              </AlertDescription>
            </Alert>
          ) : null}

          {deleteAccountDataMutation.isError ? (
            <Alert variant="destructive">
              <AlertTriangle aria-hidden="true" />
              <AlertTitle>Local account data deletion failed</AlertTitle>
              <AlertDescription>
                {dataLifecycleErrorMessage(
                  deleteAccountDataMutation.error,
                  "Local account data deletion",
                )}
              </AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

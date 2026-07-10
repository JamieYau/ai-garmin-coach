"use client";

import {
  useMutation,
  useQueryClient,
  type QueryClient,
  type UseMutationOptions,
} from "@tanstack/react-query";

import { dashboardQueryKeys } from "@/hooks/useDashboard";
import {
  connectGarmin,
  deleteAccountData,
  deleteSyncedData,
  disconnectGarmin,
  triggerManualSync,
  type DeleteAccountDataResponse,
  type DeleteSyncedDataResponse,
  type DisconnectGarminResponse,
  type GarminConnectionRequest,
  type GarminConnectionResponse,
  type ManualSyncRequest,
  type ManualSyncResponse,
} from "@/lib/api/dataControls";

type DataControlMutationOptions<TData, TVariables> = Omit<
  UseMutationOptions<TData, Error, TVariables>,
  "mutationFn"
>;

export function invalidateDashboardData(queryClient: QueryClient) {
  return queryClient.invalidateQueries({ queryKey: dashboardQueryKeys.all });
}

export function useManualSyncMutation(
  options?: DataControlMutationOptions<
    ManualSyncResponse,
    ManualSyncRequest | undefined
  >,
) {
  const queryClient = useQueryClient();

  return useMutation({
    ...options,
    mutationFn: (request) => triggerManualSync(request),
    onSuccess: async (data, variables, onMutateResult, context) => {
      await invalidateDashboardData(queryClient);
      await options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useConnectGarminMutation(
  options?: DataControlMutationOptions<
    GarminConnectionResponse,
    GarminConnectionRequest
  >,
) {
  const queryClient = useQueryClient();

  return useMutation({
    ...options,
    mutationFn: connectGarmin,
    onSuccess: async (data, variables, onMutateResult, context) => {
      if (!data.requires_mfa) {
        await invalidateDashboardData(queryClient);
      }
      await options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useDisconnectGarminMutation(
  options?: DataControlMutationOptions<DisconnectGarminResponse, void>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    ...options,
    mutationFn: disconnectGarmin,
    onSuccess: async (data, variables, onMutateResult, context) => {
      await invalidateDashboardData(queryClient);
      await options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useDeleteSyncedDataMutation(
  options?: DataControlMutationOptions<
    DeleteSyncedDataResponse,
    { source?: string } | undefined
  >,
) {
  const queryClient = useQueryClient();

  return useMutation({
    ...options,
    mutationFn: (variables) => deleteSyncedData(variables),
    onSuccess: async (data, variables, onMutateResult, context) => {
      await invalidateDashboardData(queryClient);
      await options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

export function useDeleteAccountDataMutation(
  options?: DataControlMutationOptions<DeleteAccountDataResponse, void>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    ...options,
    mutationFn: deleteAccountData,
    onSuccess: async (data, variables, onMutateResult, context) => {
      await invalidateDashboardData(queryClient);
      await options?.onSuccess?.(data, variables, onMutateResult, context);
    },
  });
}

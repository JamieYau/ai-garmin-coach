import { ApiError } from "@/lib/query/api";

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function getApiErrorMessage(
  error: unknown,
  fallback = "The dashboard data could not be loaded.",
) {
  if (isApiError(error)) {
    if (error.status === 401) {
      return "Sign in again to view your dashboard data.";
    }

    if (error.status >= 500) {
      return "The API is temporarily unavailable.";
    }

    return error.message;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

"use client";

import { ErrorState } from "@/components/states";

export default function DashboardError({
  error,
  reset,
}: Readonly<{
  error: Error & { digest?: string };
  reset: () => void;
}>) {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-6 sm:px-8 lg:px-10">
      <ErrorState
        title="Dashboard failed to load"
        description={error.message || "Refresh the dashboard and try again."}
        actionLabel="Try again"
        onAction={reset}
      />
    </div>
  );
}

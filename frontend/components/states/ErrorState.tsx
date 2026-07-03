"use client";

import { AlertTriangle } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ErrorStateProps = {
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
};

export function ErrorState({
  title = "Something went wrong",
  description = "The dashboard could not load this data.",
  actionLabel,
  onAction,
  className,
}: ErrorStateProps) {
  return (
    <Alert
      variant="destructive"
      className={cn(
        "min-h-40 content-center p-6 has-data-[slot=alert-action]:pr-6",
        className,
      )}
    >
      <AlertTriangle className="size-5" aria-hidden="true" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{description}</AlertDescription>
      {actionLabel && onAction ? (
        <Button
          type="button"
          variant="outline"
          onClick={onAction}
          className="col-start-2 mt-5 w-fit"
        >
          {actionLabel}
        </Button>
      ) : null}
    </Alert>
  );
}

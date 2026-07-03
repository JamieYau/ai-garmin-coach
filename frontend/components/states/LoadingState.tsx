import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

type LoadingStateProps = {
  title?: string;
  description?: string;
  className?: string;
};

export function LoadingState({
  title = "Loading",
  description,
  className,
}: LoadingStateProps) {
  return (
    <div
      className={cn(
        "flex min-h-40 flex-col items-center justify-center rounded-lg border border-border bg-card p-6 text-center",
        className
      )}
      role="status"
      aria-live="polite"
    >
      <Spinner className="size-5 text-muted-foreground" />
      <p className="mt-3 text-sm font-medium">{title}</p>
      {description ? (
        <p className="mt-1 max-w-sm text-sm leading-6 text-muted-foreground">
          {description}
        </p>
      ) : null}
    </div>
  );
}

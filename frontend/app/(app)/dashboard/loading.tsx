import { Skeleton } from "@/components/states";

export default function DashboardLoading() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6 sm:px-8 lg:px-10">
      <header className="flex flex-col justify-between gap-4 border-b border-border pb-6 lg:flex-row lg:items-end">
        <div className="w-full max-w-2xl">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="mt-3 h-9 w-72 max-w-full" />
          <Skeleton className="mt-3 h-4 w-full" />
          <Skeleton className="mt-2 h-4 w-3/4" />
        </div>
        <Skeleton className="h-10 w-24" />
      </header>

      <section
        className="grid gap-4 md:grid-cols-3"
        aria-label="Loading metrics"
      >
        {["load", "recovery", "sleep"].map((item) => (
          <article
            key={item}
            className="rounded-lg border border-border bg-card p-5 shadow-sm"
          >
            <div className="flex items-center justify-between gap-3">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="size-5" />
            </div>
            <Skeleton className="mt-5 h-8 w-36" />
            <Skeleton className="mt-3 h-4 w-44 max-w-full" />
          </article>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
      </section>
    </div>
  );
}

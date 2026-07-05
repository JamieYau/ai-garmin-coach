import { Activity, ArrowRight, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";

const highlights = [
  "Garmin sync",
  "Recovery trends",
  "Structured coach insights",
];

export default function Home() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col justify-center gap-12 px-6 py-10 sm:px-8 lg:px-10">
        <nav className="flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <span className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Activity className="size-5" aria-hidden="true" />
            </span>
            AI Garmin Coach
          </Link>
          <Link
            href="/sign-in"
            className="inline-flex h-10 items-center justify-center rounded-md border border-border px-4 text-sm font-medium transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Sign in
          </Link>
        </nav>

        <div className="grid items-center gap-10 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="max-w-2xl">
            <Badge variant="secondary" className="mb-5">
              MVP dashboard
            </Badge>
            <h1 className="text-4xl font-semibold leading-tight tracking-normal sm:text-5xl">
              Personal training and recovery context from Garmin data.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground">
              A focused coaching workspace for normalized activity, sleep,
              recovery, and daily recommendation signals.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/sign-in"
                className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Sign in
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex h-11 items-center justify-center rounded-md border border-border px-5 text-sm font-medium transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Connect Garmin
              </Link>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-5 shadow-sm">
            <div className="flex items-center justify-between gap-4 border-b border-border pb-4">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  Today
                </p>
                <p className="mt-1 text-2xl font-semibold">Ready to sync</p>
              </div>
              <ShieldCheck
                className="size-6 text-muted-foreground"
                aria-hidden="true"
              />
            </div>
            <dl className="mt-5 grid gap-4 sm:grid-cols-3">
              {highlights.map((item) => (
                <div key={item} className="rounded-md border border-border p-4">
                  <dt className="text-sm text-muted-foreground">{item}</dt>
                  <dd className="mt-3 text-lg font-semibold">Pending</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>
    </main>
  );
}

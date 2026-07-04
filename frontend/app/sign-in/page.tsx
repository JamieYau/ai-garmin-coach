import { Suspense } from "react";
import { Activity } from "lucide-react";
import Link from "next/link";

import { AuthForm } from "@/components/auth/AuthForm";
import { Skeleton } from "@/components/states";

export default function SignInPage() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8 sm:px-8 lg:px-10">
        <nav className="flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <span className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Activity className="size-5" aria-hidden="true" />
            </span>
            AI Garmin Coach
          </Link>
        </nav>

        <div className="flex flex-1 items-center justify-center py-10">
          <Suspense fallback={<Skeleton className="h-112 w-full max-w-md" />}>
            <AuthForm />
          </Suspense>
        </div>
      </section>
    </main>
  );
}

"use client";

import {
  Activity,
  AlertCircle,
  BarChart3,
  Brain,
  Home,
  UserCircle,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { SignOutButton } from "@/components/auth/SignOutButton";
import { buttonVariants } from "@/components/ui/button";
import { authClient } from "@/lib/auth/client";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: BarChart3 },
  { href: "/dashboard#metrics", label: "Metrics", icon: Activity },
  { href: "/dashboard#coach", label: "Coach", icon: Brain },
];

type NavUser = {
  name?: string | null;
  email?: string | null;
};

export function MainNav({
  initialUser,
}: Readonly<{
  initialUser?: NavUser | null;
}>) {
  const pathname = usePathname();
  const { data: session, isPending, error } = authClient.useSession();
  const user = session?.user ?? initialUser;
  const userLabel = user?.name || user?.email || "Account";

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-4 px-6 sm:px-8 lg:px-10">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <span className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Home className="size-5" aria-hidden="true" />
          </span>
          <span className="hidden sm:inline">AI Garmin Coach</span>
        </Link>

        <nav
          className="flex items-center gap-1"
          aria-label="Primary navigation"
        >
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === "/dashboard" && item.href === "/dashboard";

            return (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  "inline-flex h-10 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isActive && "bg-muted text-foreground",
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon className="size-4" aria-hidden="true" />
                <span className="hidden md:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="flex min-w-20 items-center justify-end gap-3">
          {error ? (
            <span className="inline-flex items-center gap-2 text-sm font-medium text-destructive">
              <AlertCircle className="size-4" aria-hidden="true" />
              <span className="hidden lg:inline">Session unavailable</span>
            </span>
          ) : (
            <span className="hidden max-w-44 items-center gap-2 truncate text-sm text-muted-foreground sm:inline-flex">
              <UserCircle className="size-4 shrink-0" aria-hidden="true" />
              <span className="truncate">{userLabel}</span>
            </span>
          )}

          {isPending && !user ? (
            <span
              className="size-9 animate-pulse rounded-md bg-muted"
              aria-label="Checking session"
            />
          ) : user ? (
            <SignOutButton />
          ) : (
            <Link
              href="/sign-in"
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Sign in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

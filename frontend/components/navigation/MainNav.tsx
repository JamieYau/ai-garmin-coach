"use client";

import { Activity, BarChart3, Brain, Home } from "lucide-react";
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

export function MainNav() {
  const pathname = usePathname();
  const { data: session } = authClient.useSession();

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

        <div className="flex min-w-20 justify-end">
          {session ? (
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

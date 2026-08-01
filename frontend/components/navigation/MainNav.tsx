"use client";

import { useState } from "react";

import {
  Activity,
  AlertCircle,
  BarChart3,
  Bed,
  Brain,
  DatabaseZap,
  Ellipsis,
  Home,
  Menu,
  Settings,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { SignOutButton } from "@/components/auth/SignOutButton";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { authClient } from "@/lib/auth/client";
import { cn } from "@/lib/utils";

const primaryNavItems = [
  { href: "/dashboard", label: "Overview", icon: BarChart3 },
  { href: "/dashboard/activities", label: "Activities", icon: Activity },
  { href: "/dashboard/recovery", label: "Recovery", icon: Bed },
  { href: "/dashboard/coach", label: "Coach", icon: Brain },
];

const moreNavItems = [
  { href: "/dashboard/sources", label: "Sources", icon: DatabaseZap },
  { href: "/settings", label: "Settings", icon: Settings },
];

const allNavItems = [...primaryNavItems, ...moreNavItems];

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
  const userInitials = getInitials(userLabel);
  const moreIsActive = moreNavItems.some((item) => pathname === item.href);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-4 px-6 sm:px-8 lg:px-10">
        <Link
          href="/dashboard"
          className="flex items-center gap-2 font-semibold"
        >
          <span className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Home className="size-5" aria-hidden="true" />
          </span>
          <span className="hidden sm:inline">AI Garmin Coach</span>
        </Link>

        <nav
          className="hidden items-center gap-1 lg:flex"
          aria-label="Primary navigation"
        >
          {primaryNavItems.map((item) => {
            const Icon = item.icon;
            const itemPathname = item.href.split("#")[0];
            const isActive =
              itemPathname === "/dashboard"
                ? pathname === itemPathname && item.href === "/dashboard"
                : pathname === itemPathname;

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

          <DropdownMenu>
            <DropdownMenuTrigger
              render={
                <Button
                  variant="ghost"
                  className={cn(
                    "h-10 gap-2 px-3 text-muted-foreground hover:text-foreground",
                    moreIsActive && "bg-muted text-foreground",
                  )}
                  data-active={moreIsActive ? "true" : undefined}
                  aria-label="More navigation"
                />
              }
            >
              <Ellipsis className="size-4" aria-hidden="true" />
              <span className="hidden md:inline">More</span>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              <DropdownMenuGroup>
                {moreNavItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;

                  return (
                    <DropdownMenuItem
                      key={item.href}
                      render={<Link href={item.href} />}
                      className={cn(
                        isActive && "bg-accent text-accent-foreground",
                      )}
                    >
                      <Icon aria-hidden="true" />
                      {item.label}
                    </DropdownMenuItem>
                  );
                })}
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </nav>

        <div className="flex min-w-20 items-center justify-end gap-3">
          <ThemeToggle />

          <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
            <SheetTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon"
                  className="lg:hidden"
                  aria-label="Open navigation menu"
                />
              }
            >
              <Menu aria-hidden="true" />
            </SheetTrigger>
            <SheetContent side="right" className="w-full max-w-sm p-0">
              <SheetHeader className="border-b border-border pr-14">
                <SheetTitle>AI Garmin Coach</SheetTitle>
                <SheetDescription>
                  Navigate your training and recovery dashboard.
                </SheetDescription>
              </SheetHeader>
              <nav
                className="flex flex-col gap-1 px-4"
                aria-label="Dashboard navigation"
              >
                {allNavItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = isNavItemActive(pathname, item.href);

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                        isActive && "bg-muted text-foreground",
                      )}
                      aria-current={isActive ? "page" : undefined}
                      onClick={() => setMobileNavOpen(false)}
                    >
                      <Icon className="size-4" aria-hidden="true" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
              <SheetFooter className="border-t border-border">
                {error ? (
                  <span className="inline-flex items-center gap-2 text-sm font-medium text-destructive">
                    <AlertCircle className="size-4" aria-hidden="true" />
                    Session unavailable
                  </span>
                ) : isPending && !user ? (
                  <span
                    className="size-9 animate-pulse rounded-md bg-muted"
                    aria-label="Checking session"
                  />
                ) : user ? (
                  <>
                    <div className="flex items-center gap-3 px-1 py-2">
                      <Avatar>
                        <AvatarFallback>{userInitials}</AvatarFallback>
                      </Avatar>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {userLabel}
                        </p>
                        {user.name && user.email ? (
                          <p className="truncate text-xs text-muted-foreground">
                            {user.email}
                          </p>
                        ) : null}
                      </div>
                    </div>
                    <SignOutButton
                      className="h-11 w-full justify-center"
                      showLabel
                    />
                  </>
                ) : (
                  <Link
                    href="/sign-in"
                    className={cn(
                      buttonVariants({ variant: "outline", size: "sm" }),
                      "w-full justify-center",
                    )}
                    onClick={() => setMobileNavOpen(false)}
                  >
                    Sign in
                  </Link>
                )}
              </SheetFooter>
            </SheetContent>
          </Sheet>

          <div className="hidden items-center gap-3 lg:flex">
            {error ? (
              <span className="inline-flex items-center gap-2 text-sm font-medium text-destructive">
                <AlertCircle className="size-4" aria-hidden="true" />
                <span>Session unavailable</span>
              </span>
            ) : isPending && !user ? (
              <span
                className="size-9 animate-pulse rounded-md bg-muted"
                aria-label="Checking session"
              />
            ) : user ? (
              <DropdownMenu>
                <DropdownMenuTrigger
                  render={
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`${userLabel} account menu`}
                    />
                  }
                >
                  <Avatar>
                    <AvatarFallback>{userInitials}</AvatarFallback>
                  </Avatar>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuGroup>
                    <DropdownMenuLabel>{userLabel}</DropdownMenuLabel>
                    {user.name && user.email ? (
                      <DropdownMenuLabel className="pt-0 font-normal normal-case">
                        {user.email}
                      </DropdownMenuLabel>
                    ) : null}
                  </DropdownMenuGroup>
                  <DropdownMenuSeparator />
                  <DropdownMenuGroup>
                    <SignOutButton menuItem />
                  </DropdownMenuGroup>
                </DropdownMenuContent>
              </DropdownMenu>
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
      </div>
    </header>
  );
}

function isNavItemActive(pathname: string, href: string) {
  return href === "/dashboard" ? pathname === href : pathname === href;
}

function getInitials(label: string) {
  const initials = label
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join("");

  return initials.toUpperCase() || "A";
}

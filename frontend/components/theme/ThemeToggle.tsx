"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";

export type ThemeChoice = "system" | "light" | "dark";

function subscribeToHydration() {
  return () => {};
}

function getClientHydrationSnapshot() {
  return true;
}

function getServerHydrationSnapshot() {
  return false;
}

function useIsHydrated() {
  return useSyncExternalStore(
    subscribeToHydration,
    getClientHydrationSnapshot,
    getServerHydrationSnapshot,
  );
}

export function getNextTheme(theme: string | undefined): ThemeChoice {
  if (theme === "light") {
    return "dark";
  }

  if (theme === "dark") {
    return "system";
  }

  return "light";
}

export function getThemeLabel(theme: string | undefined) {
  if (theme === "light") {
    return "Light theme";
  }

  if (theme === "dark") {
    return "Dark theme";
  }

  return "System theme";
}

export function ThemeToggle() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const mounted = useIsHydrated();

  if (!mounted) {
    return (
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        disabled
        aria-label="Theme preference loading"
      >
        <Monitor className="size-4" aria-hidden="true" />
      </Button>
    );
  }

  const nextTheme = getNextTheme(theme);
  const Icon =
    theme === "system" ? Monitor : resolvedTheme === "dark" ? Moon : Sun;
  const label = `${getThemeLabel(theme)}. Switch to ${getThemeLabel(nextTheme).toLowerCase()}.`;

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      aria-label={label}
      title={label}
      onClick={() => setTheme(nextTheme)}
    >
      <Icon className="size-4" aria-hidden="true" />
    </Button>
  );
}

import type { ReactNode } from "react";

import { MainNav } from "@/components/navigation/MainNav";

export function AppShell({
  children,
  user,
}: Readonly<{
  children: ReactNode;
  user?: {
    name?: string | null;
    email?: string | null;
  } | null;
}>) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <MainNav initialUser={user} />
      <main>{children}</main>
    </div>
  );
}

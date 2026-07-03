import type { ReactNode } from "react";

import { MainNav } from "@/components/navigation/MainNav";

export function AppShell({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <MainNav />
      <main>{children}</main>
    </div>
  );
}

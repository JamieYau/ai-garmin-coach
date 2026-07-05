import type { ReactNode } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { requireCurrentSession } from "@/lib/auth/server";

export default async function AuthenticatedAppLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  const session = await requireCurrentSession();

  return <AppShell user={session.user}>{children}</AppShell>;
}

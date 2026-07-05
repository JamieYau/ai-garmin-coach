import "server-only";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

export { auth } from "@/lib/auth/config";
export type { AuthSession } from "@/lib/auth/config";

import { auth } from "@/lib/auth/config";

export async function getCurrentSession() {
  return auth.api.getSession({
    headers: await headers(),
  });
}

export async function requireCurrentSession() {
  const session = await getCurrentSession();

  if (!session) {
    redirect("/sign-in?callbackUrl=/dashboard");
  }

  return session;
}

"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { authClient } from "@/lib/auth/client";

export function SignOutButton({
  menuItem = false,
}: Readonly<{
  menuItem?: boolean;
}>) {
  const router = useRouter();
  const signOut = () => {
    void authClient.signOut({
      fetchOptions: {
        onSuccess: () => {
          router.push("/sign-in");
          router.refresh();
        },
      },
    });
  };

  if (menuItem) {
    return (
      <DropdownMenuItem onClick={signOut} variant="destructive">
        <LogOut aria-hidden="true" />
        Sign out
      </DropdownMenuItem>
    );
  }

  return (
    <Button type="button" variant="outline" size="sm" onClick={signOut}>
      <LogOut className="size-4" aria-hidden />
      <span className="hidden sm:inline">Sign out</span>
    </Button>
  );
}

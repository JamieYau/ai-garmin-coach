"use client";

import { useState, type SubmitEvent } from "react";
import { AlertCircle, LogIn, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { authClient } from "@/lib/auth/client";

type AuthMode = "sign-in" | "sign-up";

export function AuthForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mode, setMode] = useState<AuthMode>("sign-in");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const callbackUrl = searchParams.get("callbackUrl") || "/dashboard";
  const isSignUp = mode === "sign-up";
  const Icon = isSignUp ? UserPlus : LogIn;

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") ?? "");
    const password = String(formData.get("password") ?? "");
    const name = String(formData.get("name") ?? "");

    const result = isSignUp
      ? await authClient.signUp.email({
          email,
          password,
          name,
          callbackURL: callbackUrl,
        })
      : await authClient.signIn.email({
          email,
          password,
          callbackURL: callbackUrl,
        });

    if (result.error) {
      setError(result.error.message || "Authentication failed.");
      setIsSubmitting(false);
      return;
    }

    router.push(callbackUrl);
    router.refresh();
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="border-b border-border">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-2xl">
              {isSignUp ? "Create account" : "Sign in"}
            </CardTitle>
            <CardDescription className="mt-1">
              {isSignUp
                ? "Start a local development account."
                : "Use your local development account."}
            </CardDescription>
          </div>
          <Icon className="size-5 text-muted-foreground" aria-hidden />
        </div>
      </CardHeader>

      <CardContent className="pt-5">
        <Tabs
          value={mode}
          onValueChange={(value) => {
            setMode(value as AuthMode);
            setError(null);
          }}
        >
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="sign-in">Sign in</TabsTrigger>
            <TabsTrigger value="sign-up">Sign up</TabsTrigger>
          </TabsList>
        </Tabs>

        <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
          {isSignUp ? (
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                required
              />
            </div>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              name="password"
              type="password"
              autoComplete={isSignUp ? "new-password" : "current-password"}
              minLength={8}
              required
            />
          </div>

          {error ? (
            <Alert variant="destructive">
              <AlertCircle className="size-4" aria-hidden />
              <AlertTitle>Authentication failed</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <Button
            type="submit"
            size="lg"
            className="w-full"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? "Working..."
              : isSignUp
                ? "Create account"
                : "Sign in"}
          </Button>
        </form>
      </CardContent>

      <CardFooter className="justify-center border-t border-border pt-4 text-sm text-muted-foreground">
        <Link href="/" className="font-medium text-foreground hover:underline">
          Back to home
        </Link>
      </CardFooter>
    </Card>
  );
}

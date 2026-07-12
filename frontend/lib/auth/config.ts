import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { loadEnvConfig } from "@next/env";
import { existsSync } from "node:fs";
import path from "node:path";
import { Pool } from "pg";

import { getCrossSubdomainCookieDomain } from "@/lib/auth/cookie-domain";

const rootEnvDir = path.resolve(process.cwd(), "..");
const envDir = existsSync(path.join(rootEnvDir, ".env"))
  ? rootEnvDir
  : process.cwd();

loadEnvConfig(envDir, undefined, console, true);

function getDatabaseUrl() {
  const databaseUrl =
    process.env.BETTER_AUTH_DATABASE_URL ?? process.env.DATABASE_URL;

  return databaseUrl?.replace("postgresql+psycopg://", "postgresql://");
}

const globalForAuth = globalThis as typeof globalThis & {
  betterAuthPgPool?: Pool;
};

const pool =
  globalForAuth.betterAuthPgPool ??
  new Pool({
    connectionString: getDatabaseUrl(),
  });

if (process.env.NODE_ENV !== "production") {
  globalForAuth.betterAuthPgPool = pool;
}

const trustedOrigins = [
  process.env.BETTER_AUTH_URL,
  process.env.FRONTEND_URL,
].filter((origin): origin is string => Boolean(origin));

const isProduction = process.env.NODE_ENV === "production";
const useSecureCookies =
  process.env.BETTER_AUTH_SECURE_COOKIES === "true" ||
  (process.env.BETTER_AUTH_SECURE_COOKIES !== "false" && isProduction);
const rateLimitEnabled =
  process.env.BETTER_AUTH_RATE_LIMIT_ENABLED === "true" ||
  (process.env.BETTER_AUTH_RATE_LIMIT_ENABLED !== "false" && isProduction);
const crossSubdomainCookieDomain = getCrossSubdomainCookieDomain(
  process.env.BETTER_AUTH_URL,
  process.env.BETTER_AUTH_COOKIE_DOMAIN,
);

export const auth = betterAuth({
  appName: "AI Garmin Coach",
  baseURL: process.env.BETTER_AUTH_URL,
  secret: process.env.BETTER_AUTH_SECRET,
  database: pool,
  trustedOrigins,
  advanced: {
    useSecureCookies,
    disableCSRFCheck: false,
    disableOriginCheck: false,
    defaultCookieAttributes: {
      httpOnly: true,
      sameSite: "lax",
      secure: useSecureCookies,
    },
    ...(crossSubdomainCookieDomain
      ? {
          crossSubDomainCookies: {
            enabled: true,
            domain: crossSubdomainCookieDomain,
          },
        }
      : {}),
  },
  rateLimit: {
    enabled: rateLimitEnabled,
    window: Number(process.env.BETTER_AUTH_RATE_LIMIT_WINDOW_SECONDS ?? 60),
    max: Number(process.env.BETTER_AUTH_RATE_LIMIT_MAX_REQUESTS ?? 20),
  },
  emailAndPassword: {
    enabled: true,
  },
  plugins: [nextCookies()],
});

export type AuthSession = typeof auth.$Infer.Session;

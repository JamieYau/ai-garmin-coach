import { betterAuth } from "better-auth";
import { nextCookies } from "better-auth/next-js";
import { loadEnvConfig } from "@next/env";
import path from "node:path";
import { Pool } from "pg";

loadEnvConfig(process.cwd());
loadEnvConfig(path.resolve(process.cwd(), ".."));

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

export const auth = betterAuth({
  appName: "AI Garmin Coach",
  baseURL: process.env.BETTER_AUTH_URL,
  secret: process.env.BETTER_AUTH_SECRET,
  database: pool,
  trustedOrigins,
  emailAndPassword: {
    enabled: true,
  },
  plugins: [nextCookies()],
});

export type AuthSession = typeof auth.$Infer.Session;

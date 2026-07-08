import nextEnv from "@next/env";
import { hashPassword } from "better-auth/crypto";
import { existsSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import pg from "pg";

const { Pool } = pg;
const { loadEnvConfig } = nextEnv;

export const DEMO_USER_ID = "demo-user-ai-garmin-coach";
export const DEMO_APP_USER_ID = "11111111-1111-4111-8111-111111111111";
export const DEMO_CONNECTION_ID = "22222222-2222-4222-8222-222222222222";
export const DEMO_SYNC_RUN_ID = "33333333-3333-4333-8333-333333333333";

const DEFAULT_EMAIL = "demo@example.test";
const DEFAULT_PASSWORD = "demo-password-local-only";
const DEFAULT_NAME = "Demo Runner";

function loadProjectEnv() {
  const cwd = process.cwd();
  const rootEnvDir = path.resolve(cwd, "..");
  const envDir = existsSync(path.join(rootEnvDir, ".env")) ? rootEnvDir : cwd;

  loadEnvConfig(envDir, undefined, console, true);
}

function getDatabaseUrl() {
  const databaseUrl =
    process.env.BETTER_AUTH_DATABASE_URL ?? process.env.DATABASE_URL;

  if (!databaseUrl) {
    throw new Error(
      "Set BETTER_AUTH_DATABASE_URL or DATABASE_URL before running demo:seed.",
    );
  }

  return databaseUrl.replace("postgresql+psycopg://", "postgresql://");
}

function assertLocalEnvironment() {
  const appEnv = process.env.APP_ENV;
  const nodeEnv = process.env.NODE_ENV;

  if (
    process.env.DEMO_SEED_ALLOW_PRODUCTION !== "true" &&
    (appEnv === "production" || nodeEnv === "production")
  ) {
    throw new Error("Refusing to seed demo data in production.");
  }
}

function isoDate(offsetDays = 0) {
  const date = new Date();
  date.setUTCHours(12, 0, 0, 0);
  date.setUTCDate(date.getUTCDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

function isoDateTime(offsetDays, hour, minute = 0) {
  const date = new Date(`${isoDate(offsetDays)}T00:00:00.000Z`);
  date.setUTCHours(hour, minute, 0, 0);
  return date.toISOString();
}

export function buildDemoDataset() {
  const activities = [
    {
      id: "44444444-4444-4444-8444-444444444401",
      sourceActivityId: "demo-run-aerobic",
      type: "running",
      name: "Morning aerobic run",
      dayOffset: 0,
      startHour: 6,
      startMinute: 35,
      durationSeconds: 2760,
      movingDurationSeconds: 2700,
      distanceMeters: "9100.00",
      calories: 682,
      activeCalories: 610,
      averageHeartRate: 142,
      maxHeartRate: 166,
      elevationGainMeters: "78.00",
      trainingLoad: "82.40",
    },
    {
      id: "44444444-4444-4444-8444-444444444402",
      sourceActivityId: "demo-ride-endurance",
      type: "cycling",
      name: "Endurance ride",
      dayOffset: -2,
      startHour: 17,
      startMinute: 20,
      durationSeconds: 4380,
      movingDurationSeconds: 4200,
      distanceMeters: "31200.00",
      calories: 760,
      activeCalories: 690,
      averageHeartRate: 124,
      maxHeartRate: 151,
      elevationGainMeters: "220.00",
      trainingLoad: "66.20",
    },
    {
      id: "44444444-4444-4444-8444-444444444403",
      sourceActivityId: "demo-run-tempo",
      type: "running",
      name: "Controlled tempo",
      dayOffset: -4,
      startHour: 7,
      startMinute: 10,
      durationSeconds: 2520,
      movingDurationSeconds: 2460,
      distanceMeters: "7800.00",
      calories: 590,
      activeCalories: 540,
      averageHeartRate: 153,
      maxHeartRate: 174,
      elevationGainMeters: "42.00",
      trainingLoad: "91.70",
    },
    {
      id: "44444444-4444-4444-8444-444444444404",
      sourceActivityId: "demo-strength",
      type: "strength_training",
      name: "Strength maintenance",
      dayOffset: -5,
      startHour: 18,
      startMinute: 0,
      durationSeconds: 2400,
      movingDurationSeconds: null,
      distanceMeters: null,
      calories: 260,
      activeCalories: 210,
      averageHeartRate: 101,
      maxHeartRate: 136,
      elevationGainMeters: null,
      trainingLoad: "24.30",
    },
    {
      id: "44444444-4444-4444-8444-444444444405",
      sourceActivityId: "demo-run-easy",
      type: "running",
      name: "Easy recovery run",
      dayOffset: -7,
      startHour: 6,
      startMinute: 50,
      durationSeconds: 1980,
      movingDurationSeconds: 1920,
      distanceMeters: "5700.00",
      calories: 410,
      activeCalories: 370,
      averageHeartRate: 132,
      maxHeartRate: 151,
      elevationGainMeters: "24.00",
      trainingLoad: "38.10",
    },
  ];

  const dailyMetrics = Array.from({ length: 14 }, (_, index) => {
    const dayOffset = -13 + index;
    const wave = index % 5;

    return {
      id: `55555555-5555-4555-8555-${String(index + 1).padStart(12, "0")}`,
      metricDate: isoDate(dayOffset),
      steps: 7400 + index * 420 + wave * 650,
      calories: 2140 + index * 18,
      activeCalories: 420 + wave * 45,
      floorsAscended: 6 + wave,
      activeSeconds: 2600 + wave * 520,
      highlyActiveSeconds: 600 + wave * 180,
      restingHeartRate: 51 - Math.min(4, Math.floor(index / 4)),
      hrvMs: (54 + index * 0.8 + wave).toFixed(2),
      stressAverage: (31 - index * 0.45 + wave * 0.7).toFixed(2),
      bodyBatteryMin: 24 + wave,
      bodyBatteryMax: 82 + wave * 2,
      bodyBatteryLatest: 58 + index + wave,
    };
  });

  const sleepSessions = Array.from({ length: 10 }, (_, index) => {
    const dayOffset = -9 + index;
    const score = 76 + ((index * 3) % 15);
    const totalSleepSeconds = 25200 + ((index + 2) % 4) * 1800;

    return {
      id: `66666666-6666-4666-8666-${String(index + 1).padStart(12, "0")}`,
      sourceSleepId: `demo-sleep-${index + 1}`,
      sleepDate: isoDate(dayOffset),
      startedAt: isoDateTime(dayOffset - 1, 22, 25 + (index % 3) * 10),
      endedAt: isoDateTime(dayOffset, 6, 20 + (index % 4) * 8),
      totalSleepSeconds,
      deepSleepSeconds: 3900 + (index % 3) * 600,
      remSleepSeconds: 5400 + (index % 4) * 500,
      lightSleepSeconds: totalSleepSeconds - 10600,
      awakeSeconds: 1100 + (index % 3) * 240,
      sleepScore: score,
      averageSpo2: (96.4 + (index % 4) * 0.2).toFixed(2),
      averageHrvMs: (56 + index * 1.1).toFixed(2),
      averageRespiration: (13.4 + (index % 4) * 0.2).toFixed(2),
    };
  });

  return { activities, dailyMetrics, sleepSessions };
}

async function tableExists(client, tableName) {
  const result = await client.query("SELECT to_regclass($1) AS table_name", [
    tableName,
  ]);
  return result.rows[0]?.table_name !== null;
}

async function ensureRequiredTables(client) {
  const requiredTables = [
    "public.user",
    "public.account",
    "public.app_users",
    "public.source_connections",
    "public.sync_runs",
    "public.activities",
    "public.daily_metrics",
    "public.sleep_sessions",
    "public.coach_insights",
  ];

  const missing = [];
  for (const tableName of requiredTables) {
    if (!(await tableExists(client, tableName))) {
      missing.push(tableName);
    }
  }

  if (missing.length) {
    throw new Error(
      `Missing required tables: ${missing.join(", ")}. Run backend Alembic migrations and npm run auth:migrate first.`,
    );
  }
}

async function upsertDemoAuth(client, { email, password, name }) {
  const passwordHash = await hashPassword(password);
  const now = new Date();

  await client.query(
    `
    INSERT INTO "user" ("id", "name", "email", "emailVerified", "image", "createdAt", "updatedAt")
    VALUES ($1, $2, $3, true, NULL, $4, $4)
    ON CONFLICT ("id") DO UPDATE SET
      "name" = EXCLUDED."name",
      "email" = EXCLUDED."email",
      "emailVerified" = true,
      "updatedAt" = EXCLUDED."updatedAt"
    `,
    [DEMO_USER_ID, name, email, now],
  );

  await client.query(
    `
    DELETE FROM "account"
    WHERE "userId" = $1 AND "providerId" = 'credential'
    `,
    [DEMO_USER_ID],
  );

  await client.query(
    `
    INSERT INTO "account" (
      "id",
      "accountId",
      "providerId",
      "userId",
      "password",
      "createdAt",
      "updatedAt"
    )
    VALUES ($1, $2, 'credential', $2, $3, $4, $4)
    `,
    [`${DEMO_USER_ID}-credential`, DEMO_USER_ID, passwordHash, now],
  );
}

async function resetDemoAppData(client) {
  await client.query(`DELETE FROM coach_insights WHERE user_id = $1`, [
    DEMO_APP_USER_ID,
  ]);
  await client.query(`DELETE FROM sleep_sessions WHERE user_id = $1`, [
    DEMO_APP_USER_ID,
  ]);
  await client.query(`DELETE FROM daily_metrics WHERE user_id = $1`, [
    DEMO_APP_USER_ID,
  ]);
  await client.query(`DELETE FROM activities WHERE user_id = $1`, [
    DEMO_APP_USER_ID,
  ]);
  await client.query(`DELETE FROM sync_runs WHERE user_id = $1`, [
    DEMO_APP_USER_ID,
  ]);
  await client.query(`DELETE FROM source_connections WHERE user_id = $1`, [
    DEMO_APP_USER_ID,
  ]);
}

async function seedAppUserAndConnection(client, { email, name }) {
  const now = new Date();

  await client.query(
    `
    INSERT INTO app_users (
      id,
      better_auth_user_id,
      email,
      display_name,
      timezone,
      created_at,
      updated_at
    )
    VALUES ($1, $2, $3, $4, 'Europe/London', $5, $5)
    ON CONFLICT (id) DO UPDATE SET
      better_auth_user_id = EXCLUDED.better_auth_user_id,
      email = EXCLUDED.email,
      display_name = EXCLUDED.display_name,
      updated_at = EXCLUDED.updated_at
    `,
    [DEMO_APP_USER_ID, DEMO_USER_ID, email, name, now],
  );

  await client.query(
    `
    INSERT INTO source_connections (
      id,
      user_id,
      source,
      status,
      provider_subject_id,
      display_name,
      metadata,
      last_sync_at,
      created_at,
      updated_at
    )
    VALUES ($1, $2, 'garmin', 'active', 'demo-garmin-user', 'Demo Garmin', $3, $4, $4, $4)
    `,
    [
      DEMO_CONNECTION_ID,
      DEMO_APP_USER_ID,
      JSON.stringify({ demo: true, credentials_required: false }),
      now,
    ],
  );

  await client.query(
    `
    INSERT INTO sync_runs (
      id,
      user_id,
      source_connection_id,
      status,
      sync_type,
      started_at,
      completed_at,
      window_start,
      window_end,
      records_seen,
      records_imported,
      error_code,
      error_message,
      created_at,
      updated_at
    )
    VALUES ($1, $2, $3, 'succeeded', 'backfill', $4, $4, $5, $4, 30, 30, NULL, NULL, $4, $4)
    `,
    [
      DEMO_SYNC_RUN_ID,
      DEMO_APP_USER_ID,
      DEMO_CONNECTION_ID,
      now,
      isoDateTime(-13, 0),
    ],
  );
}

async function seedActivities(client, activities) {
  for (const activity of activities) {
    const startedAt = isoDateTime(
      activity.dayOffset,
      activity.startHour,
      activity.startMinute,
    );
    const endedAt = new Date(
      new Date(startedAt).getTime() + activity.durationSeconds * 1000,
    ).toISOString();

    await client.query(
      `
      INSERT INTO activities (
        id,
        user_id,
        source_connection_id,
        source_activity_id,
        activity_type,
        name,
        activity_date,
        started_at,
        ended_at,
        duration_seconds,
        moving_duration_seconds,
        distance_meters,
        calories,
        active_calories,
        average_heart_rate,
        max_heart_rate,
        elevation_gain_meters,
        training_load,
        raw_data,
        created_at,
        updated_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, NOW(), NOW())
      `,
      [
        activity.id,
        DEMO_APP_USER_ID,
        DEMO_CONNECTION_ID,
        activity.sourceActivityId,
        activity.type,
        activity.name,
        isoDate(activity.dayOffset),
        startedAt,
        endedAt,
        activity.durationSeconds,
        activity.movingDurationSeconds,
        activity.distanceMeters,
        activity.calories,
        activity.activeCalories,
        activity.averageHeartRate,
        activity.maxHeartRate,
        activity.elevationGainMeters,
        activity.trainingLoad,
        JSON.stringify({
          demo: true,
          source_activity_id: activity.sourceActivityId,
        }),
      ],
    );
  }
}

async function seedDailyMetrics(client, dailyMetrics) {
  for (const metric of dailyMetrics) {
    await client.query(
      `
      INSERT INTO daily_metrics (
        id,
        user_id,
        source_connection_id,
        metric_date,
        steps,
        calories,
        active_calories,
        floors_ascended,
        active_seconds,
        highly_active_seconds,
        resting_heart_rate,
        hrv_ms,
        stress_average,
        body_battery_min,
        body_battery_max,
        body_battery_latest,
        raw_data,
        created_at,
        updated_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, NOW(), NOW())
      `,
      [
        metric.id,
        DEMO_APP_USER_ID,
        DEMO_CONNECTION_ID,
        metric.metricDate,
        metric.steps,
        metric.calories,
        metric.activeCalories,
        metric.floorsAscended,
        metric.activeSeconds,
        metric.highlyActiveSeconds,
        metric.restingHeartRate,
        metric.hrvMs,
        metric.stressAverage,
        metric.bodyBatteryMin,
        metric.bodyBatteryMax,
        metric.bodyBatteryLatest,
        JSON.stringify({ demo: true, metric_date: metric.metricDate }),
      ],
    );
  }
}

async function seedSleepSessions(client, sleepSessions) {
  for (const sleep of sleepSessions) {
    await client.query(
      `
      INSERT INTO sleep_sessions (
        id,
        user_id,
        source_connection_id,
        source_sleep_id,
        sleep_date,
        started_at,
        ended_at,
        total_sleep_seconds,
        deep_sleep_seconds,
        rem_sleep_seconds,
        light_sleep_seconds,
        awake_seconds,
        sleep_score,
        average_spo2,
        average_hrv_ms,
        average_respiration,
        raw_data,
        created_at,
        updated_at
      )
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, NOW(), NOW())
      `,
      [
        sleep.id,
        DEMO_APP_USER_ID,
        DEMO_CONNECTION_ID,
        sleep.sourceSleepId,
        sleep.sleepDate,
        sleep.startedAt,
        sleep.endedAt,
        sleep.totalSleepSeconds,
        sleep.deepSleepSeconds,
        sleep.remSleepSeconds,
        sleep.lightSleepSeconds,
        sleep.awakeSeconds,
        sleep.sleepScore,
        sleep.averageSpo2,
        sleep.averageHrvMs,
        sleep.averageRespiration,
        JSON.stringify({ demo: true, source_sleep_id: sleep.sourceSleepId }),
      ],
    );
  }
}

async function seedCoachInsight(client) {
  const insightDate = isoDate(0);
  const generatedAt = isoDateTime(0, 9, 15);

  await client.query(
    `
    INSERT INTO coach_insights (
      id,
      user_id,
      source_sync_run_id,
      insight_date,
      insight_type,
      title,
      summary,
      recommendation,
      schema_version,
      model_provider,
      model_name,
      prompt_version,
      input_fingerprint,
      output,
      generated_at,
      created_at,
      updated_at
    )
    VALUES ($1, $2, $3, $4, 'daily', $5, $6, $7, 'v1', 'mock', 'demo-coach', 'demo-v1', $8, $9, $10, NOW(), NOW())
    `,
    [
      "77777777-7777-4777-8777-777777777777",
      DEMO_APP_USER_ID,
      DEMO_SYNC_RUN_ID,
      insightDate,
      "Keep aerobic volume steady",
      "Recent training is consistent, sleep quality is stable, and recovery markers support a controlled aerobic session.",
      "Keep the next workout easy to moderate, avoid stacking intensity, and use the following day for recovery if resting heart rate rises.",
      `demo-${insightDate}`,
      JSON.stringify({
        readiness: "good",
        focus: "aerobic_consistency",
        risk_flags: [],
      }),
      generatedAt,
    ],
  );
}

export async function seedDemoData() {
  loadProjectEnv();
  assertLocalEnvironment();

  const email = process.env.DEMO_USER_EMAIL ?? DEFAULT_EMAIL;
  const password = process.env.DEMO_USER_PASSWORD ?? DEFAULT_PASSWORD;
  const name = process.env.DEMO_USER_NAME ?? DEFAULT_NAME;
  const dataset = buildDemoDataset();

  const pool = new Pool({ connectionString: getDatabaseUrl() });
  const client = await pool.connect();

  try {
    await client.query("BEGIN");
    await ensureRequiredTables(client);
    await upsertDemoAuth(client, { email, password, name });
    await resetDemoAppData(client);
    await seedAppUserAndConnection(client, { email, name });
    await seedActivities(client, dataset.activities);
    await seedDailyMetrics(client, dataset.dailyMetrics);
    await seedSleepSessions(client, dataset.sleepSessions);
    await seedCoachInsight(client);
    await client.query("COMMIT");

    return {
      email,
      password,
      activities: dataset.activities.length,
      dailyMetrics: dataset.dailyMetrics.length,
      sleepSessions: dataset.sleepSessions.length,
    };
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

async function main() {
  const result = await seedDemoData();

  console.log("Seeded local demo account and dashboard data.");
  console.log(`Email: ${result.email}`);
  console.log(`Password: ${result.password}`);
  console.log(
    `Records: ${result.activities} activities, ${result.dailyMetrics} daily metrics, ${result.sleepSessions} sleep sessions.`,
  );
}

const executedPath = process.argv[1]
  ? pathToFileURL(path.resolve(process.argv[1])).href
  : null;

if (import.meta.url === executedPath) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  });
}

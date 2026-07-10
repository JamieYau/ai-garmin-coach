# Security Notes

This document describes the MVP security model and data-handling posture for
AI Garmin Coach. Treat it as developer-facing guidance, not a public privacy
policy.

## Security Model

The application is split between a Next.js frontend, a FastAPI backend, and a
PostgreSQL database. The frontend owns interactive authentication through Better
Auth, while FastAPI validates browser requests against Better Auth session data
before touching user-owned Garmin records.

Security boundaries in the MVP:

- Browser API requests must carry a valid Better Auth session.
- FastAPI route handlers scope user-owned reads and writes to the authenticated
  `app_users` record.
- Garmin connector code runs behind service modules instead of directly inside
  route handlers.
- Provider session material is encrypted before persistence.
- Logs must use sanitized IDs, statuses, counts, and error codes rather than raw
  health data, credentials, prompts, or model outputs.
- AI coach output is structured JSON validated by Pydantic; free-form chat is
  outside MVP scope.

The MVP does not yet include organization-level access control, multi-user
sharing, admin impersonation, or cross-account data export.

## Auth Boundary

The Next.js frontend owns interactive authentication through Better Auth. FastAPI treats the Better Auth session cookie as the browser authorization boundary and validates it against the shared Better Auth database before creating or updating the local `app_users` profile.

## CORS

FastAPI only accepts browser credentials from the configured `BACKEND_CORS_ORIGINS` allowlist. Local development defaults to `http://localhost:3000`; production must set this to the deployed frontend origin. Because browser API calls use cookies, `BACKEND_CORS_ALLOW_CREDENTIALS` stays enabled and wildcard origins must not be used in production.

## Cookies

Better Auth uses HTTP-only, `SameSite=Lax` cookies. Production should set `BETTER_AUTH_URL` to an `https://` URL and leave `BETTER_AUTH_SECURE_COOKIES` enabled so cookies include the `Secure` attribute. Local development may set `BETTER_AUTH_SECURE_COOKIES=false` for `http://localhost`.

## CSRF Posture

CSRF checks are intentionally enabled in Better Auth. The app keeps origin validation and fetch metadata checks active, and trusted origins are limited to `BETTER_AUTH_URL` and `FRONTEND_URL`. FastAPI routes should avoid state-changing GET endpoints and should continue to require a valid Better Auth session for user-owned data.

## Rate Limiting

Better Auth rate limiting is configured through `BETTER_AUTH_RATE_LIMIT_ENABLED`, `BETTER_AUTH_RATE_LIMIT_WINDOW_SECONDS`, and `BETTER_AUTH_RATE_LIMIT_MAX_REQUESTS`. It defaults on in production and off in local development. Before public launch, add infrastructure-level rate limits for `/api/auth/*` and any FastAPI endpoints that trigger Garmin login, sync, or AI generation.

FastAPI also applies process-local fixed-window rate limits to Garmin connection attempts, manual sync requests, and the planned AI insight generation route. Configure these with `RATE_LIMIT_ENABLED`, `GARMIN_CONNECTION_RATE_LIMIT_*`, `MANUAL_SYNC_RATE_LIMIT_*`, and `AI_INSIGHT_RATE_LIMIT_*`. This is baseline MVP abuse protection; horizontally scaled production deployments should enforce the same limits at the edge or through shared infrastructure.

## Request Tracing

FastAPI adds an `X-Request-ID` response header to every request. If the client sends a non-empty `X-Request-ID` up to 128 characters, the backend preserves it; otherwise it generates a UUID. Use this ID for correlating sanitized logs and client-visible failures.

## Sensitive Material

Garmin session material is stored inside `source_connections.metadata.session_material` as a versioned encrypted envelope. The current MVP encryption strategy uses Fernet with key material derived from `BETTER_AUTH_SECRET`; production deployments must provide a long, randomly generated secret and rotate it through a planned migration because existing connection material depends on it.

Backend logs use JSON formatting with recursive redaction for sensitive field names such as passwords, tokens, API keys, cookies, prompts, raw payloads, and Garmin session material. Log messages should still be written as structured fields rather than interpolated secrets; redaction is a guardrail, not permission to log raw health data or provider credentials.

## Data Stored

The backend stores the minimum records needed for Garmin sync, dashboard views,
and daily coaching insights:

- Local app user profile: Better Auth user ID, email, display name, timezone,
  and timestamps.
- Source connection metadata: source name, status, provider subject ID, display
  name, region, hashed Garmin username, and encrypted Garmin tokenstore/session
  material.
- Sync metadata: sync status, type, source connection, sync windows, record
  counts, sanitized error code/message, and timestamps.
- Canonical fitness records: normalized activities, daily metrics, sleep
  sessions, and biometric samples.
- Raw provider snapshots: Garmin payload snapshots linked to the user, source
  connection, sync run, provider object type, provider object ID, and payload
  hash.
- AI coach insights: structured title, summary, recommendation, schema version,
  model metadata, prompt version, input fingerprint, output JSON, and generated
  timestamp.
- Better Auth tables in the shared database: users, sessions, and related auth
  metadata managed by Better Auth.

Raw provider payload snapshots and canonical record `raw_data` fields may
contain health and fitness details from Garmin. Treat both as sensitive user
data even when they do not contain credentials.

## Data Not Stored

The MVP intentionally avoids storing these values:

- Garmin account password after connection setup.
- MFA codes after the current connection request completes.
- Plaintext Garmin tokenstore/session material.
- Plaintext OpenAI API keys in the database.
- Raw prompts, full model outputs, Garmin credentials, or raw health payloads in
  application logs.
- User-written chat history; chat is not part of the MVP.
- Nutrition, mood, habit, calendar, location timeline, or contact data unless a
  future roadmap phase adds a connector and database model for it.

Environment variables and local `.env` files may still contain secrets such as
`BETTER_AUTH_SECRET`, `DATABASE_URL`, Garmin local test credentials, and
`OPENAI_API_KEY`. Keep those files ignored and out of commits.

## User Data Lifecycle

Users can disconnect Garmin and remove locally stored user-owned data through
FastAPI routes:

- `DELETE /connections/garmin` marks the Garmin source connection as
  `disconnected` and removes stored Garmin session material from connection
  metadata. Future manual or scheduled syncs should skip disconnected sources.
- `DELETE /users/me/data?source=garmin` deletes the current user's synced Garmin
  records, raw observations, sync runs, and linked coach insights while keeping
  the source connection row.
- `DELETE /users/me` deletes the current user's local app profile, source
  connections, synced data, raw observations, sync runs, and coach insights.

These routes remove data from the app database. They do not delete the user's
Garmin account, remove data from Garmin, or revoke any external provider-side
permission outside the app's stored session material.

## Garmin API Limitations

The Garmin connector uses `python-garminconnect`, which wraps Garmin Connect
behavior rather than a formal public OAuth API for this app. Known MVP
limitations:

- Garmin login can require MFA and may fail when Garmin changes web flows,
  rate-limits requests, or invalidates sessions.
- Sync availability and field names can vary by account, device, locale, region,
  and Garmin product changes.
- Historical backfills are intentionally bounded to avoid excessive provider
  requests.
- The app stores normalized records and raw snapshots from successful syncs; it
  cannot guarantee Garmin has every metric for every day.
- Disconnecting in this app clears local session material but does not perform a
  provider-side revocation call.
- Garmin health data is personal and may be incomplete or delayed; coach
  insights must remain conservative and non-medical.

## Production Checklist

Before public launch, revisit these items:

- Move rate limits to shared edge or infrastructure controls for horizontally
  scaled deployments.
- Define a secret rotation procedure for `BETTER_AUTH_SECRET` because it derives
  current encrypted Garmin session material keys.
- Add automated secret scanning in CI.
- Review database backup retention and deletion guarantees.
- Review provider terms, consent language, and user-facing privacy disclosures.

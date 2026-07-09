# Security Notes

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

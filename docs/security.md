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

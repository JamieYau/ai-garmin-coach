# Background Job Approach

## Decision

For the MVP, use a simple scheduled backend process that runs the same tested sync and coach services as the API. The process should be started separately from the FastAPI web server in development and deployment, with one active instance responsible for scheduled work.

Production should use Azure Container Apps Jobs for scheduled execution once the app is deployed to Azure. The initial implementation should keep the runner portable so the same command can run locally, in CI smoke checks, or inside an Azure job container.

## Options Compared

| Option | Fit For MVP | Strengths | Tradeoffs |
| --- | --- | --- | --- |
| Simple scheduled process | Best initial choice | Easy to understand, no extra infrastructure, can reuse FastAPI settings and SQLAlchemy services, works locally with `uv run` | Needs deployment discipline to avoid duplicate schedulers, limited retry orchestration, not ideal for high-throughput queues |
| FastAPI background task | Poor fit for scheduled sync | Convenient for short request-adjacent work after an authenticated API call | Tied to web requests and web process lifetime, unsuitable for recurring jobs, can be interrupted by restarts, risks making sync behavior depend on API traffic |
| Redis-backed worker | Defer | Durable queue semantics, clearer retries, concurrency controls, useful if sync or AI jobs become long-running or numerous | Adds Redis, worker deployment, queue monitoring, and more failure modes before the MVP needs them |
| Azure Container Apps Job | Production path | Native scheduled container execution, separated from the web API, integrates with Azure deployment model, avoids running a scheduler in every web replica | Azure-specific, still needs idempotent job code and database-level protection against duplicate work |

## Initial Design

- Add a backend job module under `backend/app/jobs/` that exposes explicit commands for scheduled sync and daily insight generation.
- Keep business logic in services such as `backend/app/services/sync.py` and `backend/app/services/coach.py`; job modules should orchestrate, not normalize Garmin payloads or generate coach text directly.
- Run manual sync through a protected FastAPI endpoint, but do not rely on FastAPI background tasks for recurring scheduled sync.
- Record every sync attempt in `sync_runs` with `queued`, `running`, `succeeded`, or `failed` status, window bounds, counts, and sanitized error codes.
- Make scheduled work bounded by the existing incremental sync window and backfill limits.
- Generate daily coach insights only after a successful sync or when explicitly run against already available fresh data.
- Treat Garmin credentials, provider tokens, prompts, model outputs, and raw health data as sensitive; job logs must only include stable IDs, counts, statuses, and sanitized error codes.

## Production Path

The Azure deployment should run the API and scheduled worker as separate containers:

- FastAPI Container App: serves browser API requests and manual sync triggers.
- Scheduled Azure Container Apps Job: runs the scheduled sync command on a fixed cadence.
- Optional one-off Azure Container Apps Job: runs bounded backfills or maintenance tasks manually.

Before enabling more than one scheduler, add database-backed idempotency or locking around user/source sync windows so duplicate jobs cannot import the same provider window concurrently.

## When To Revisit

Move to a Redis-backed worker only when one of these becomes true:

- Manual sync needs durable asynchronous progress after the HTTP request returns.
- Multiple job types need prioritized queues or controlled concurrency.
- Provider rate limits require centralized retry scheduling.
- Azure Container Apps Job cadence is too coarse or operationally awkward for the desired sync frequency.

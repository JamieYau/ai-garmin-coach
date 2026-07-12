# Architecture (MVP)

## Frontend

- Next.js dashboard
- Displays metrics and AI coaching insights

## Backend

- FastAPI
- Handles Garmin integration
- Runs AI coach logic
- Exposes REST API

## Database

- PostgreSQL stores:
  - users
  - activities
  - sleep
  - daily metrics
  - AI insights

## Background Jobs

- MVP decision: use a simple scheduled backend process for local and early development jobs.
- Production path: run scheduled sync and daily insight generation as Azure Container Apps Jobs, separate from the FastAPI web container.
- Avoid FastAPI background tasks for recurring scheduled sync; reserve request-bound work for short, non-critical follow-up only.
- Defer Redis-backed workers until the app needs durable queues, job priorities, or centralized retry scheduling.
- Keep job modules thin: orchestrate tested sync and coach services, write `sync_runs`, and emit only sanitized IDs, counts, statuses, and error codes.

## Production Deployment

- Deploy the Next.js frontend and FastAPI backend as separate Azure Container
  Apps in one consumption environment; both are external HTTPS services and
  scale to zero for the MVP.
- Run the existing scheduled sync command as a separate Azure Container Apps
  Job once daily. It has no ingress and must remain single-execution until
  database-backed scheduler locking exists.
- Use one private-access Azure Database for PostgreSQL Flexible Server shared by
  the application, Better Auth, and Alembic migrations. Do not expose the
  database publicly.
- Store runtime secrets in Azure Key Vault and authorize the Container Apps with
  managed identities. GitHub deployment automation will use OIDC federation,
  not an Azure client secret.
- Use Azure Container Registry for versioned images and Log Analytics for
  sanitized platform/application logs. Application Insights is deferred until
  its additional telemetry is needed.
- The initial deployment intentionally excludes Redis, Azure OpenAI,
  geo-replication, high availability, and a WAF; the full resource decisions
  and cost guardrails are documented in `docs/deployment.md`.

## AI System

- structured JSON outputs only
- no chat in MVP


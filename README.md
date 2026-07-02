# AI Garmin Coach

An AI-powered coaching dashboard that ingests Garmin fitness data and generates personalised training and recovery insights.

## Product Scope

The MVP connects a user's Garmin data, stores normalized training and recovery records, and presents a dashboard with structured AI coaching insights. The first working slice should prioritize Garmin ingestion, dashboard metrics, and daily coach recommendations over broad connector or chat features.

## Stack
- Frontend: Next.js App Router, TypeScript, Tailwind, shadcn/ui or Radix, TanStack Query
- Backend: FastAPI, Pydantic, SQLAlchemy 2.0, Alembic
- Database: PostgreSQL
- Auth: Better Auth for your app users
- Garmin integration: python-garminconnect

## Repository Layout

- `frontend/`: Next.js App Router application.
- `backend/`: FastAPI service, Pydantic schemas, SQLAlchemy models, Garmin integration, and coach logic.
- `backend/alembic/`: database migrations.
- `docs/`: longer design notes and architecture decision records.
- `.github/workflows/`: CI/CD workflow definitions.

## Local Services

| Service | Local name | Port | URL |
| --- | --- | --- | --- |
| Frontend | `garmin-coach-frontend` | `3000` | `http://localhost:3000` |
| Backend API | `garmin-coach-api` | `8000` | `http://localhost:8000` |
| PostgreSQL | `garmin-coach-postgres` | `5432` | `postgresql://localhost:5432/garmin_coach` |

## Environment

Copy `.env.example` to `.env` for local development and replace placeholder values with local-only secrets. Do not commit `.env` files, Garmin credentials, database URLs with real passwords, auth secrets, or model API keys.

Required variables are grouped in `.env.example`:

- App runtime: `APP_ENV`, `LOG_LEVEL`.
- Local ports and URLs: `FRONTEND_PORT`, `BACKEND_PORT`, `POSTGRES_PORT`, `FRONTEND_URL`, `NEXT_PUBLIC_API_BASE_URL`, `BACKEND_CORS_ORIGINS`.
- PostgreSQL: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`.
- Auth: `BETTER_AUTH_URL`, `BETTER_AUTH_SECRET`.
- AI provider: `AI_PROVIDER`, `OPENAI_API_KEY`.
- Garmin local setup: `GARMIN_USERNAME`, `GARMIN_PASSWORD`.

## Development Commands

Backend commands are available from `backend/` after installing `uv`:

```bash
cd backend
uv sync --dev
uv run uvicorn app.main:app --reload
uv run pytest
uv run ruff check
uv run mypy app
```

Once Alembic migrations exist, apply them with:

```bash
cd backend
uv run alembic upgrade head
```

Frontend commands will be added when the Next.js scaffold lands in Phase 2.

## Status
MVP in development

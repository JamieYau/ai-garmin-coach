# AI Garmin Coach

An AI-powered coaching dashboard that ingests Garmin fitness data and generates personalised training and recovery insights.

## Product Scope

The MVP connects a user's Garmin data, stores normalized training and recovery records, and presents a dashboard with structured AI coaching insights. The first working slice should prioritize Garmin ingestion, dashboard metrics, and daily coach recommendations over broad connector or chat features.

## Stack
- Frontend: Next.js App Router, TypeScript, Tailwind, shadcn/ui or Radix, TanStack Query
- Backend: FastAPI, Pydantic, SQLAlchemy 2.0, Alembic
- Database: PostgreSQL
- Auth: Better Auth
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
- Better Auth database: `BETTER_AUTH_DATABASE_URL`.
- AI provider: `AI_PROVIDER`, `OPENAI_API_KEY`.
- Garmin local setup: `GARMIN_USERNAME`, `GARMIN_PASSWORD`.

## Development Commands

Backend commands are available from `backend/` after installing `uv`:

```bash
cd backend
uv sync --dev
uv run python --version
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

## Database Migrations

The backend expects a native local PostgreSQL instance for development. Create a local database that matches `.env.example`, set `DATABASE_URL` in `.env`, then run Alembic through `uv` from `backend/`.

Useful commands:

```bash
cd backend
uv run alembic current
uv run alembic revision --autogenerate -m "Describe schema change"
uv run alembic upgrade head
uv run alembic downgrade -1
```

If PostgreSQL client tools are installed, verify the local service with:

```bash
pg_isready -h localhost -p 5432
```

Frontend commands are available from `frontend/`:

```bash
cd frontend
npm install
npm run dev
npm run lint
npm run lint:fix
npm run format:check
npm run format
npm run auth:generate
npm run auth:migrate
npm run typecheck
npm run test
```

For local email/password authentication, point `BETTER_AUTH_DATABASE_URL`
at the same PostgreSQL database using the standard `postgresql://` URL form,
then run `npm run auth:migrate` from `frontend/` to create Better Auth's
tables.

## API Authentication Boundary

The frontend owns interactive authentication through Better Auth. FastAPI
authorizes browser API calls by validating the signed
`better-auth.session_token` cookie against Better Auth's shared PostgreSQL
`session` table and joining it to the Better Auth `user` table.

Local development flow:

```bash
cd frontend
npm run auth:migrate
npm run dev
```

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Use the same `DATABASE_URL`/`BETTER_AUTH_DATABASE_URL` target and
`BETTER_AUTH_SECRET` for both services. Protected FastAPI routes should depend
on `get_current_app_user` or `get_current_user` from
`backend/app/api/dependencies.py`; the dependency creates or updates the local
`app_users` profile from the Better Auth user record and then scopes API work
to that local user.

## Status
MVP in development

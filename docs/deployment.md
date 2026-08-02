# Azure MVP Deployment Plan

## Scope and Status

This document defines the target Azure production topology for the MVP. Phase
12.2 supplies reproducible Bicep definitions for the platform baseline; it does
not provision the subscription or enable automatic deployment. Phase 12.3 adds
the secure runtime-configuration definitions; deployment automation belongs to
Phases 12.4 and 12.5.

The plan is deliberately sized for an Azure for Students portfolio deployment.
It uses consumption-based Container Apps, a single small PostgreSQL server, and
scale-to-zero web workloads. It is suitable for a small, non-commercial demo;
reassess sizing, availability, backup retention, and networking before a
public launch.

## Target Topology

```text
Internet
  |
  +-- Frontend Container App (Next.js, external HTTPS ingress)
  |       |
  |       +-- Backend Container App (FastAPI, external HTTPS ingress)
  |
  +-- Azure Container Apps environment
          |
          +-- Scheduled Container Apps Job (backend image; no ingress)
          |
          +-- private PostgreSQL Flexible Server

GitHub Actions --OIDC--> Azure Container Registry --> Container Apps
                         |
                         +--> versioned frontend and backend images

Container Apps managed identities --> Azure Key Vault
Container Apps environment --> Log Analytics workspace
```

All resources will be created in one production resource group,
`rg-garmin-coach-prod`, in `UK South` unless the Student subscription cannot
create a required resource there. Phase 12.2 must verify availability before
provisioning and use one alternate UK region consistently if needed.

## Resources and Responsibilities

| Resource                                      | MVP decision                                                                                                         | Responsibility and limits                                                                                                                                                                                                    |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Azure Container Registry                      | One Basic registry, `acrgarmincoachprod` (subject to Azure naming availability).                                     | Stores versioned frontend and backend images. No geo-replication, registry Tasks, or public anonymous pulls. Container Apps pulls using managed identity and the `AcrPull` role.                                             |
| Azure Container Apps environment              | One consumption environment, `cae-garmin-coach-prod`, integrated with a dedicated virtual network.                   | Hosts both web apps and the scheduled job, sends platform/app logs to the Log Analytics workspace, and allows workloads to scale to zero.                                                                                    |
| Frontend Container App                        | `ca-garmin-coach-web`, built from `frontend/Dockerfile`; external HTTPS ingress on port 3000.                        | Runs Next.js and Better Auth. Set `minReplicas: 0`, `maxReplicas: 1`; it is intentionally a single-replica MVP deployment.                                                                                                   |
| Backend Container App                         | `ca-garmin-coach-api`, built from `backend/Dockerfile`; external HTTPS ingress on port 8000.                         | Runs FastAPI for browser requests and manual sync. Set `minReplicas: 0`, `maxReplicas: 1`. The frontend calls its public HTTPS origin.                                                                                       |
| Scheduled Container Apps Job                  | `caj-garmin-coach-sync`, using the backend image with command `python -m app.jobs.sync`; no ingress.                 | Runs once daily at `03:00 UTC`, with one parallel execution and one retry. It performs incremental Garmin syncs and generates insights for successful syncs. One scheduled execution prevents duplicate scheduler instances. |
| Migration Container Apps Job                  | `caj-garmin-coach-migrate`, using the backend image with command `/app/.venv/bin/alembic upgrade head`; no ingress.  | Starts manually once for each deployment after its backend image is available. It has one replica, no retry, and uses the same Key Vault database secret as the API.                                                         |
| Better Auth Migration Job                     | `caj-garmin-coach-auth-migrate`, using the frontend migration image with command `npm run auth:migrate`; no ingress. | Starts manually after the Alembic job and before web apps. It creates or updates Better Auth's `user`, `session`, and related auth tables using the Key Vault Better Auth database URL.                                      |
| Demo Seed Job                                 | `caj-garmin-coach-demo-seed`, using the frontend migration image with command `npm run demo:seed`; no ingress.       | Starts once per deployment after Better Auth migrations. It creates or resets one synthetic smoke-test account and dashboard dataset; it never uses Garmin credentials or real health data.                                  |
| Azure Database for PostgreSQL Flexible Server | One Burstable B1ms server with 32 GB storage and 32 GB backup storage.                                               | Holds application, Better Auth, and Alembic-managed schema data. One database and one server only; no HA or read replicas for the MVP.                                                                                       |
| Azure Key Vault                               | One Standard vault, `kv-garmin-coach-prod`.                                                                          | Stores production secrets; apps and jobs read secrets through managed identities. Secrets are never committed, baked into images, or placed in GitHub Actions logs.                                                          |
| Log Analytics workspace                       | One workspace, `log-garmin-coach-prod`, with the shortest supported retention that meets debugging needs.            | Receives Container Apps platform and sanitized application logs. Configure a daily ingestion cap/alert in Phase 12.2.                                                                                                        |
| Application Insights                          | Not provisioned initially.                                                                                           | Structured logs plus `/health` and `/ready` are sufficient for the MVP. Add workspace-based Application Insights only when request tracing, dependency telemetry, or production alerting needs it.                           |

The concrete Azure names above are naming targets, not credentials or stable
public hostnames. Phase 12.2 will add a unique suffix where Azure's global
naming rules require it.

## Network and Access Boundaries

- Use a dedicated virtual network with a delegated Container Apps subnet and a
  separate delegated PostgreSQL subnet, plus a private DNS zone. The PostgreSQL
  server uses private access only; do not enable public database access or the
  broad "allow Azure services" firewall exception.
- Frontend and API Container Apps use external ingress so browsers can reach
  them over Azure-managed HTTPS. No direct ingress is configured for the job or
  PostgreSQL server.
- Assign one user-managed runtime identity to the frontend, API, and job. It is
  created before the workloads so its `AcrPull` and Key Vault secret-read roles
  are available before private images or secrets are consumed.
- GitHub Actions authenticates through an Azure user-assigned managed identity
  and workload identity federation (OIDC). The federated credential trusts only
  this repository's `main` branch; no long-lived Azure client secret is stored
  in GitHub. The identity receives Contributor at this resource group, AcrPush
  at the registry, and Key Vault Secrets Officer at the vault.

## Runtime Configuration and Secrets

Phase 12.3 defines the following values as Key Vault secrets or Container Apps
secret references. `configureRuntimeSecrets=true` writes the first three from
secure Bicep parameters; none are stored in source control or template outputs:

- `DATABASE_URL` and `BETTER_AUTH_DATABASE_URL`, both using TLS to the same
  PostgreSQL server.
- `BETTER_AUTH_SECRET`, a new long random production secret. It must be kept
  stable because it derives encryption keys for stored Garmin session material.
- `demo-user-password`, supplied from the GitHub `SMOKE_TEST_PASSWORD` secret
  only during deployment and read by the ingress-free demo seed job. It is not
  exposed to the frontend or API containers.
- `FRONTEND_URL` and `BETTER_AUTH_URL`, set to the final frontend HTTPS origin.
- `BETTER_AUTH_COOKIE_DOMAIN`, set to the shared parent domain of the frontend
  and API hosts when they use different subdomains (for example,
  `coach.jamieyau.com` for `coach.jamieyau.com` and
  `api.coach.jamieyau.com`).
- `NEXT_PUBLIC_API_BASE_URL`, set at _frontend image build time_ to the final
  backend HTTPS origin. It is public configuration, not a secret.
- `BACKEND_CORS_ORIGINS`, set exactly to the final frontend origin; do not use a
  wildcard while credentials are enabled.

The production workflow reconciles the API and frontend hostname bindings after
its final Bicep deployment, which handles managed-certificate issuance and
recovery. The DNS CNAME and `asuid` TXT validation records must already exist
before the first deployment using a custom domain; the workflow uses
Azure-managed certificates with CNAME validation and fails if a binding cannot
be created.

- `APP_ENV=production`, `BETTER_AUTH_SECURE_COOKIES=true`, and production rate
  limiting settings.
- `AI_PROVIDER=mock` by default. `OPENAI_API_KEY` is required only if a later
  decision changes the provider to `openai`; Azure OpenAI is not part of this
  deployment plan.

The frontend, API, and scheduled job share database and encryption settings.
Only the frontend receives Better Auth's runtime database settings; only the
backend and job receive the AI-provider settings.

Container Apps external ingress explicitly rejects HTTP (`allowInsecure=false`)
and Azure supplies the default `https://...azurecontainerapps.io` origin. The
backend refuses to start in production unless its database URL, 32+-character
Better Auth secret, exact HTTPS CORS origin, and credentialed CORS setting are
present. Better Auth's secure cookies, CSRF/origin checks, and rate limiting are
also explicitly enabled in the frontend Container App.

## Operations, Cost, and Delivery Guardrails

- Keep both web apps at zero minimum replicas and one maximum replica until
  actual traffic demonstrates a need to scale. Cold starts are acceptable for
  this portfolio MVP.
- The scheduled job must remain a single daily execution. It relies on the
  existing bounded incremental sync behavior and must not be scaled into
  concurrent schedulers without database-backed locking.
- Create an Azure Cost Management budget and alerts before provisioning. Do not
  remove the Azure for Students spending limit or add Marketplace services.
- The Student/free allowances can change and the database/monitoring usage can
  exceed them. Check the subscription's current offer, remaining credit, and
  UK-region availability in the Azure portal before Phase 12.2.
- Deploy only immutable, versioned images. After CI passes on `main`, the Phase
  12.4 workflow pushes backend and Better Auth migration images, runs Alembic
  and Better Auth schema migrations through manual jobs, resets the synthetic
  smoke-test dashboard through an ingress-free job, discovers the Azure HTTPS
  origins while staging the API/frontend, then applies the final exact
  CORS/Auth configuration and enables scheduled sync.
- Retain only sanitized logs. Revisit PostgreSQL backup retention and data
  deletion behavior before any public launch.

## Infrastructure as Code

Phase 12.2 uses Azure-native Bicep. The subscription-scoped entry point in
`infra/main.bicep` creates the production resource group and calls the
resource-group baseline in `infra/modules/platform.bicep`. It creates the VNet,
private DNS zone, PostgreSQL server/database, registry, Key Vault, Log
Analytics workspace, runtime identity, and Container Apps environment.

The frontend, API, and scheduled job definitions are present but conditional.
`deployWorkloads` defaults to `false`, so validating or creating the baseline
does not attempt to pull placeholder images or resolve Key Vault secrets.
`infra/README.md` documents the required Azure CLI `validate`, `what-if`, and
`create` commands. Only enable the workloads after Phase 12.3 creates the
runtime secret values and Phase 12.4 pushes immutable images. The workload
module also defines an ingress-free manual migration job that Phase 12.4 starts
before deploying the backend revision.

`infra/main.bicep` is intentionally subscription-scoped for the one-time
resource-group and GitHub OIDC bootstrap. `infra/deploy.bicep` is equivalent at
resource-group scope and is the template used by GitHub Actions after bootstrap.
The deployment workflow runs only from a successful CI run on `main` (or a
manual workflow dispatch) and serializes production deploys to avoid competing
migrations.

## Deployment Verification

After applying the final production configuration, the deployment workflow runs
`tests/smoke/deployment-smoke.sh`. It retries through Container Apps cold starts
and verifies all of the following over the public HTTPS origins:

- `GET /health` returns the expected healthy API response.
- The configured smoke account can sign in through Better Auth and retrieve its
  session.
- The authenticated frontend serves `/dashboard`, and the authenticated API
  dashboard overview contains the seeded demo connection, activity, recovery,
  sleep, and coaching-insight data.

Before enabling the workflow, create GitHub repository secrets
`SMOKE_TEST_EMAIL` and `SMOKE_TEST_PASSWORD` for a non-personal synthetic demo
account. Each deployment writes the password to Key Vault as a secure template
parameter, starts `caj-garmin-coach-demo-seed` after the Better Auth migration,
and resets that account's dashboard records before it is used by the smoke
test. The account must never contain real Garmin data or credentials. The
secrets are neither printed nor supplied to the frontend/API containers and
must be rotated if exposed.

For a manual verification using the same contract, run the script from a
trusted machine with `curl` and `jq` installed:

```bash
SMOKE_TEST_EMAIL='demo@example.invalid' \
SMOKE_TEST_PASSWORD='replace-with-the-demo-password' \
bash tests/smoke/deployment-smoke.sh \
  --api-origin 'https://your-api-origin' \
  --frontend-origin 'https://your-frontend-origin'
```

The script intentionally fails if either origin is not HTTPS, authentication
does not issue a usable shared session cookie, or the dashboard account lacks
the expected synthetic data. Investigate failed smoke tests through sanitized
Container Apps logs; do not put session cookies, credentials, or health data in
workflow output.

## Explicit Non-Goals

- No Azure resources, DNS custom domain, or deployment workflow are created by
  the repository alone. Bicep definitions are present, but deployment remains
  an explicit Azure CLI or future GitHub Actions action.
- No Redis, queue worker, Azure OpenAI, Front Door/WAF, application gateway,
  geo-replication, high availability, or database read replica is included.
- No guarantee is made that the deployment stays free after Azure for Students
  credit or service allowances expire.

# Azure MVP Deployment Plan

## Scope and Status

This document defines the target Azure production topology for the MVP. Phase
12.2 supplies reproducible Bicep definitions for the platform baseline; it does
not provision the subscription, configure runtime secret values, or enable
automatic deployment. Those changes belong to Phases 12.3 through 12.5.

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

| Resource | MVP decision | Responsibility and limits |
| --- | --- | --- |
| Azure Container Registry | One Basic registry, `acrgarmincoachprod` (subject to Azure naming availability). | Stores versioned frontend and backend images. No geo-replication, registry Tasks, or public anonymous pulls. Container Apps pulls using managed identity and the `AcrPull` role. |
| Azure Container Apps environment | One consumption environment, `cae-garmin-coach-prod`, integrated with a dedicated virtual network. | Hosts both web apps and the scheduled job, sends platform/app logs to the Log Analytics workspace, and allows workloads to scale to zero. |
| Frontend Container App | `ca-garmin-coach-web`, built from `frontend/Dockerfile`; external HTTPS ingress on port 3000. | Runs Next.js and Better Auth. Set `minReplicas: 0`, `maxReplicas: 1`; it is intentionally a single-replica MVP deployment. |
| Backend Container App | `ca-garmin-coach-api`, built from `backend/Dockerfile`; external HTTPS ingress on port 8000. | Runs FastAPI for browser requests and manual sync. Set `minReplicas: 0`, `maxReplicas: 1`. The frontend calls its public HTTPS origin. |
| Scheduled Container Apps Job | `caj-garmin-coach-sync`, using the backend image with command `python -m app.jobs.sync`; no ingress. | Runs once daily at `03:00 UTC`, with one parallel execution and one retry. It performs incremental Garmin syncs and generates insights for successful syncs. One scheduled execution prevents duplicate scheduler instances. |
| Azure Database for PostgreSQL Flexible Server | One Burstable B1ms server with 32 GB storage and 32 GB backup storage. | Holds application, Better Auth, and Alembic-managed schema data. One database and one server only; no HA or read replicas for the MVP. |
| Azure Key Vault | One Standard vault, `kv-garmin-coach-prod`. | Stores production secrets; apps and jobs read secrets through managed identities. Secrets are never committed, baked into images, or placed in GitHub Actions logs. |
| Log Analytics workspace | One workspace, `log-garmin-coach-prod`, with the shortest supported retention that meets debugging needs. | Receives Container Apps platform and sanitized application logs. Configure a daily ingestion cap/alert in Phase 12.2. |
| Application Insights | Not provisioned initially. | Structured logs plus `/health` and `/ready` are sufficient for the MVP. Add workspace-based Application Insights only when request tracing, dependency telemetry, or production alerting needs it. |

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
- GitHub Actions authenticates through Azure workload identity federation (OIDC)
  in Phase 12.4. It receives deployment-scoped access only; no long-lived Azure
  client secret is stored in GitHub.

## Runtime Configuration and Secrets

Phase 12.3 must provide the following values from Key Vault or Container Apps
secret references, never from the image build or source control:

- `DATABASE_URL` and `BETTER_AUTH_DATABASE_URL`, both using TLS to the same
  PostgreSQL server.
- `BETTER_AUTH_SECRET`, a new long random production secret. It must be kept
  stable because it derives encryption keys for stored Garmin session material.
- `FRONTEND_URL` and `BETTER_AUTH_URL`, set to the final frontend HTTPS origin.
- `NEXT_PUBLIC_API_BASE_URL`, set at *frontend image build time* to the final
  backend HTTPS origin. It is public configuration, not a secret.
- `BACKEND_CORS_ORIGINS`, set exactly to the final frontend origin; do not use a
  wildcard while credentials are enabled.
- `APP_ENV=production`, `BETTER_AUTH_SECURE_COOKIES=true`, and production rate
  limiting settings.
- `AI_PROVIDER=mock` by default. `OPENAI_API_KEY` is required only if a later
  decision changes the provider to `openai`; Azure OpenAI is not part of this
  deployment plan.

The frontend, API, and scheduled job share database and encryption settings.
Only the frontend receives Better Auth's runtime database settings; only the
backend and job receive the AI-provider settings.

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
- Deploy only immutable, versioned images. Phase 12.4 will build and push both
  images after CI passes on `main`, run Alembic migrations once, then update the
  Container Apps revisions.
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
runtime secret values and Phase 12.4 pushes immutable images.

## Explicit Non-Goals

- No Azure resources, DNS custom domain, or deployment workflow are created by
  the repository alone. Bicep definitions are present, but deployment remains
  an explicit Azure CLI or future GitHub Actions action.
- No Redis, queue worker, Azure OpenAI, Front Door/WAF, application gateway,
  geo-replication, high availability, or database read replica is included.
- No guarantee is made that the deployment stays free after Azure for Students
  credit or service allowances expire.

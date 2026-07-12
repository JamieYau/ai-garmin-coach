# Azure Infrastructure

This directory uses Bicep rather than Terraform. Bicep is Azure-native and
keeps the MVP deployment in the same Azure Resource Manager control plane; it
does not require a separate state backend.

`main.bicep` is subscription-scoped so it creates the production resource
group. `modules/platform.bicep` defines the reusable resource-group baseline.
It creates the VNet, private DNS zone, PostgreSQL Flexible Server, Container
Registry, Key Vault, Log Analytics workspace, managed identity, and Container
Apps environment.

Container App and Job resources are defined in `modules/workloads.bicep`, but
are disabled by default. This keeps the first infrastructure deployment safe:
real images and final public origins do not exist until Phase 12.4.

## Prerequisites

- Azure CLI with the Bicep extension available (`az bicep version`).
- An active Azure for Students subscription selected with `az account set`.
- The `Microsoft.App`, `Microsoft.ContainerRegistry`, `Microsoft.DBforPostgreSQL`,
  `Microsoft.KeyVault`, `Microsoft.Network`, and `Microsoft.OperationalInsights`
  resource providers registered in that subscription.
- A strong PostgreSQL administrator password supplied only through a local
  environment variable or a secure CI secret. Do not add it to a parameter file.

## Validate Before Provisioning

```bash
export AZURE_POSTGRES_ADMIN_PASSWORD='replace-with-a-strong-local-password'

az deployment sub validate \
  --location uksouth \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam
```

Preview the planned changes with `what-if` before creating any resource:

```bash
az deployment sub what-if \
  --location uksouth \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam
```

Create the infrastructure baseline only after reviewing the preview:

```bash
az deployment sub create \
  --name garmin-coach-platform \
  --location uksouth \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam
```

This baseline creates billable Azure resources. Keep the Azure for Students
spending limit enabled and verify the current Student offer, remaining credit,
and UK South availability before running it.

## Enabling Workloads Later

The baseline can now create the Key Vault secrets named `database-url`,
`better-auth-database-url`, and `better-auth-secret` from secure deployment
parameters. It does not create them unless `configureRuntimeSecrets=true`.

Before setting that parameter, assign the deployment identity the **Key Vault
Secrets Officer** role on the generated Key Vault. Generate and export a random
secret locally; do not print it, commit it, or pass it on a command line:

```bash
export AZURE_BETTER_AUTH_SECRET="$(openssl rand -base64 48)"

az deployment sub what-if \
  --location uksouth \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam \
  --parameters configureRuntimeSecrets=true
```

After reviewing the preview, use the same command with `az deployment sub
create`. Bicep derives the two TLS PostgreSQL connection strings from the
secure administrator-password parameter and stores all three values in Key
Vault. No connection string or Better Auth secret is output by the template.

Do not set `deployWorkloads=true` yet. Phase 12.4 must push the immutable image
tags named by `frontendImageTag` and `backendImageTag` and deploy the Container
Apps with the final origins.

The first live deployment also needs the exact frontend and API HTTPS origins.
The deployment workflow will stage this safely: deploy the API, read its Azure
FQDN, build the frontend with that API origin, deploy the frontend, then update
the API CORS origin to the frontend FQDN. A custom domain can replace the Azure
FQDNs later without changing the resource topology.

The backend migration job (`caj-garmin-coach-migrate`) is also defined with the
workloads. It has no ingress and runs `alembic upgrade head` once per manual
execution using the Key Vault database secret. Phase 12.4 will start it after
pushing the backend image and before updating the API revision.

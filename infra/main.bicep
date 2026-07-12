targetScope = 'subscription'

@description('Azure region for every production resource.')
param location string = 'uksouth'

@description('Production resource group to create or update.')
param resourceGroupName string = 'rg-garmin-coach-prod'

@description('Lowercase alphanumeric project prefix used in resource names.')
@minLength(5)
@maxLength(14)
param projectName string = 'garmincoach'

@description('Administrator login for the PostgreSQL Flexible Server.')
param postgresAdministratorLogin string = 'garminadmin'

@secure()
@description('Administrator password for the PostgreSQL Flexible Server. Supply only at deployment time.')
param postgresAdministratorPassword string

@description('Deploy the Next.js frontend Container App. Keep false until its API origin is known.')
param deployFrontendApp bool = false

@description('Deploy the FastAPI Container App. Keep false until migration succeeds.')
param deployApiApp bool = false

@description('Deploy the scheduled Garmin sync Container Apps Job.')
param deployScheduledSyncJob bool = false

@description('Deploy the manual Alembic migration Container Apps Job.')
param deployMigrationJob bool = false

@description('Immutable frontend image tag to deploy when deployWorkloads is true.')
param frontendImageTag string = 'bootstrap'

@description('Immutable backend image tag to deploy when deployWorkloads is true.')
param backendImageTag string = 'bootstrap'

@description('Final public HTTPS frontend origin, without a trailing slash.')
param frontendOrigin string = ''

@secure()
@description('Long random Better Auth secret. Provide only when configureRuntimeSecrets is true.')
param betterAuthSecret string = ''

@description('Create or update Key Vault runtime secrets from the secure deployment parameters.')
param configureRuntimeSecrets bool = false

@description('GitHub owner/repository slug trusted for main-branch OIDC, for example owner/repository.')
param githubRepository string = ''

@description('Create the GitHub Actions OIDC managed identity, federated credential, and deployment roles.')
param configureGithubOidc bool = false

@description('Create one-time Azure RBAC role assignments for runtime and GitHub deployment identities.')
param configureRoleAssignments bool = false

var nameSuffix = toLower(take(uniqueString(subscription().id, resourceGroupName), 6))

resource productionResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: {
    application: 'ai-garmin-coach'
    environment: 'production'
    managedBy: 'bicep'
  }
}

module platform './modules/platform.bicep' = {
  name: 'garmin-coach-platform'
  scope: productionResourceGroup
  params: {
    location: location
    projectName: projectName
    nameSuffix: nameSuffix
    postgresAdministratorLogin: postgresAdministratorLogin
    postgresAdministratorPassword: postgresAdministratorPassword
    deployFrontendApp: deployFrontendApp
    deployApiApp: deployApiApp
    deployScheduledSyncJob: deployScheduledSyncJob
    deployMigrationJob: deployMigrationJob
    frontendImageTag: frontendImageTag
    backendImageTag: backendImageTag
    frontendOrigin: frontendOrigin
    betterAuthSecret: betterAuthSecret
    configureRuntimeSecrets: configureRuntimeSecrets
    githubRepository: githubRepository
    configureGithubOidc: configureGithubOidc
    configureRoleAssignments: configureRoleAssignments
  }
}

output resourceGroupId string = productionResourceGroup.id
output containerRegistryLoginServer string = platform.outputs.containerRegistryLoginServer
output keyVaultUri string = platform.outputs.keyVaultUri
output postgresServerFqdn string = platform.outputs.postgresServerFqdn
output frontendFqdn string = platform.outputs.frontendFqdn
output apiFqdn string = platform.outputs.apiFqdn
output githubDeploymentClientId string = platform.outputs.githubDeploymentClientId

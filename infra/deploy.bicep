targetScope = 'resourceGroup'

@description('Azure region for every production resource.')
param location string = resourceGroup().location

@description('Lowercase alphanumeric project prefix used in resource names.')
@minLength(5)
@maxLength(14)
param projectName string = 'garmincoach'

@description('Administrator login for the PostgreSQL Flexible Server.')
param postgresAdministratorLogin string = 'garminadmin'

@secure()
@description('Administrator password for the PostgreSQL Flexible Server. Supply only at deployment time.')
param postgresAdministratorPassword string

param deployFrontendApp bool = false
param deployApiApp bool = false
param deployScheduledSyncJob bool = false
param deployMigrationJob bool = false
param deployAuthMigrationJob bool = false
param frontendImageTag string = 'bootstrap'
param backendImageTag string = 'bootstrap'
param frontendOrigin string = ''

@secure()
param betterAuthSecret string = ''

param configureRuntimeSecrets bool = false
param githubRepository string = ''
param configureGithubOidc bool = false
param configureRoleAssignments bool = false

var nameSuffix = toLower(take(uniqueString(subscription().id, resourceGroup().name), 6))

module platform './modules/platform.bicep' = {
  name: 'garmin-coach-platform'
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
    deployAuthMigrationJob: deployAuthMigrationJob
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

output containerRegistryLoginServer string = platform.outputs.containerRegistryLoginServer
output keyVaultUri string = platform.outputs.keyVaultUri
output postgresServerFqdn string = platform.outputs.postgresServerFqdn
output frontendFqdn string = platform.outputs.frontendFqdn
output apiFqdn string = platform.outputs.apiFqdn
output githubDeploymentClientId string = platform.outputs.githubDeploymentClientId

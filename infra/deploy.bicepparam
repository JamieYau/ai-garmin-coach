using './deploy.bicep'

param projectName = 'garmincoach'
param postgresAdministratorLogin = 'garminadmin'
param postgresAdministratorPassword = readEnvironmentVariable('AZURE_POSTGRES_ADMIN_PASSWORD')
param betterAuthSecret = readEnvironmentVariable('AZURE_BETTER_AUTH_SECRET', '')
param deployFrontendApp = false
param deployApiApp = false
param deployScheduledSyncJob = false
param deployMigrationJob = false
param deployAuthMigrationJob = false
param configureRuntimeSecrets = false
param configureGithubOidc = false
param configureRoleAssignments = false

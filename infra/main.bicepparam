using './main.bicep'

param location = 'uksouth'
param resourceGroupName = 'rg-garmin-coach-prod'
param projectName = 'garmincoach'
param postgresAdministratorLogin = 'garminadmin'

// Read the password from a local environment variable or secure pipeline
// environment. It must never be committed to this file.
param postgresAdministratorPassword = readEnvironmentVariable('AZURE_POSTGRES_ADMIN_PASSWORD')

param deployWorkloads = false
param configureRuntimeSecrets = false

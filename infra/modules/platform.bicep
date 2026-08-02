param location string
@minLength(5)
param projectName string
param nameSuffix string
param postgresAdministratorLogin string

@secure()
param postgresAdministratorPassword string

param deployFrontendApp bool
param deployApiApp bool
param deployScheduledSyncJob bool
param deployMigrationJob bool
param deployAuthMigrationJob bool
param deployDemoSeedJob bool
param frontendImageTag string
param backendImageTag string
param frontendOrigin string
param betterAuthCookieDomain string

@secure()
param betterAuthSecret string

@secure()
param demoUserPassword string

param demoUserEmail string

param configureRuntimeSecrets bool
param configureDemoSeedSecret bool
param githubRepository string
param configureGithubOidc bool
param configureRoleAssignments bool

var resourcePrefix = '${projectName}-${nameSuffix}'
var tags = {
  application: 'ai-garmin-coach'
  environment: 'production'
  managedBy: 'bicep'
}
var acrPullRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
var acrPushRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8311e382-0749-4cb8-b61a-304f252e45ec')
var keyVaultSecretsUserRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
var keyVaultSecretsOfficerRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7')
var contributorRoleDefinitionId = subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
var databaseHost = postgresServer.properties.fullyQualifiedDomainName
var encodedPostgresPassword = uriComponent(postgresAdministratorPassword)
var databaseUrl = 'postgresql+psycopg://${postgresAdministratorLogin}:${encodedPostgresPassword}@${databaseHost}:5432/garmin_coach?sslmode=require'
var betterAuthDatabaseUrl = 'postgresql://${postgresAdministratorLogin}:${encodedPostgresPassword}@${databaseHost}:5432/garmin_coach?sslmode=require'

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-${resourcePrefix}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.42.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'snet-container-apps'
        properties: {
          addressPrefix: '10.42.0.0/23'
          delegations: [
            {
              name: 'container-apps-environment'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'snet-postgres'
        properties: {
          addressPrefix: '10.42.2.0/28'
          delegations: [
            {
              name: 'postgres-flexible-server'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
    ]
  }
}

resource containerAppsSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: virtualNetwork
  name: 'snet-container-apps'
}

resource postgresSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' existing = {
  parent: virtualNetwork
  name: 'snet-postgres'
}

resource postgresPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'private.postgres.database.azure.com'
  location: 'global'
  tags: tags
}

resource postgresPrivateDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: postgresPrivateDnsZone
  name: 'postgres-vnet-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetwork.id
    }
  }
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${resourcePrefix}'
  location: location
  tags: tags
  properties: {
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
    workspaceCapping: {
      dailyQuotaGb: 1
    }
  }
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acr${projectName}${nameSuffix}'
  location: location
  sku: {
    name: 'Basic'
  }
  tags: tags
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-${resourcePrefix}'
  location: location
  tags: tags
  properties: {
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    publicNetworkAccess: 'Enabled'
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
  }
}

resource runtimeIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${resourcePrefix}-runtime'
  location: location
  tags: tags
}

resource githubDeploymentIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (configureGithubOidc) {
  name: 'id-${resourcePrefix}-github-deploy'
  location: location
  tags: tags
}

resource githubMainFederatedCredential 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = if (configureGithubOidc) {
  parent: githubDeploymentIdentity
  name: 'github-main'
  properties: {
    audiences: [
      'api://AzureADTokenExchange'
    ]
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepository}:ref:refs/heads/main'
  }
}

resource githubDeploymentContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (configureGithubOidc && configureRoleAssignments) {
  name: guid(resourceGroup().id, githubDeploymentIdentity.id, contributorRoleDefinitionId)
  properties: {
    principalId: githubDeploymentIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: contributorRoleDefinitionId
  }
}

resource githubDeploymentAcrPush 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (configureGithubOidc && configureRoleAssignments) {
  name: guid(containerRegistry.id, githubDeploymentIdentity.id, acrPushRoleDefinitionId)
  scope: containerRegistry
  properties: {
    principalId: githubDeploymentIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPushRoleDefinitionId
  }
}

resource githubDeploymentKeyVaultSecretsOfficer 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (configureGithubOidc && configureRoleAssignments) {
  name: guid(keyVault.id, githubDeploymentIdentity.id, keyVaultSecretsOfficerRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: githubDeploymentIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsOfficerRoleDefinitionId
  }
}

resource runtimeAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (configureRoleAssignments) {
  name: guid(containerRegistry.id, runtimeIdentity.id, acrPullRoleDefinitionId)
  scope: containerRegistry
  properties: {
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
}

resource runtimeKeyVaultSecretsUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (configureRoleAssignments) {
  name: guid(keyVault.id, runtimeIdentity.id, keyVaultSecretsUserRoleDefinitionId)
  scope: keyVault
  properties: {
    principalId: runtimeIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: keyVaultSecretsUserRoleDefinitionId
  }
}

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: 'psql-${resourcePrefix}'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  tags: tags
  properties: {
    administratorLogin: postgresAdministratorLogin
    administratorLoginPassword: postgresAdministratorPassword
    availabilityZone: '1'
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    createMode: 'Create'
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: postgresSubnet.id
      privateDnsZoneArmResourceId: postgresPrivateDnsZone.id
    }
    storage: {
      autoGrow: 'Disabled'
      storageSizeGB: 32
    }
    version: '16'
  }
}

resource applicationDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgresServer
  name: 'garmin_coach'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource databaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (configureRuntimeSecrets) {
  parent: keyVault
  name: 'database-url'
  properties: {
    value: databaseUrl
  }
}

resource betterAuthDatabaseUrlSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (configureRuntimeSecrets) {
  parent: keyVault
  name: 'better-auth-database-url'
  properties: {
    value: betterAuthDatabaseUrl
  }
}

resource betterAuthSecretSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (configureRuntimeSecrets) {
  parent: keyVault
  name: 'better-auth-secret'
  properties: {
    value: betterAuthSecret
  }
}

resource demoUserPasswordSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (configureDemoSeedSecret) {
  parent: keyVault
  name: 'demo-user-password'
  properties: {
    value: demoUserPassword
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-${resourcePrefix}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: containerAppsSubnet.id
      internal: false
    }
    zoneRedundant: false
  }
}

module workloads './workloads.bicep' = if (deployFrontendApp || deployApiApp || deployScheduledSyncJob || deployMigrationJob || deployAuthMigrationJob || deployDemoSeedJob) {
  name: 'garmin-coach-workloads'
  params: {
    location: location
    environmentId: containerAppsEnvironment.id
    registryLoginServer: containerRegistry.properties.loginServer
    runtimeIdentityId: runtimeIdentity.id
    keyVaultUri: keyVault.properties.vaultUri
    frontendImageTag: frontendImageTag
    backendImageTag: backendImageTag
    frontendOrigin: frontendOrigin
    betterAuthCookieDomain: betterAuthCookieDomain
    deployFrontendApp: deployFrontendApp
    deployApiApp: deployApiApp
    deployScheduledSyncJob: deployScheduledSyncJob
    deployMigrationJob: deployMigrationJob
    deployAuthMigrationJob: deployAuthMigrationJob
    deployDemoSeedJob: deployDemoSeedJob
    demoUserEmail: demoUserEmail
    tags: tags
  }
  dependsOn: [
    databaseUrlSecret
    betterAuthDatabaseUrlSecret
    betterAuthSecretSecret
    demoUserPasswordSecret
  ]
}

output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output keyVaultUri string = keyVault.properties.vaultUri
output postgresServerFqdn string = postgresServer.properties.fullyQualifiedDomainName
output frontendFqdn string = deployFrontendApp ? workloads!.outputs.frontendFqdn : ''
output apiFqdn string = deployApiApp ? workloads!.outputs.apiFqdn : ''
output githubDeploymentClientId string = configureGithubOidc ? githubDeploymentIdentity!.properties.clientId : ''

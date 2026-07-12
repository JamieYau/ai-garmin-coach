param location string
param environmentId string
param registryLoginServer string
param runtimeIdentityId string
param keyVaultUri string
param frontendImageTag string
param backendImageTag string
param frontendOrigin string
param tags object
param deployFrontendApp bool
param deployApiApp bool
param deployScheduledSyncJob bool
param deployMigrationJob bool

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = if (deployFrontendApp) {
  name: 'ca-garmin-coach-web'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentityId}': {}
    }
  }
  tags: tags
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: true
        targetPort: 3000
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: registryLoginServer
          identity: runtimeIdentityId
        }
      ]
      secrets: [
        {
          name: 'better-auth-database-url'
          keyVaultUrl: '${keyVaultUri}secrets/better-auth-database-url'
          identity: runtimeIdentityId
        }
        {
          name: 'better-auth-secret'
          keyVaultUrl: '${keyVaultUri}secrets/better-auth-secret'
          identity: runtimeIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${registryLoginServer}/garmin-coach-frontend:${frontendImageTag}'
          env: [
            {
              name: 'NODE_ENV'
              value: 'production'
            }
            {
              name: 'BETTER_AUTH_DATABASE_URL'
              secretRef: 'better-auth-database-url'
            }
            {
              name: 'BETTER_AUTH_SECRET'
              secretRef: 'better-auth-secret'
            }
            {
              name: 'BETTER_AUTH_URL'
              value: frontendOrigin
            }
            {
              name: 'FRONTEND_URL'
              value: frontendOrigin
            }
            {
              name: 'BETTER_AUTH_SECURE_COOKIES'
              value: 'true'
            }
            {
              name: 'BETTER_AUTH_RATE_LIMIT_ENABLED'
              value: 'true'
            }
            {
              name: 'BETTER_AUTH_RATE_LIMIT_WINDOW_SECONDS'
              value: '60'
            }
            {
              name: 'BETTER_AUTH_RATE_LIMIT_MAX_REQUESTS'
              value: '20'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = if (deployApiApp) {
  name: 'ca-garmin-coach-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentityId}': {}
    }
  }
  tags: tags
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        external: true
        targetPort: 8000
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: registryLoginServer
          identity: runtimeIdentityId
        }
      ]
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${keyVaultUri}secrets/database-url'
          identity: runtimeIdentityId
        }
        {
          name: 'better-auth-secret'
          keyVaultUrl: '${keyVaultUri}secrets/better-auth-secret'
          identity: runtimeIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${registryLoginServer}/garmin-coach-backend:${backendImageTag}'
          env: [
            {
              name: 'APP_ENV'
              value: 'production'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'BETTER_AUTH_SECRET'
              secretRef: 'better-auth-secret'
            }
            {
              name: 'FRONTEND_URL'
              value: frontendOrigin
            }
            {
              name: 'BACKEND_CORS_ORIGINS'
              value: frontendOrigin
            }
            {
              name: 'BACKEND_CORS_ALLOW_CREDENTIALS'
              value: 'true'
            }
            {
              name: 'AI_PROVIDER'
              value: 'mock'
            }
            {
              name: 'RATE_LIMIT_ENABLED'
              value: 'true'
            }
            {
              name: 'GARMIN_CONNECTION_RATE_LIMIT_MAX_REQUESTS'
              value: '5'
            }
            {
              name: 'GARMIN_CONNECTION_RATE_LIMIT_WINDOW_SECONDS'
              value: '60'
            }
            {
              name: 'MANUAL_SYNC_RATE_LIMIT_MAX_REQUESTS'
              value: '3'
            }
            {
              name: 'MANUAL_SYNC_RATE_LIMIT_WINDOW_SECONDS'
              value: '60'
            }
            {
              name: 'AI_INSIGHT_RATE_LIMIT_MAX_REQUESTS'
              value: '3'
            }
            {
              name: 'AI_INSIGHT_RATE_LIMIT_WINDOW_SECONDS'
              value: '60'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

resource scheduledSyncJob 'Microsoft.App/jobs@2024-03-01' = if (deployScheduledSyncJob) {
  name: 'caj-garmin-coach-sync'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentityId}': {}
    }
  }
  tags: tags
  properties: {
    environmentId: environmentId
    configuration: {
      triggerType: 'Schedule'
      replicaRetryLimit: 1
      replicaTimeout: 1800
      scheduleTriggerConfig: {
        cronExpression: '0 3 * * *'
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          server: registryLoginServer
          identity: runtimeIdentityId
        }
      ]
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${keyVaultUri}secrets/database-url'
          identity: runtimeIdentityId
        }
        {
          name: 'better-auth-secret'
          keyVaultUrl: '${keyVaultUri}secrets/better-auth-secret'
          identity: runtimeIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'scheduled-sync'
          image: '${registryLoginServer}/garmin-coach-backend:${backendImageTag}'
          command: [
            'python'
            '-m'
            'app.jobs.sync'
          ]
          env: [
            {
              name: 'APP_ENV'
              value: 'production'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'BETTER_AUTH_SECRET'
              secretRef: 'better-auth-secret'
            }
            {
              name: 'AI_PROVIDER'
              value: 'mock'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }
}

resource migrationJob 'Microsoft.App/jobs@2024-03-01' = if (deployMigrationJob) {
  name: 'caj-garmin-coach-migrate'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${runtimeIdentityId}': {}
    }
  }
  tags: tags
  properties: {
    environmentId: environmentId
    configuration: {
      triggerType: 'Manual'
      replicaRetryLimit: 0
      replicaTimeout: 1800
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      registries: [
        {
          server: registryLoginServer
          identity: runtimeIdentityId
        }
      ]
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${keyVaultUri}secrets/database-url'
          identity: runtimeIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'database-migration'
          image: '${registryLoginServer}/garmin-coach-backend:${backendImageTag}'
          command: [
            'alembic'
            'upgrade'
            'head'
          ]
          env: [
            {
              name: 'APP_ENV'
              value: 'production'
            }
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }
}

output frontendFqdn string = deployFrontendApp ? frontendApp!.properties.configuration.ingress.fqdn : ''
output apiFqdn string = deployApiApp ? apiApp!.properties.configuration.ingress.fqdn : ''

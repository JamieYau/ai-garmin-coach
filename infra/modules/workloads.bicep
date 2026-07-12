param location string
param environmentId string
param registryLoginServer string
param runtimeIdentityId string
param keyVaultUri string
param frontendImageTag string
param backendImageTag string
param frontendOrigin string
param tags object

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
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

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = {
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

resource scheduledSyncJob 'Microsoft.App/jobs@2024-03-01' = {
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

output frontendFqdn string = frontendApp.properties.configuration.ingress.fqdn
output apiFqdn string = apiApp.properties.configuration.ingress.fqdn

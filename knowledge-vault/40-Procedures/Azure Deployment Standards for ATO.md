---
title: Azure Deployment Standards for ATO
type: procedure
created: 2026-01-02
updated: 2026-01-02
tags: [azure, ato, deployment, security, compliance]
status: active
project: ATO-Tax-Agent
---

# Azure Deployment Standards for ATO

## Overview

Production deployment standards for Australian Tax Office (ATO) compliant applications on Microsoft Azure. Critical for public-facing tax assistance applications handling Australian taxpayer data.

## Regulatory Context

### Australian Privacy Principles (APPs)

**Applies**: Privacy Act 1988 (Cth)

**Requirements**:
- APP 1: Open and transparent management of personal information
- APP 5: Notification of collection
- APP 11: Security of personal information (CRITICAL)
- APP 12: Access to personal information
- APP 13: Correction of personal information

### ATO-Specific Requirements

- **Data sovereignty**: Australian taxpayer data must remain in Australia
- **Encryption**: Data at rest and in transit
- **Access controls**: Role-based access, audit logging
- **Incident response**: Breach notification within 72 hours
- **Data retention**: 7 years for tax records (ATO requirement)

## Azure Infrastructure

### Region Selection

**MANDATORY**: Australia East or Australia Southeast

```bicep
param location string = 'australiaeast'  // or 'australiasoutheast'

// FORBIDDEN in production
// param location string = 'eastus'  // ❌ Data leaves Australia
```

**Rationale**: APP 11 + data sovereignty requirements

### Resource Naming Convention

```
{app}-{env}-{resource}-{region}

Examples:
- atotax-prod-app-aue  (App Service)
- atotax-prod-db-aue   (PostgreSQL)
- atotax-prod-kv-aue   (Key Vault)
- atotax-prod-st-aue   (Storage Account)
```

**Environment Codes**:
- `dev`: Development
- `uat`: User Acceptance Testing
- `prod`: Production

### Resource Groups

```bicep
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'atotax-prod-rg-aue'
  location: 'australiaeast'
  tags: {
    Environment: 'Production'
    Application: 'ATO Tax Agent'
    CostCenter: 'Engineering'
    Owner: 'john.dixon@example.com'
    DataClassification: 'Sensitive'  // Taxpayer PII
    Compliance: 'APP11,ATO'
  }
}
```

## Security Architecture

### 1. Network Security

#### Virtual Network (VNet)

```bicep
resource vnet 'Microsoft.Network/virtualNetworks@2021-05-01' = {
  name: 'atotax-prod-vnet-aue'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: 'app-subnet'
        properties: {
          addressPrefix: '10.0.1.0/24'
          serviceEndpoints: [
            { service: 'Microsoft.KeyVault' }
            { service: 'Microsoft.Sql' }
            { service: 'Microsoft.Storage' }
          ]
        }
      }
      {
        name: 'db-subnet'
        properties: {
          addressPrefix: '10.0.2.0/24'
          delegations: [
            {
              name: 'postgres-delegation'
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
```

#### Network Security Groups (NSG)

```bicep
resource appNsg 'Microsoft.Network/networkSecurityGroups@2021-05-01' = {
  name: 'atotax-prod-app-nsg-aue'
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-HTTPS-Inbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'Deny-All-Inbound'
        properties: {
          priority: 4096
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}
```

### 2. Identity and Access Management

#### Managed Identity

```bicep
resource appServiceIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2018-11-30' = {
  name: 'atotax-prod-identity-aue'
  location: location
}

// Grant Key Vault access
resource kvAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2021-10-01' = {
  parent: keyVault
  name: 'add'
  properties: {
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: appServiceIdentity.properties.principalId
        permissions: {
          secrets: ['get', 'list']
          // NO 'set' or 'delete' in production
        }
      }
    ]
  }
}
```

#### Role-Based Access Control (RBAC)

```bicep
// Principle of Least Privilege
var contributorRole = subscriptionResourceId('Microsoft.Authorization/roleDefinitions',
  'b24988ac-6180-42a0-ab88-20f7382dd24c')  // Contributor

resource appServiceRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(appService.id, contributorRole)
  scope: appService
  properties: {
    roleDefinitionId: contributorRole
    principalId: appServiceIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}
```

### 3. Encryption

#### Key Vault

```bicep
resource keyVault 'Microsoft.KeyVault/vaults@2021-10-01' = {
  name: 'atotax-prod-kv-aue'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'premium'  // HSM-backed keys for production
    }
    tenantId: subscription().tenantId
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: true  // MANDATORY for production
    enableRbacAuthorization: true
    networkAcls: {
      defaultAction: 'Deny'  // Deny by default
      bypass: 'AzureServices'
      virtualNetworkRules: [
        {
          id: vnet.properties.subnets[0].id
        }
      ]
    }
  }
}
```

#### Database Encryption

```bicep
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' = {
  name: 'atotax-prod-db-aue'
  location: location
  sku: {
    name: 'Standard_D2ds_v4'
    tier: 'GeneralPurpose'
  }
  properties: {
    version: '15'
    administratorLogin: 'dbadmin'
    administratorLoginPassword: null  // Use Key Vault reference
    storage: {
      storageSizeGB: 128
    }
    backup: {
      backupRetentionDays: 35  // 5 weeks for production
      geoRedundantBackup: 'Enabled'  // Disaster recovery
    }
    highAvailability: {
      mode: 'ZoneRedundant'  // 99.99% SLA
    }
    network: {
      delegatedSubnetResourceId: vnet.properties.subnets[1].id
      privateDnsZoneResourceId: privateDnsZone.id
    }
  }
}

// Transparent Data Encryption (TDE) - enabled by default
// Customer-managed keys (CMK) for additional security
resource dbEncryption 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2022-12-01' = {
  parent: postgres
  name: 'azure.extensions'
  properties: {
    value: 'pgcrypto'  // For application-level encryption
  }
}
```

#### Storage Encryption

```bicep
resource storageAccount 'Microsoft.Storage/storageAccounts@2021-09-01' = {
  name: 'atotaxprodstaue'  // No hyphens in storage names
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_GRS'  // Geo-redundant
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true  // MANDATORY
    encryption: {
      services: {
        blob: {
          enabled: true
          keyType: 'Account'
        }
        file: {
          enabled: true
          keyType: 'Account'
        }
      }
      keySource: 'Microsoft.Keyvault'  // Customer-managed keys
      keyvaultproperties: {
        keyname: 'storage-encryption-key'
        keyvaulturi: keyVault.properties.vaultUri
      }
    }
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
      virtualNetworkRules: [
        {
          id: vnet.properties.subnets[0].id
          action: 'Allow'
        }
      ]
    }
  }
}
```

### 4. Application Services

#### App Service (Web App)

```bicep
resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: 'atotax-prod-plan-aue'
  location: location
  sku: {
    name: 'P1v3'  // Production tier (3 instances min)
    tier: 'PremiumV3'
    capacity: 3
  }
  properties: {
    reserved: true  // Linux
    zoneRedundant: true  // High availability
  }
}

resource appService 'Microsoft.Web/sites@2022-03-01' = {
  name: 'atotax-prod-app-aue'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${appServiceIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true  // MANDATORY
    clientAffinityEnabled: false  // Stateless for scaling
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'  // or 'NODE|20-lts'
      minTlsVersion: '1.2'
      ftpsState: 'Disabled'  // No FTP in production
      alwaysOn: true
      http20Enabled: true
      webSocketsEnabled: false
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'DATABASE_URL'
          value: '@Microsoft.KeyVault(SecretUri=${keyVault.properties.vaultUri}secrets/database-url/)'
        }
        {
          name: 'APP_ENV'
          value: 'production'
        }
        {
          name: 'LOG_LEVEL'
          value: 'INFO'
        }
      ]
      connectionStrings: []  // Use Key Vault, not connection strings
    }
  }
}
```

## Monitoring and Logging

### Application Insights

```bicep
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'atotax-prod-ai-aue'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    RetentionInDays: 90  // 3 months for production
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Disabled'  // Query via workspace only
  }
}
```

### Log Analytics Workspace

```bicep
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2021-06-01' = {
  name: 'atotax-prod-logs-aue'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 730  // 2 years for compliance
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// Diagnostic settings for audit trail
resource appServiceDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: appService
  name: 'audit-logs'
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      {
        category: 'AppServiceHTTPLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 730
        }
      }
      {
        category: 'AppServiceAuditLogs'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 730
        }
      }
    ]
    metrics: [
      {
        category: 'AllMetrics'
        enabled: true
        retentionPolicy: {
          enabled: true
          days: 90
        }
      }
    ]
  }
}
```

## CI/CD Pipeline (GitHub Actions)

### Deployment Workflow

```yaml
name: Deploy to Azure Production

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write  # OIDC authentication
  contents: read

env:
  AZURE_WEBAPP_NAME: atotax-prod-app-aue
  PYTHON_VERSION: '3.11'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://atotax-prod-app-aue.azurewebsites.net

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        run: |
          pytest tests/ --cov=app --cov-report=xml

      - name: Security scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'

      - name: Azure Login (OIDC)
        uses: azure/login@v1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy to App Service
        uses: azure/webapps-deploy@v2
        with:
          app-name: ${{ env.AZURE_WEBAPP_NAME }}
          slot-name: 'staging'  # Deploy to staging first

      - name: Health check (staging)
        run: |
          sleep 30
          curl -f https://atotax-prod-app-aue-staging.azurewebsites.net/health || exit 1

      - name: Swap to production
        run: |
          az webapp deployment slot swap \
            --resource-group atotax-prod-rg-aue \
            --name atotax-prod-app-aue \
            --slot staging \
            --target-slot production

      - name: Health check (production)
        run: |
          sleep 30
          curl -f https://atotax-prod-app-aue.azurewebsites.net/health || exit 1
```

## Security Checklist

### Pre-Deployment

- [ ] All secrets in Azure Key Vault (none in code/config)
- [ ] Managed Identity configured for all resources
- [ ] RBAC assignments follow least privilege
- [ ] Network security groups configured (deny-by-default)
- [ ] VNet integration enabled for App Service
- [ ] TLS 1.2 minimum enforced
- [ ] HTTPS only (no HTTP)
- [ ] Application Insights configured
- [ ] Log Analytics workspace with 2-year retention
- [ ] Backup and disaster recovery tested
- [ ] Incident response plan documented

### Post-Deployment

- [ ] Vulnerability scan (Trivy/Defender for Cloud)
- [ ] Penetration test scheduled
- [ ] Security baselines configured (Azure Policy)
- [ ] Compliance dashboard reviewed (ATO requirements)
- [ ] Audit logs verified (all access logged)
- [ ] Encryption verified (data at rest + in transit)
- [ ] Backup tested (restore drill)
- [ ] Monitoring alerts configured (security + performance)

## Compliance Validation

### Australian Data Sovereignty

```bash
# Verify all resources in Australia
az resource list \
  --resource-group atotax-prod-rg-aue \
  --query "[].location" \
  -o tsv | sort -u

# Expected output: australiaeast (or australiasoutheast)
# ❌ FAIL if any resource in eastus, westeurope, etc.
```

### Encryption Validation

```bash
# Check App Service HTTPS only
az webapp show \
  --name atotax-prod-app-aue \
  --resource-group atotax-prod-rg-aue \
  --query "httpsOnly"

# Expected: true

# Check Database TLS
az postgres flexible-server show \
  --name atotax-prod-db-aue \
  --resource-group atotax-prod-rg-aue \
  --query "storage.tier"

# Expected: Premium (TDE enabled by default)
```

## Incident Response

### Data Breach Protocol

1. **Detect** (0-4 hours):
   - Monitor Log Analytics alerts
   - Check Application Insights anomalies
   - Review Azure Defender for Cloud

2. **Contain** (4-24 hours):
   - Isolate affected resources (NSG rules)
   - Rotate compromised credentials (Key Vault)
   - Enable geo-redundant backups

3. **Notify** (within 72 hours):
   - **ATO**: If taxpayer data compromised
   - **OAIC**: Privacy breach notification
   - **Users**: Affected taxpayers

4. **Recover**:
   - Restore from geo-redundant backup
   - Apply security patches
   - Post-incident review

## Cost Optimization

### Production Resources

| Resource | SKU | Monthly Cost (AUD) |
|----------|-----|-------------------|
| App Service | P1v3 (3 instances) | $480 |
| PostgreSQL | Standard_D2ds_v4 + HA | $420 |
| Storage | Standard_GRS (100 GB) | $25 |
| Key Vault | Premium | $12 |
| Application Insights | 5 GB/day | $60 |
| **Total** | | **~$1,000/month** |

### Cost Saving Tips

1. Use Azure Hybrid Benefit (if applicable)
2. Reserved instances (1-year commitment = 30% saving)
3. Auto-scaling (scale down off-peak)
4. Archive old logs to Blob Storage (cold tier)

## Related Documents

- `~/.claude/standards/framework/azure-bicep.md` - Bicep coding standards
- `~/.claude/standards/pattern/security-aspnet.md` - Security standards
- `~/.claude/standards/pattern/docker.md` - Containerization
- `knowledge-vault/20-Domains/APIs/ATO/` - ATO-specific requirements

## References

- [Australian Privacy Principles](https://www.oaic.gov.au/privacy/australian-privacy-principles)
- [Azure Security Baseline](https://docs.microsoft.com/azure/security/fundamentals/security-baseline)
- [Azure Well-Architected Framework](https://docs.microsoft.com/azure/architecture/framework/)
- [ATO Digital Service Standard](https://www.ato.gov.au/About-ATO/About-us/In-detail/Strategic-direction/Digital-first/)

---

**Version**: 1.0
**Created**: 2026-01-02
**Status**: Active
**Classification**: Internal Use
**Compliance**: APP11, ATO Data Sovereignty

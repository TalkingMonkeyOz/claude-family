---
projects:
  - ato-infrastructure
  - ato-tax-agent
tags:
  - azure
  - infrastructure
  - deployment
  - free-tier
synced: false
---

# ATO Infrastructure - Azure Resources Overview

This document describes the Azure infrastructure deployed for the Talking Ape / ATO Tax Agent platform.

## Subscription

| Property | Value |
|----------|-------|
| **Name** | ATO Development |
| **ID** | 682721d1-06f1-4b41-81a4-ddc4fb185a8f |
| **Account** | johndevere@outlook.com |

## Resource Groups

| Name | Purpose | Location |
|------|---------|----------|
| rg-ato-prod | Production resources | Australia East |
| rg-ato-shared | Shared resources | Australia East |

## Deployed Resources

### Static Web App (Holding Page)

| Property | Value |
|----------|-------|
| **Name** | swa-talkingape |
| **SKU** | Free |
| **Location** | East Asia |
| **Default URL** | https://delightful-meadow-02472ae00.2.azurestaticapps.net |
| **Custom Domains** | www.talkingape.com.au, talkingape.com.au |
| **GitHub Repo** | https://github.com/TalkingMonkeyOz/talkingape-holding-page |

### PostgreSQL Flexible Server

| Property | Value |
|----------|-------|
| **Name** | psql-ato-prod-001 |
| **SKU** | B1ms (FREE 12 months) |
| **Location** | Australia East |
| **Host** | psql-ato-prod-001.postgres.database.azure.com |
| **Admin** | atoadmin |
| **Database** | postgres |
| **SSL** | Required |

### App Service (Backend API)

| Property | Value |
|----------|-------|
| **Name** | ato-tax-api |
| **Plan** | plan-ato-prod (F1 FREE) |
| **Runtime** | Python 3.12 |
| **URL** | https://ato-tax-api.azurewebsites.net |
| **Status** | Not deployed yet |

### Key Vault

| Property | Value |
|----------|-------|
| **Name** | kv-ato-prod-001 |
| **Location** | Australia East |
| **SKU** | Standard |
| **Access** | RBAC (needs portal config) |

## Monthly Cost

**Total: $0** (all FREE tier resources)

| Resource | Cost |
|----------|------|
| Static Web App | $0 |
| PostgreSQL (12mo free) | $0 |
| App Service (F1) | $0 |
| Key Vault | $0 |

## Security Hardening Applied

- [x] PostgreSQL: SSL required
- [x] App Service: HTTPS only
- [x] App Service: TLS 1.2 minimum
- [x] App Service: FTP disabled
- [x] App Service: HTTP/2 enabled
- [ ] Key Vault: RBAC needs portal configuration

## Related Documents

- [[DNS Configuration]] - Domain setup details
- [[Deployment Workflow]] - CI/CD pipeline
- [[Architecture Design]] - Full system architecture

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/10-Projects/ato-infrastructure/Azure Resources Overview.md

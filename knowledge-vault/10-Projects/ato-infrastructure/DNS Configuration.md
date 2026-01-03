---
projects:
  - ato-infrastructure
tags:
  - dns
  - ventraip
  - azure
  - custom-domain
synced: false
---

# ATO Infrastructure - DNS Configuration

This document describes the DNS setup for talkingape.com.au domains.

## Domain Registrar

| Property | Value |
|----------|-------|
| **Provider** | VentraIP |
| **Domain** | talkingape.com.au |
| **Additional** | talkingape.au, talkingape.store |

## DNS Records (VentraIP)

### Current Configuration

| Type | Hostname | Value | TTL |
|------|----------|-------|-----|
| ALIAS | talkingape.com.au | delightful-meadow-02472ae00.2.azurestaticapps.net | 3600 |
| CNAME | www.talkingape.com.au | delightful-meadow-02472ae00.2.azurestaticapps.net | 3600 |
| TXT | talkingape.com.au | _7dd5gtuf7g0wglhc10eohm6u1vfijo6 | 3600 |
| NS | talkingape.com.au | ns1.nameserver.net.au | 3600 |
| NS | talkingape.com.au | ns2.nameserver.net.au | 3600 |
| NS | talkingape.com.au | ns3.nameserver.net.au | 3600 |

## Azure Static Web App Custom Domains

| Domain | Status | Method |
|--------|--------|--------|
| www.talkingape.com.au | Ready | CNAME |
| talkingape.com.au | Validating | TXT token |

## How to Add Custom Domains

### Subdomain (www)

1. Add CNAME record at VentraIP pointing to Azure SWA default hostname
2. Run: `az staticwebapp hostname set --name swa-talkingape -g rg-ato-prod --hostname www.talkingape.com.au`
3. Azure auto-provisions SSL certificate

### Apex Domain

1. Get validation token: `az staticwebapp hostname show -n swa-talkingape -g rg-ato-prod --hostname talkingape.com.au --query "validationToken"`
2. Add TXT record at VentraIP with the token value
3. Add ALIAS record pointing to Azure SWA default hostname
4. Run: `az staticwebapp hostname set --name swa-talkingape -g rg-ato-prod --hostname talkingape.com.au --validation-method dns-txt-token`
5. Wait for validation (can take up to 72 hours)

## Future: API Subdomain

When ready to deploy the backend API:

| Type | Hostname | Value |
|------|----------|-------|
| CNAME | api.talkingape.com.au | ato-tax-api.azurewebsites.net |
| TXT | asuid.api.talkingape.com.au | 903E4336824BFF2A3AD5B64B8BE333F7A43014FE4BC35D4D8AC4C71B523E5AD6 |

## Troubleshooting

### Check DNS Propagation

```bash
# Check CNAME
nslookup www.talkingape.com.au

# Check TXT record
nslookup -type=TXT talkingape.com.au

# Check from multiple locations
# Use: https://dnschecker.org/
```

### Common Issues

1. **"@" not valid as hostname**: Leave hostname blank or use full domain name
2. **CNAME invalid error**: Use `--validation-method dns-txt-token` for apex domains
3. **Slow propagation**: TTL is 3600 (1 hour), can take longer

---

**Version**: 1.0
**Created**: 2026-01-03
**Updated**: 2026-01-03
**Location**: knowledge-vault/10-Projects/ato-infrastructure/DNS Configuration.md

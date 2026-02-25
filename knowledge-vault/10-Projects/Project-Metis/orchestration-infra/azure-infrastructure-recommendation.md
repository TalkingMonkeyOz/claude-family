---
tags: [Project-Metis, infrastructure, azure, decision, pricing]
project: Project-Metis
date: 2026-02-19
status: recommendation
decision: OPS — Azure Infrastructure
---

# Azure Infrastructure Recommendation

## Context
nimbus already operates on Azure. The AI platform needs an isolated environment — either a new Resource Group within the existing subscription, or a completely separate subscription if security policy requires it.

**Key design principle:** Start small, scale up without rebuilding. Every tier below can be upgraded to the next with zero architectural change — just resize in Azure Portal.

## Pricing Sources
- VM pricing: Vantage (instances.vantage.sh), updated Feb 2026
- PostgreSQL Flexible Server: Azure pricing page + Oreate AI analysis (Feb 2026)
- Prices below are **US East baseline**. Australia East is typically **15-20% higher**
- nimbus may have Enterprise Agreement pricing which could be lower

---

## Option A: Starter — Phase 0-1 (1 user, development)

| Component | SKU | Specs | USD/month (est.) |
|---|---|---|---|
| VM (API server) | B2s | 2 vCPU, 4 GiB RAM | ~$30 |
| PostgreSQL Flexible | B1ms Burstable | 1 vCore, 2 GiB RAM | ~$12-15 |
| Storage (DB) | 32 GB Premium SSD | + pgvector extension (free) | ~$4 |
| Backup storage | 32 GB included | Free up to 100% of provisioned | $0 |
| **TOTAL** | | | **~$46-49/month USD** |
| **Australia East estimate** | | | **~$55-60/month USD** |
| **In AUD (approx)** | | | **~$85-95/month AUD** |

**Good for:** Knowledge Engine development, API connector building, single-user dev/test. pgvector works fine at this tier for our initial knowledge base size.

**Limitation:** 4 GiB VM RAM is tight if running multiple services. Will need upgrade before Monash POC.

---

## Option B: POC Ready — Phase 1-2 (Monash engagement) ⭐ RECOMMENDED START

| Component | SKU | Specs | USD/month (est.) |
|---|---|---|---|
| VM (API server) | B2ms | 2 vCPU, 8 GiB RAM | ~$61 |
| PostgreSQL Flexible | B2ms Burstable | 2 vCore, 8 GiB RAM | ~$50 |
| Storage (DB) | 64 GB Premium SSD | + pgvector extension (free) | ~$7 |
| Backup storage | 64 GB included | Free up to 100% of provisioned | $0 |
| **TOTAL** | | | **~$118/month USD** |
| **Australia East estimate** | | | **~$140/month USD** |
| **In AUD (approx)** | | | **~$215-225/month AUD** |

**Good for:** Running the full platform stack — API layer, Knowledge Engine with vector search, agent orchestration, Monash-specific workloads. Enough memory for PostgreSQL + pgvector to perform well with moderate knowledge base.

**Why this is the recommended start:** Costs less than one day of a consultant's time per month. Enough headroom to demo to Monash without performance issues. Can still use stop/start to save costs when not in use.

---

## Option C: Production Multi-Client — Phase 3+

| Component | SKU | Specs | USD/month (est.) |
|---|---|---|---|
| VM (API server) | B4ms | 4 vCPU, 16 GiB RAM | ~$121 |
| PostgreSQL Flexible | General Purpose D2ds v5 | 2 vCore, 8 GiB RAM | ~$130-150 |
| Storage (DB) | 128 GB Premium SSD | + pgvector extension (free) | ~$15 |
| Backup storage | 128 GB included | Free up to 100% | $0 |
| **TOTAL** | | | **~$266-286/month USD** |
| **Australia East estimate** | | | **~$315-340/month USD** |
| **In AUD (approx)** | | | **~$490-530/month AUD** |

**Good for:** Multiple clients with isolated data, sustained workloads, production SLAs. General Purpose DB tier provides consistent performance (no CPU credit model).

**When to upgrade:** When burstable DB starts hitting CPU credit limits, or when adding 2nd+ client and need consistent performance.

---

## Cost Saving Levers

1. **Stop/Start:** When the DB is stopped, you only pay for storage. During Phase 0-1, stop the server overnight and weekends → could save 60%+ on compute costs
2. **Burstable tier:** Perfect for us — workload is intermittent (dev sessions, not 24/7 production). CPU credits accumulate while idle, available when needed
3. **Reserved Instances (later):** 1-year commitment saves ~40%, 3-year saves ~60%. Only worth it once we're sure about the sizing (Phase 3+)
4. **nimbus EA pricing:** If nimbus has an Enterprise Agreement, prices could be lower than pay-as-you-go
5. **pgvector is free:** It's a PostgreSQL extension, no additional licence cost

## Isolation Options

### Option 1: New Resource Group (in existing nimbus subscription)
- Cheapest and fastest to set up
- Uses nimbus's existing billing, networking
- Isolate via RBAC (Role-Based Access Control) — John gets Contributor on the Resource Group only
- Data residency inherited from subscription (Australia East ✅)
- **Recommended if nimbus security policy allows it**

### Option 2: Separate Subscription (within nimbus tenant)
- Full billing isolation — easy to track AI platform costs separately
- Own network, own RBAC, own resources
- Slightly more setup effort
- **Recommended if management wants clear cost separation**

### Option 3: Completely Separate Azure Tenant
- Maximum isolation
- Probably overkill for this stage
- Harder to connect to nimbus internal resources (time2work APIs)
- **Not recommended unless required by security policy**

## What We Need from nimbus (the actual ask)

1. **Isolated Resource Group** in Azure Australia East (or separate subscription if preferred)
2. **B2ms VM** (Linux) — ~$61 USD/month
3. **PostgreSQL Flexible Server** B2ms Burstable with pgvector — ~$57 USD/month
4. **Networking** to allow outbound connections to time2work API endpoints
5. **John as Contributor** on the Resource Group

**Total ask: ~$140 USD/month (~$215 AUD/month)**

That's less than 2 hours of consultant billing. And the first Monash subscription month ($3-5K) pays for 2+ years of this infrastructure.

## Scalability Path

```
Phase 0-1: B2s VM + B1ms DB         (~$55/mo USD)   ← if cost-conscious
Phase 1-2: B2ms VM + B2ms DB        (~$140/mo USD)  ← recommended start
Phase 3:   B4ms VM + GP D2ds v5 DB  (~$315/mo USD)  ← multi-client
Phase 4+:  D-series VM + scale DB   (~$500+/mo USD) ← enterprise
```

Every step is a resize operation — no rebuild, no migration, no downtime (for DB, brief restart for VM). Architecture stays the same throughout.

## Decision Status
- [ ] nimbus to confirm: Resource Group or Separate Subscription?
- [ ] nimbus to confirm: who provisions (John or IT team)?
- [ ] nimbus to confirm: networking rules for time2work API access from new resource group

---

*Prices checked Feb 19, 2026. Azure pricing changes — verify at time of provisioning.*
*Sources: instances.vantage.sh, azure.microsoft.com/pricing, oreateai.com analysis*

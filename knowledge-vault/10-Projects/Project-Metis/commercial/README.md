---
tags:
  - project/Project-Metis
  - area/commercial
  - scope/system
  - scope/customer
  - level/1
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
synced: false
---

# Commercial Model

> **Scope:** system + customer (generic pricing model at system level, configured per customer deployment)
>
> **Design Principles:**
> - Subscription model creates recurring revenue and aligned incentives
> - Platform costs scale modestly — additional customers share the same engine
> - Enhancement pricing grows the contract incrementally, not in large one-off jumps
> - Business model sits outside platform architecture — not a build dependency

> Revenue model, pricing, revenue share, operating model. The business side of the platform.

**Status:** ✓ BRAINSTORM-COMPLETE (business model, not a build dependency)
**Parent:** [[Project-Metis/README|Level 0 Map]]

## What This Area Covers

Everything about how the platform is structured as a business: pricing, contracts, revenue share, operating model, and the management pitch. This sits outside the platform architecture — it's business model, not system design.

## Operating Model (from Doc 3 §1)

- AI platform sits alongside the core nimbus product, not inside it
- John de Vere does AI development after hours using Claude as primary dev partner
- nimbus provides: API/OData access, Azure infrastructure, test environments
- No internal nimbus development resources required
- No changes to core product timelines or priorities
- Separate entity model — isolates risk, avoids competing for internal resources

## Subscription Pricing (from Doc 3 §2)

| Item | Detail |
|------|--------|
| Base price | $3,000–$5,000/month (per client, based on complexity) |
| Contract term | 24 months |
| Total contract value | $72,000–$120,000 per client |
| Billing | Monthly in advance |
| Enhancements | ~$500–$2,000 added to annual subscription per enhancement |

### Enhancement Examples
- New report: ~$1,000/year added
- New integration: ~$1,000–$2,000/year added
- Custom workflow: ~$1,000/year added
- Additional entity coverage: ~$500–$1,000/year added

### Monash Example
- Base: $4,000/month ($48,000/year)
- Year 1: 3 enhancements at $1,000 = $51,000
- Year 2: 2 more enhancements = $53,000
- 24-month contract value: $104,000

## Revenue Share (from Doc 3 §3)

| Component | John de Vere (20%) | nimbus (80%) |
|-----------|-------------------|-------------|
| Base subscription ($4K/month) | $800/month | $3,200/month |
| Annual (before enhancements) | $9,600/year | $38,400/year |
| 24-month contract | $19,200 | $76,800 |

Revenue share applies to: bespoke AI services to individual clients, AI-assisted implementation subscriptions, custom AI workflows, client-specific enhancements.

Does NOT apply to: internal nimbus use of AI platform, standard PS that happens to use AI, generic features that become part of core time2work.

## Build Costs (from Doc 3 §4)

| Item | Annual Cost |
|------|-----------|
| Claude API usage | $2,000–$5,000 |
| Claude Pro subscription | $240 |
| Azure hosting (isolated) | $1,200–$3,600 |
| Domain/SSL/misc | $200–$500 |
| John's time | After hours — not a nimbus cost |
| **Total Year 1** | **$3,600–$9,300** |

Compare to: $50K–$500K outsourced, $15K–$50K off-the-shelf licences.

## Revenue vs Cost (from Doc 3 §4.2)

With one client (Monash) at $4,000/month:
| Timeframe | Revenue (nimbus 80%) | Infrastructure | Net to nimbus |
|-----------|---------------------|---------------|--------------|
| Month 1 | $3,200 | $300–$750 | $2,450–$2,900 |
| Year 1 | $38,400 | $3,600–$9,300 | $29,100–$34,800 |
| 24-month contract | $76,800+ | $7,200–$18,600 | $58,200–$69,600 |

**Breakeven:** First month's subscription covers nearly the entire annual infrastructure cost.

## Scale Projection (from Doc 3 §4.3)

| Scenario | Monthly Revenue (nimbus 80%) | Annual Revenue | Infra Cost |
|----------|----------------------------|---------------|-----------|
| 1 client | $2,400–$4,000 | $28,800–$48,000 | $3,600–$9,300 |
| 3 clients | $7,200–$12,000 | $86,400–$144,000 | $5,000–$12,000 |
| 5 clients | $12,000–$20,000 | $144,000–$240,000 | $6,000–$15,000 |

## Management Pitch

12-slide meeting handout deck exists — covers problem, opportunity, capabilities, department impact, Monash POC, build vs buy, numbers, decisions needed. Ready for presentation.

## Commercial Decisions Needed

- [ ] #decision Is 20%/80% revenue share acceptable? Formal agreement needed?
- [ ] #decision Is separate entity model workable? What legal structure?
- [ ] #decision Is $3–5K/month the right range for Monash? Who validates pricing?
- [ ] #decision Who owns client relationship for AI services — John or existing account manager?

## Related

- [[decisions/README|Open Decisions]] — commercial decisions tracked there too
- [[ps-accelerator/README|PS Accelerator]] — the Monash POC that proves the model

---
*Source: Doc 3 (all) | Meeting Handout Deck | Created: 2026-02-19*

---
tags: [Project-Metis, security, privacy, claude, anthropic, decision]
project: Project-Metis
date: 2026-02-19
status: reference
---

# Claude / Anthropic Data Privacy — Facts for Management

## The Short Answer

**API usage and Commercial plans (Team/Enterprise) = your data is NOT used for training. Full stop.**

Consumer plans (Free/Pro/Max) changed in Sept 2025 — training is now opt-in. But for the nimbus AI platform, we'd be using the **API**, which has the strongest privacy protections.

---

## Privacy by Account Type (Verified Feb 2026)

| Account Type | Data Used for Training? | Retention | Notes |
|---|---|---|---|
| **API (direct)** | ❌ Never | 7 days (since Sep 2025) | Zero-Data-Retention (ZDR) available |
| **Claude for Work (Team/Enterprise)** | ❌ Never | 30 days | Commercial Terms apply |
| **Claude Gov** | ❌ Never | Configurable | Government-grade |
| **AWS Bedrock / Google Vertex** | ❌ Never | Provider-managed | Provider logging configurable |
| Claude Free/Pro/Max (consumer) | ✅ If user opts in | 30 days (opt-out) / 5 years (opt-in) | Changed Sept 2025 |
| Claude Code (from consumer account) | ✅ If user opts in | Same as above | Follows account type |
| Claude Code (from API/commercial) | ❌ Never | Same as API | Follows account type |

**Source:** Anthropic Privacy Center (privacy.claude.com), Anthropic Consumer Terms update Aug 2025, Claude Code docs (code.claude.com/docs/en/data-usage)

---

## What This Means for nimbus

### Current State (John's personal setup)
- John uses Claude **Pro/Max** (consumer plan) for development
- Training opt-out is available and should be toggled OFF in settings
- 30-day retention applies when opted out
- **Action:** Verify John's privacy settings are set to NOT allow training

### Production Platform (recommended)
- nimbus AI platform should use **Anthropic API keys**
- API data is **never** used for training — this is contractual under Commercial Terms
- Retention is **7 days** by default (since Sep 2025)
- **Zero-Data-Retention (ZDR)** available via Data Processing Addendum — logs deleted immediately after abuse checks
- All data encrypted in transit (TLS)

### If nimbus wants enterprise-grade
- **Claude for Work (Enterprise)** or **API with ZDR addendum** gives maximum protection
- Anthropic offers a Data Processing Addendum (DPA) for commercial customers
- Trust Center available at trust.anthropic.com with compliance artifacts

---

## Comparison: Claude API vs Copilot (Microsoft 365)

| Factor | Claude API | Microsoft Copilot (M365) |
|---|---|---|
| Training on your data | ❌ Never (API) | ❌ Never (enterprise) |
| Data retention | 7 days (ZDR available) | Microsoft's standard retention policies |
| Data residency | US-based (Anthropic servers) | Configurable (Azure regions) |
| Compliance certs | SOC 2 Type II | SOC 2, ISO 27001, FedRAMP, etc. |
| DPA available | Yes | Yes |
| Zero-data-retention option | Yes (ZDR addendum) | Not standard |
| Data stays in Australia? | ❌ Not currently — processed in US | ✅ Can be configured for AU |

### Honest Gap: Data Residency
**This is the one area where Claude is weaker than Copilot for an Australian enterprise.** Anthropic processes API calls in the US. The data is encrypted in transit, retained for only 7 days (or zero with ZDR), and never used for training — but it does leave Australia temporarily for processing.

**Mitigations:**
- Data is transient (prompts and responses), not stored long-term
- 7-day retention, or ZDR for zero retention
- The Knowledge Engine itself (PostgreSQL + pgvector) stays in Azure Australia East
- Only API calls to Claude leave the country; all persistent data stays in AU
- AWS Bedrock (Sydney region) could be an alternative if AU data residency is a hard requirement — Claude is available on Bedrock in ap-southeast-2

---

## Management Talking Points

1. **"Does Claude train on our data?"** — No. Not on the API. Not on commercial plans. This is contractual.

2. **"Is it as private as Copilot?"** — For training data protection, yes — same policy (never trains on commercial data). For data residency, Copilot has the edge because it can run in Australian Azure regions. Claude API currently processes in the US but retains for only 7 days (or zero). If AU residency is a hard constraint, Claude on AWS Bedrock (Sydney) is an option.

3. **"What about client data (Monash)?"** — The platform design keeps all persistent client data in Azure Australia East. Only transient API calls (prompts/responses) go to Anthropic's US servers, encrypted, retained 7 days max, never used for training.

4. **"Can we get a DPA?"** — Yes. Anthropic provides Data Processing Addendums for commercial API customers.

---

## Decision Items for Management

- [ ] Is 7-day transient data retention in US acceptable, or do we need ZDR?
- [ ] Is transient US processing acceptable, or must ALL data stay in Australia? (If yes → evaluate Claude on AWS Bedrock Sydney)
- [ ] Does nimbus need a formal DPA with Anthropic before starting?
- [ ] Should John's personal Pro/Max account privacy settings be audited?

---

*Sources: Anthropic Privacy Center, Anthropic Consumer Terms (Aug 2025), Claude Code docs, Bitdefender analysis, AMST Legal analysis, Goldfarb Gross Seligman analysis. All verified Feb 19, 2026.*

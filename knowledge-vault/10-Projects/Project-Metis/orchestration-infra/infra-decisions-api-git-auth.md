---
tags: [Project-Metis, infrastructure, decisions, anthropic-api, git, authentication]
project: Project-Metis
date: 2026-02-19
status: recommendation
---

# INFRA Decisions: API Keys, Git, Authentication

Three decisions that unblock building. Researched and recommended — needs John's approval.

---

## Decision 1: API Key Provisioning

**Question:** Personal Anthropic account or nimbus org? What budget cap?

### How Anthropic API Billing Works (Verified Feb 2026)

- **Prepaid credits.** You buy credits upfront, usage deducts from them. No surprise bills.
- **Auto-reload optional.** You can set a threshold to auto-purchase more credits, or just let it stop when credits run out. Either way, you control spend.
- **Tier system based on cumulative deposits:**

| Tier | Cumulative Deposit | Monthly Spend Limit | Rate Limits |
|---|---|---|---|
| Tier 1 | $5 | $100/month | 50 RPM, basic |
| Tier 2 | $40 | $500/month | Higher RPM |
| Tier 3 | $200 | $1,000/month | ~2x Tier 2 |
| Tier 4 | $400 | $4,000/month | Max self-service, 1M context |

- **Workspaces** — Console supports workspaces for organising keys by project/environment. Each workspace can have its own spend cap and rate limits. API keys are workspace-scoped.

### Options

**Option A: John's Personal Account (recommended start)**
- Fastest to set up (minutes)
- John controls the billing
- Start at Tier 1 ($5 deposit), upgrade to Tier 2 ($40 cumulative) within days
- Create workspaces: `nimbus-dev`, `nimbus-monash-poc`
- Set workspace spend limits independently
- If nimbus formalises → migrate to org account later (keys are replaceable, code just reads ANTHROPIC_API_KEY env var)

**Option B: nimbus Organisation Account**
- Requires nimbus to sign up at console.anthropic.com
- Better for: multiple developers, admin oversight, formal billing
- Slower to set up (needs someone with company credit card + phone verification)
- Better for production, but overkill for Phase 0

**Option C: Hybrid (recommended path)**
- Start with John's personal account NOW → begin building immediately
- Create a nimbus org account when management approves the initiative
- Migration is trivial: generate new key in new org, update env var, done

### Budget Recommendation

| Phase | Monthly Budget | Tier Needed | Notes |
|---|---|---|---|
| Phase 0 (setup) | $50–100 | Tier 1 ($5 deposit) | Schema setup, initial testing |
| Phase 1 (Knowledge Engine) | $200–500 | Tier 2 ($40 deposit) | Heavy development, agent teams |
| Phase 2 (Monash POC) | $500–1,000 | Tier 3 ($200 deposit) | Client-facing work, more throughput |
| Production | $1,000–2,000 | Tier 3–4 | Depends on client count |

**Cost controls built in:**
- Prepaid credits = no surprise bills (it just stops when credits run out)
- Workspace-level spend caps for additional safety
- Auto-reload is optional (recommend OFF initially)
- Prompt caching reduces costs 70-80% for repeated context (Knowledge Engine system prompts)
- Batch API at 50% discount for non-urgent work (documentation generation, reports)

### ⭐ RECOMMENDATION

**Start with John's personal account. $40 deposit to reach Tier 2. Create a `nimbus-platform` workspace with $200/month spend cap. Migrate to nimbus org account when formally approved.**

Initial out-of-pocket: $40. Maximum exposure: $200/month (hard cap). Can start building today.

---

## Decision 2: Git Repository Location

**Question:** GitHub (personal) or Azure DevOps (nimbus)?

### Considerations

| Factor | GitHub (Personal) | Azure DevOps (nimbus) |
|---|---|---|
| Setup speed | Minutes | Needs IT involvement |
| Claude Code integration | Native (GitHub is first-class) | Supported but less native |
| Agent Teams support | Proven (all Anthropic examples use GitHub) | Works but less documented |
| Visibility to nimbus | Invite collaborators manually | Already in nimbus ecosystem |
| CI/CD | GitHub Actions (excellent, free for private repos) | Azure Pipelines (nimbus may already have) |
| IP ownership | On John's account (transfer later) | On nimbus from day one |
| Cost | Free for private repos | Included in nimbus subscription |

### The IP Question

This is the real consideration. If code is on John's personal GitHub:
- nimbus may have concerns about IP ownership
- Transfer to nimbus later is straightforward (GitHub repo transfer or mirror to Azure DevOps)
- But it's a conversation that's easier to have upfront

If code is on nimbus Azure DevOps:
- IP clearly sits with nimbus from day one
- But needs IT to set up, which may slow things down
- And if the project doesn't get approved, there's cruft in nimbus's DevOps

### ⭐ RECOMMENDATION

**Start with private GitHub repo under John's account. Solves the "I need to start building" problem immediately. Include a clear statement in the project docs that IP developed for the nimbus AI platform is nimbus's intellectual property regardless of hosting location. Migrate to Azure DevOps when the project is formally approved — this is a standard git remote change, takes 5 minutes.**

Compromise option: If nimbus IT can set up an Azure DevOps project within a week, start there instead. The technical difference is minimal — it's about speed vs formality.

---

## Decision 3: Authentication Model

**Question:** What auth model for the platform itself?

### Context

This is about how users (John, other nimbus staff, eventually Monash stakeholders) authenticate to the nimbus AI platform — NOT about how the platform authenticates to external APIs (that's handled by the connector layer with encrypted credentials).

### Options

**Option A: API Key Only (internal tool)**
- Simplest: generate a key, put it in config
- Good for: single developer (John) during Phase 0-1
- Bad for: multi-user, no audit trail per user, no RBAC
- Effort: Hours

**Option B: Username/Password + JWT (recommended start)**
- Standard web auth: login form, JWT tokens, refresh tokens
- Supports: multiple users, role-based access, audit trail per user
- Good for: Phase 1-2, Monash POC (give Monash stakeholders read-only access)
- Designed to be swappable — auth middleware is a single layer
- Effort: 1-2 days with Claude Code

**Option C: OAuth2/OIDC with nimbus SSO**
- Enterprise-grade: integrate with nimbus's identity provider
- Supports: SSO, MFA, centralised user management
- Good for: Phase 3+ production multi-client
- Requires: nimbus IT involvement, identity provider access
- Effort: 1-2 weeks

**Option D: Auth0/Clerk (managed auth service)**
- Outsource auth to a managed provider
- Free tier covers MVP (Auth0: 7,500 MAU free; Clerk: 10,000 MAU free)
- Supports: social login, MFA, RBAC, SSO integration later
- Effort: Days (pre-built components)

### ⭐ RECOMMENDATION

**Option B (JWT) for Phase 0-2. Design the auth middleware as a swappable layer from day one.**

Reasoning:
- Phase 0-1 is John only — a simple JWT auth with hardcoded admin user is sufficient
- Phase 2 (Monash) needs at least 2-3 users with different roles (admin, viewer)
- The auth middleware pattern means switching to OAuth2/SSO later is a code change in ONE file, not a rewrite
- Avoid managed auth services for now — adds external dependency and another vendor conversation

Implementation approach:
```
src/auth/
  ├── middleware.ts      ← checks JWT, extracts user, checks role
  ├── jwt.ts            ← token generation/validation
  ├── users.ts          ← user CRUD (database-backed)
  └── roles.ts          ← role definitions (admin, developer, viewer, client)
```

When nimbus wants SSO: replace `jwt.ts` with an OIDC provider adapter. Everything else stays the same.

---

## Summary: All Three Decisions

| Decision | Recommendation | Effort | Blocker? |
|---|---|---|---|
| API Key | John's personal account, $40 deposit, Tier 2, workspace caps | 30 minutes | No — John can do today |
| Git Repo | Private GitHub under John, migrate to Azure DevOps when approved | 15 minutes | No — John can do today |
| Auth Model | JWT + middleware, designed for SSO swap later | 1-2 days (Phase 0 task) | No — part of Phase 0 build |

**None of these block each other. All three can be set up in the first day of Phase 0.**

---

## Decision Required from John

- [ ] **API Key:** Confirm personal account start with $40 deposit + $200/month cap
- [ ] **Git Repo:** Confirm GitHub personal start (or flag if nimbus IT can set up Azure DevOps quickly)
- [ ] **Auth Model:** Confirm JWT approach for Phase 0-2
- [ ] **IP Statement:** Agree to include IP ownership statement in project README

---

*Researched: Feb 19, 2026 | Sources: Anthropic API docs, Console Workspaces announcement (Oct 2025), Rate limits docs, Admin API docs*

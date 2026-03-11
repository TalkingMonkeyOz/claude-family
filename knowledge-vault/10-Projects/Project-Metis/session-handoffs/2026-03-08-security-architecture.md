---
tags:
  - project/Project-Metis
  - type/session-handoff
  - domain/security
created: 2026-03-08
session: security-architecture
status: complete
supersedes: 2026-03-08-scope-reframe-actor-map.md
---

# Session Handoff: Security Architecture

## Session Summary

Complete security architecture conversation. 12 decisions validated across deployment model, access control, agent boundaries, authentication, integration security, and audit trail. Written up as `security-architecture.md`. Gate Zero Constraint 6 (data isolation) formally addressed.

---

## WHAT WAS DONE

### security-architecture.md — NEW
Cross-cutting document covering all security concerns. 12 validated decisions:

1. **Separate instances per customer** — each enterprise gets complete METIS deployment (nimbus model)
2. **RBAC + project/client scoping** within instances — scope tags on data, role + assignments on users
3. **Agent access inherits human ceiling** — agent can never see more than the human who initiated work
4. **Agent further constrained to task scope** — prevents AI bleed across projects
5. **Phase 1 hard scope, no elevation** — if you don't have access, agent doesn't either
6. **Elevated access gatekeeper** — designed for, build later (request → evaluate → summary or redacted docs)
7. **Agent action boundaries category-specific** — event-driven lowest risk, project agents need approval for writes/external, system agents observe-only
8. **All agents through application layer** — never direct DB access
9. **All deletes are soft deletes** — nothing permanently removed
10. **Pluggable auth adapter** — token Phase 1, SSO later, RBAC engine built day one
11. **Integration credentials** — encrypted DB now, secrets manager interface for later
12. **Audit trail logs everything** — tiered retention, extract-then-decay, three use cases (crash recovery, language analysis, error detection)

### Design lifecycle updated
- Gate Zero gap (Constraint 6) marked as addressed
- Security architecture added to key references

### Human-AI interaction model flagged
Two modes identified (controlled METIS UI vs MCP-exposed services). Flagged for its own session — bigger than security, affects architecture fundamentally.

---

## KEY DECISIONS THIS SESSION

| Decision | Detail |
|---|---|
| Deployment model | Separate instances per customer, not shared platform |
| Within-instance isolation | RBAC + project/client scoping |
| Agent access rule 1 | Inherits human's access ceiling |
| Agent access rule 2 | Further constrained to task scope |
| Elevated access | Design for, build later (gatekeeper pattern) |
| Agent actions | Category-specific permissions |
| Backend access | All agents through application layer, never direct DB |
| Deletes | Soft deletes only, all actors |
| Auth architecture | Pluggable adapter (token → SSO → future), RBAC from day one |
| Credential storage | Pluggable (encrypted DB → secrets manager) |
| Integration access | Per-user delegation preferred |
| Audit scope | Log everything, tiered retention, extract-then-decay |
| Audit storage | PostgreSQL tables, abstracted interface |
| Recurring pattern | Pluggable adapters behind stable interfaces throughout |

---

## WHAT'S NEXT — PRIORITISED

### 1. Human-AI interaction model session
Controlled METIS UI vs MCP-exposed services vs both. Key architectural question that affects security Mode 2 boundaries, developer experience, and how the Augmentation Layer presents itself.

### 2. Plan-of-attack rewrite
Hand `plan-of-attack-rewrite-brief.md` to doc consolidator (Claude Code).

### 3. Remaining Gate 1 documents
- Process Inventory (Doc 1) — scattered across 9 areas, needs consolidation
- Data Entity Map (Doc 3) — scattered, needs consolidation
- Business Rules Inventory (Doc 4) — scattered, needs consolidation
- Integration Points (Doc 5) — partial, needs detail

### 4. Still open from prior sessions
- Follow up on msg 67d8af18 (vault sync to claude-family)
- Toolkit Categories 2-4 brainstorm
- Validate unvalidated February vault output conversationally

---

## KEY FILES

| File | Status |
|---|---|
| `security-architecture.md` | NEW — validated |
| `design-lifecycle.md` | UPDATED — security gap noted, reference added |
| `gate-zero/assumptions-constraints.md` | Constraint 6 now addressed by security-architecture.md |

---

## SESSION STARTER FOR NEXT CHAT

```
METIS Session Starter — Post Security Architecture
READ FIRST: `session-handoffs/2026-03-08-security-architecture.md`

CONTEXT: Gate Zero COMPLETE + security gap addressed.
Gate 1 Doc 2 (Actor Map) COMPLETE.
Security architecture validated (12 decisions).

PRIORITY: Human-AI interaction model session
(controlled UI vs MCP-exposed services — flagged from security session)

AFTER THAT:
1. Hand plan-of-attack-rewrite-brief.md to Claude Code
2. Remaining Gate 1 docs (Process Inventory, Data Entity Map,
   Business Rules, Integration Points)
3. Follow up on msg 67d8af18 (vault sync to claude-family)

KEY FILES:
* session-handoffs/2026-03-08-security-architecture.md
* security-architecture.md (NEW — validated)
* system-product-definition.md (v0.3)
* plan-of-attack-rewrite-brief.md (for doc consolidator)
* gate-one/actor-map.md (validated)
* design-lifecycle.md (updated)
* gate-zero/ — all 5 docs complete
```

---
*Session: 2026-03-08 | Status: Security architecture complete. 12 decisions validated. Gate Zero gap addressed. Next: interaction model session.*

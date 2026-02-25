---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - topic/day-1-readiness
  - level/2
projects:
  - Project-Metis
created: 2026-02-19
synced: false
---

# Day 1 Readiness Plan

> What needs to be true before the platform is "in use" — not just "built."

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]

## Day 1 Definition

- **Who:** John (single user), but multi-user architecture baked in from the start
- **What they're doing:**
  1. Knowledge Engine queries — asking questions about time2work (APIs, configs, Award rules, screens)
  2. Documentation generation — producing client-facing docs from system state
  3. Config generation for Monash — generating time2work configurations from requirements
- **Where:** Local dev + Azure environment connecting to Monash time2work instance

## Day 1 Checklist

### Must Work
- [ ] Knowledge Engine responds to natural language questions about time2work
- [ ] Knowledge base populated with: API specs, OData metadata, screen discovery results, Monash EAs
- [ ] Can generate a configuration from a requirement input
- [ ] Can generate documentation from a configuration
- [ ] Auth system works (simple API key, but multi-user ready underneath)
- [ ] Audit trail logging every action
- [ ] Session management — start, work, end, resume next day where you left off
- [ ] Crash recovery — if something fails mid-session, state is recoverable

### Must Be Ready (even if not used Day 1)
- [ ] Multi-user data model in place (user_access table, RBAC design)
- [ ] Client data isolation working (Monash data separated from anything else)
- [ ] Second user could be added without architectural changes
- [ ] Integration connectors working: time2work API, time2work OData, Jira (both instances)
- [ ] Error handling — typed errors, logged, never silently swallowed

### Claude Family Patterns to Build Into Platform
These are concepts proven in Claude Family that Claude Code should implement fresh in the new platform (not ported, rebuilt from scratch):
- [ ] Session management pattern (start/end/resume)
- [ ] Crash recovery pattern (state persistence, recovery from failure)
- [ ] Memory systems (knowledge graph + database persistence)
- [ ] Audit logging (every action tracked)
- [ ] Jira integration (both Monash and Nimbus instances)
- [ ] Playwright capability (time2work screen interaction)

### Day 1 NOT in Scope
- Autonomous operations (Phase 3+)
- Support triage (Phase 3)
- Project governance dashboards (Phase 3+)
- Client portal (Future)
- SSO/enterprise auth (when multi-user is real)
- Agent Teams (needs API keys)

## Expansion Path

Day 1 is designed so that going from 1 user to 5 users requires:
- Adding user records to user_access table
- Assigning roles and client access permissions
- No architectural changes, no data migration, no rebuild

Going from Monash-only to multi-client requires:
- Adding client record to clients table
- Populating client-specific knowledge
- No changes to platform code — just new data

## Open Questions

- [ ] What's the realistic target date for Day 1?
- [ ] Does Day 1 happen before or after the management meeting?
- [ ] What's the minimum knowledge base content needed for Day 1 to be useful?

---
*Source: Decision review session 2026-02-19 | Created: 2026-02-19*

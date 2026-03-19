---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/10
  - type/ux
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Gate 2 Deliverable 10: User/Actor Journey Maps

## Overview

Journey maps for each actor type showing how they interact with METIS. Prioritised by MVP relevance. These are structural — detailed wireflows and UX design are Gate 3.

**Key insight:** Some actors (notably PS Consultants) interact with METIS through BOTH the conversational interface AND the REST API as tool builders. The dual-interface decision supports this.

---

## 1. Actor Priority for MVP

| Priority | Actor | MVP Relevance | Interface |
|----------|-------|---------------|-----------|
| **P1** | PS Consultant | Primary user — does the work | Conversational + API |
| **P1** | Enterprise Admin | Sets up the system | Web UI (admin) |
| **P2** | Support Staff | Defect triage (second stream) | Conversational |
| **P2** | Developer | Tests and validates | API + Conversational |
| **P3** | Platform Builder | Deploys and maintains | CLI + API |
| **Deferred** | End Customer | No direct access Phase 1 | None (indirect via PS) |

---

## 2. P1 Journeys

### Journey 1: PS Consultant — "Configure Nimbus for a new client"

**The end-to-end delivery stream. This IS the MVP.**

```
1. Receive client requirements (docs, specs, meetings)
2. Ask METIS: "What's the standard config for [scenario]?"
   → METIS retrieves product domain + past client patterns
3. Review METIS suggestions, adjust for client specifics
4. Ask METIS to generate configuration items from requirements
   → METIS creates config entries with reasoning + uncertainty flags
5. Review generated configs — approve, modify, or reject
6. Ask METIS to generate test scenarios for the configs
   → BPMN-to-test generation (iterative — Decision Test-2)
7. Run tests, review failures, iterate
8. Package into release, deploy to UAT
9. Client validates, defects loop back through support
10. Deploy to production
```

**Key interactions:** ask, learn (ingest client requirements), check (validate configs), find (search knowledge)

**Pain points addressed:**
- Currently: consultant carries knowledge in their head, every engagement starts from scratch
- With METIS: accumulated knowledge from past engagements surfaces automatically

### Journey 2: PS Consultant — "I have a question about Nimbus"

**Core knowledge retrieval.**

```
1. Ask natural language question via MCP or web UI
2. METIS searches knowledge base (embeddings, scope-filtered)
3. METIS assembles answer with citations
4. Consultant reads answer, checks citations
5. If helpful → implicit positive feedback
6. If wrong/incomplete → explicit correction → becomes learned knowledge
```

**Key interactions:** ask, feedback

### Journey 3: PS Consultant — "Build a custom tool"

**The tool-builder journey — PS consultant as developer.**

```
1. Identify a repeatable analysis need (e.g. Monash shift analysis)
2. Connect to METIS REST API with JWT token
3. Use /search, /knowledge/{id}, /similar endpoints
4. Build custom analysis logic around METIS data
5. Results feed back into METIS as learned knowledge
```

**Key interactions:** REST API directly (not MCP), ingest (results back in)

**Design implication:** REST API must be well-documented, easy to authenticate against, and stable enough for custom tooling.

### Journey 4: Enterprise Admin — "Set up a new engagement"

**Onboarding flow.**

```
1. Create engagement in admin UI (client, product, scope)
   → EngagementCreated event fires
2. Configure scope guardrails (strict/general, domain tags)
3. Set retention policies (or accept defaults)
4. Set token budget allocation
5. Configure connectors (OData, file drop, etc.)
6. Invite users, assign roles
7. Trigger initial knowledge ingestion
8. Verify via /health and test query
```

**Key interactions:** Admin UI (CRUD operations on config tables)

---

## 3. P2 Journeys (Sketched)

### Journey 5: Support Staff — "Client reported a bug"

```
1. Receive defect report (Jira sync or manual)
2. Ask METIS: "Have we seen this before?"
   → Pattern detection across clients
3. If pattern found: show resolution from previous instance
4. If new: create issue thread, begin investigation
5. Link defect to config items, test scenarios
6. Resolution → promoted to knowledge base
```

### Journey 6: Developer — "Test my configuration changes"

```
1. Submit configuration change
2. METIS identifies affected BPMN paths
3. Generates regression scope
4. Runs test suite against changes
5. Reports pass/fail with explanations
6. Developer fixes, re-runs (iterative — BPMN loop)
```

---

## 4. P3 Journey (Sketched)

### Journey 7: Platform Builder — "Deploy for a new customer"

```
1. Provision infrastructure (container, DB, DNS)
2. Run migration scripts
3. Configure customer instance (org, products, initial admin)
4. Set up connectors and initial knowledge ingestion
5. Run smoke tests
6. Hand off to Enterprise Admin
```

---

## 5. Three Interaction Scenarios (Prior Design)

From earlier design work — three complexity levels:

| Scenario | User Says | METIS Does | Constraint Level |
|----------|-----------|------------|-----------------|
| **Simple Query** | "What's the leave accrual config for Monash?" | Search → retrieve → answer with citation | L1 Guided |
| **Multi-Step Task** | "Generate test scenarios for the payroll pipeline" | Decompose → BPMN extract → generate → present for review | L2 Assisted |
| **Cross-Agent Handoff** | "Configure Monash payroll, test it, and prepare the release" | Controller → decompose → supervisor → specialists → human checkpoints | L3 Open |

---

## 6. Open Items (Gate 3)

- [ ] Detailed wireflows for each P1 journey
- [ ] UX design for human review experience (explanation + suggestions)
- [ ] Non-technical user experience design
- [ ] UX baseline metrics capture
- [ ] Prototype / clickable mockups
- [ ] Accessibility considerations
- [ ] Mobile/responsive design requirements
- [ ] Expand all journeys with detailed touchpoints, emotions, pain points

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-10-journey-maps.md

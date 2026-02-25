---
tags:
  - project/Project-Metis
  - area/knowledge-engine
  - scope/system
  - level/1
  - phase/1
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
synced: false
---

# Knowledge Engine

> **Scope:** system (generic platform capability — knowledge types and domains configured per customer)
>
> **Design Principles:**
> - Knowledge quality is the single biggest factor in system success (73% RAG failures are quality, not tech)
> - Tiered validation — system-generated auto-approved, human knowledge human-reviewed, AI-generated never auto-trusted
> - Four-level scope hierarchy: Organisation → Product → Client → Engagement
> - Pluggable embedding and LLM interfaces — no vendor lock-in
> - The AI must know what it doesn't know and say so

> The brain of the platform. Everything else depends on this being good.

**Priority:** CRITICAL — Phase 1
**Status:** ✓ BRAINSTORM-COMPLETE (Chat #2 deep dive + Chat #10 consolidation)
**Parent:** [[Project-Metis/README|Level 0 Map]]

## What This Area Covers

Central AI that understands time2work inside and out — every API, every configuration option, every rule type. It learns from every implementation and every support ticket. It never forgets.

## The Core Problem (from Doc 1)

nimbus has 20 years of deep workforce management knowledge. That knowledge lives in people's heads, in scattered documents, in tribal expertise. When a senior consultant leaves, that knowledge walks out the door. New hires take 6-12 months to get productive.

The Knowledge Engine captures, structures, and makes searchable everything nimbus knows.

## Brainstorm Items (from Doc 4 WS1)

### Domain Knowledge Ingestion
- Ingest time2work API specs (Swagger/OpenAPI)
- Ingest OData metadata
- Ingest configuration documentation
- Ingest Award rules and enterprise agreements
- Ingest implementation patterns from past projects
- Ingest support ticket resolutions

### Playwright Discovery
- Automated screen-by-screen discovery of time2work UI
- Record what screens exist, what fields they have, what workflows connect them
- Build a map of the product from the UI level, not just the API level

### Knowledge Graph
- Structured relationships between entities: clients, configurations, Awards, modules, API endpoints
- Not just flat text — understand how things connect
- E.g. "This Award rule type affects these pay components which are configured on these screens"

### Vector Search
- Semantic search across unstructured knowledge (support tickets, meeting notes, documentation)
- Uses pgvector extension on PostgreSQL
- Allows agents and humans to ask questions in natural language

### Knowledge Versioning
- Track how knowledge changes over time
- When did a configuration change? When was an Award updated?
- Historical view — not just current state

### Client-Specific Knowledge
- Isolated knowledge per client
- Monash has different EAs, different configurations, different patterns than other clients
- Must be strictly separated (security requirement)

### Learning Loop
- Every implementation teaches the system
- Every support ticket adds knowledge
- Every test result refines understanding
- Automated ingestion from work outputs — not manual data entry

## Knowledge Sources (What We Can Feed It)

### Available Now
- **time2work REST API** — John has access. Endpoints, request/response shapes, auth
- **time2work OData** — John has access. Reporting and data extraction
- **SQL database** — John has direct access. Data model, relationships, actual data
- **Existing vault docs** — 9 API knowledge files already in 20-Domains/APIs/

### BHAG: Source Code Access
- **time2work is C#/.NET** — if Claude Code gets read access to the codebase, the Knowledge Engine understands the system from the inside out
- Business logic, rules engine, pay calculation logic, data model, validation rules — all learnable from code
- This is the difference between "knows the API" and "knows how the system actually works"
- Requires management approval — IP and trust conversation
- Even without code access, API + OData + SQL gives us a lot to work with

## What Already Exists

- nimbus API documentation already partially captured: [[nimbus-authentication]], [[nimbus-rest-crud-pattern]], [[nimbus-odata-field-naming]], [[nimbus-idorfilter-patterns]], [[nimbus-entity-creation-order]], [[nimbus-api-endpoints]]
- These live in `20-Domains/APIs/` in the vault
- PostgreSQL database exists (partially working, connectivity issues noted)
- MCP Memory knowledge graph exists but was empty on last check

## What's Hard (from Doc 1 §6.2)

- **Knowledge curation quality.** The AI is only as good as the knowledge it has. Building a comprehensive, accurate Knowledge Engine for time2work requires months of feeding it documentation, API specs, rule type definitions, and real-world implementation patterns. No shortcut.
- **Edge cases.** Most Award configurations follow clear patterns. But unusual combinations of allowances, overlapping conditions, client-specific EA variations still require human judgment. The system must flag uncertainty rather than guess.

## Phase 1 Deliverables (from Doc 4)

- [ ] Swagger spec ingestion into knowledge base
- [ ] Playwright discovery of time2work screens
- [ ] Knowledge search API (text + vector)
- [ ] Basic knowledge versioning
- [ ] Monash-specific knowledge base populated (EAs, config) — for Phase 2

## Dependencies

- Requires [[orchestration-infra/README|Orchestration & Infrastructure]] — database, pgvector, auth
- Feeds into [[integration-hub/README|Integration Hub]] — API knowledge used by connectors
- Feeds into [[ps-accelerator/README|PS Accelerator]] — knowledge drives config generation
- Feeds into [[quality-compliance/README|Quality & Compliance]] — Award knowledge drives test scenarios
- Feeds into [[support-defect-intel/README|Support & Defect Intelligence]] — knowledge lookup for triage

## Talking Points (from Docs)

> "Think of it as giving nimbus a brain that knows every client, every configuration, every Award rule type, every implementation pattern. Then making that brain available to every person in the company."

> "Every implementation we do teaches the system something. After 10 clients, it's good. After 50 clients, it's exceptional. The knowledge compounds."

## Open Questions

- [ ] What time2work API documentation exists today? Swagger specs available?
- [ ] What Award/EA documentation exists in structured form?
- [ ] How much implementation knowledge is in Confluence vs people's heads?
- [ ] What's the Playwright discovery scope — all screens or key workflows first?

---
*Source: Doc 1 §3.1 Component 1, §6.2 | Doc 4 §3.2 WS1 | Created: 2026-02-19*

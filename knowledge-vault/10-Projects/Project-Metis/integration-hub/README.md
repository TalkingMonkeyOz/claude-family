---
tags:
  - project/Project-Metis
  - area/integration-hub
  - scope/system
  - level/1
  - phase/1
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
synced: false
---

# Integration Hub

> **Scope:** system (generic platform capability — connector targets configured per customer)
>
> **Design Principles:**
> - Every integration is bidirectional — read from systems AND write back insights
> - Standardised connector pattern — each external system gets a dedicated module with retry, rate limiting, health checks
> - Business logic never calls external APIs directly — always through connectors (allows mocking for testing)
> - Credential rotation without system restart

> The nervous system. How the platform connects to the customer's product and every tool they use.

**Priority:** CRITICAL — Phase 1
**Status:** ✓ BRAINSTORM-COMPLETE (Area 2-5 sweep — plumbing, not a design problem)
**Parent:** [[Project-Metis/README|Level 0 Map]]

## What This Area Covers

Connectors to every external system. Bidirectional — reads from them, writes back insights, reports, and automation outputs. The platform becomes the intelligence layer that sits between all these tools.

## Design Principle (from Doc 4 §10)

> Every integration is bidirectional. We don't just read from systems — we write back insights, reports, and automation outputs.

## Connector Pattern (from Doc 4 §4.4)

Every external system connects through a standardised integration layer:

- **Dedicated connector module** per system — no direct API calls from business logic
- **Retry logic** — exponential backoff with jitter, circuit breaker for persistent failures
- **Rate limiting** — respect external API limits, queue requests when approaching limits
- **Credential rotation** — support credential refresh without system restart
- **Health checks** — regular connectivity checks, alert on failures
- **Abstraction layer** — business logic never calls external APIs directly. Always through connectors. Allows mocking for testing

## Integrations Brainstorm

### time2work REST API (CRITICAL)
- Full CRUD operations against all time2work endpoints
- Authentication and token management
- Rate limiting
- Existing knowledge: [[nimbus-authentication]], [[nimbus-rest-crud-pattern]], [[nimbus-api-endpoints]]
- **What we get:** Configurations, user data, scheduling data, payroll outcomes
- **What we give back:** Generated configs, validated imports, compliance reports

### time2work OData (CRITICAL)
- Read access to reporting and data extraction endpoints
- Existing knowledge: [[nimbus-odata-field-naming]]
- **What we get:** Reporting data, data extracts
- **What we give back:** Analytics, trend data

### Jira — Monash Instance (HIGH)
- Already working via MCP
- Needs: automated defect creation, status syncing, sprint tracking
- **What we get:** Defect status, sprint progress, requirements
- **What we give back:** Automated defect creation, status syncing, collation reports

### Jira — Nimbus Instance (HIGH)
- Already working via MCP
- **What we get:** Internal defects, backlog, development progress
- **What we give back:** Cross-reference with client issues, impact analysis

### Confluence (MEDIUM)
- REST API or MCP
- **What we get:** Existing documentation, knowledge base
- **What we give back:** Auto-generated docs, gap analysis, freshness monitoring

### Salesforce (MEDIUM)
- REST API
- **What we get:** Timesheets, project data, client records
- **What we give back:** Automated time analysis, project health scoring

### Granola (MEDIUM)
- API or MCP
- **What we get:** Meeting transcripts, action items
- **What we give back:** Decision tracking, scope change detection

### Slack (LOW — already connected)
- MCP
- **What we get:** Team communications, notifications
- **What we give back:** Status updates, alerts, agent reports

### Excel/CSV Pipeline (HIGH — for data import)
- Import/export for customer data, configuration sets, test scenarios
- This is where [[nimbus-import|User Loader v2]] concepts live
- Standardised templates with validation

### Azure (INFRASTRUCTURE)
- SDK/CLI
- **What we get:** Infrastructure, hosting, Key Vault
- **What we give back:** Deployment automation, monitoring

## What Already Exists

- Jira MCP connected to both Monash and Nimbus instances — working
- Slack MCP connected — working
- Atlassian MCP connected — working
- nimbus API knowledge documented in vault (9 files in 20-Domains/APIs/)

## Existing Tool AI Features (from Doc 3 §5.1)

These are already paid for and should be enabled immediately:

| Tool | AI Feature | Limitation |
|------|-----------|-----------|
| Atlassian Intelligence | Summarise tickets, draft content, NL JQL | No nimbus domain knowledge |
| Atlassian Rovo | Cross-tool search, chat with data | Shallow reasoning, no bespoke modelling |
| Copilot (Corporate) | Email drafting, document summarisation | General purpose, zero nimbus expertise |
| Granola | Bot-free transcription, AI summaries | Meetings only, no cross-system integration |

**Key insight:** These are useful for general productivity. None know anything about time2work, Australian Awards, or nimbus implementation methodology.

## Phase 1 Deliverables (from Doc 4)

- [ ] time2work API connector with auth
- [ ] time2work OData connector
- [ ] Jira integration enhanced (automated defect creation, status sync)
- [ ] Connector pattern established and documented

## Dependencies

- Requires [[orchestration-infra/README|Orchestration & Infrastructure]] — credential storage, auth, environments
- Feeds [[knowledge-engine/README|Knowledge Engine]] — API specs ingested as knowledge
- Feeds [[ps-accelerator/README|PS Accelerator]] — connectors used for config generation and data import
- Feeds [[support-defect-intel/README|Support & Defect Intelligence]] — Jira integration for triage

## Open Questions

- [ ] What API/OData access can nimbus provide for the Monash instance? (read first, write for testing)
- [ ] Are there rate limits on the time2work API that constrain us?
- [ ] Which Confluence spaces are relevant?
- [ ] What Salesforce data model does nimbus use for timesheets/projects?

---
*Source: Doc 4 §3.2 WS2, §4.4, §10 | Doc 3 §5.1 | Doc 1 §5.5 | Created: 2026-02-19*

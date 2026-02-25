---
tags:
  - project/Project-Metis
  - area/delivery-accelerator
  - scope/system
  - level/1
  - phase/2
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
synced: false
---

# Delivery Accelerator

> *Formerly "Professional Services Accelerator" — renamed to generic framing (Feb 23 stocktake)*
> *Vault folder still `ps-accelerator/` — rename when convenient*

> **Scope:** system (generic platform capability, configured per customer)
>
> **Design Principles:**
> - Requirements → configuration → test → release → documentation is the universal pipeline
> - AI does the repetitive work, humans handle judgement calls and edge cases
> - Every engagement teaches the system — knowledge compounds across customers
> - Living documentation generated from system state, never written from memory

> The muscle for client delivery. Turning knowledge into configurations and deployments.

**Priority:** HIGH — Phase 2
**Status:** ✓ BRAINSTORM-COMPLETE (Area 2-5 sweep — 5 decisions resolved)
**Parent:** [[Project-Metis/README|Level 0 Map]]

## What This Area Covers

AI-assisted client implementation pipeline: requirements gathering, configuration generation, data import/validation, release management, and living documentation. This is where the Monash POC and User Loader v2 live.

## The Transformation (from Doc 1 §5)

### Today (Manual)
1. Consultant gathers requirements — meetings, emails, spreadsheets
2. Consultant manually configures time2work — slow, error-prone
3. Customer provides data in various formats — inconsistent, needs cleanup
4. Testing done manually — incomplete coverage, time-consuming
5. Documentation written by hand — often incomplete, quickly outdated
6. Go-live — fingers crossed, issues found in production
7. Support picks up — no context from implementation, starts from scratch

### Future (AI-Assisted)
1. AI helps gather and validate requirements — structured, complete, consistent
2. AI generates configuration from validated requirements — fast, auditable
3. AI validates and transforms customer data — standardised templates
4. AI generates pay scenarios, runs them, compares expected vs actual — comprehensive
5. Documentation generated from actual configuration — always current
6. Go-live with confidence — validated, documented, tested
7. Support has full context — AI knows the implementation history

## Brainstorm Items

### Requirements Collation & Interpretation (from Doc 2 §2.1)
- AI collates inputs from meetings, emails, docs into structured requirements
- Gaps and ambiguities flagged before configuration begins
- Every configuration traced back to a validated requirement
- Consistent structured approach regardless of which consultant runs the project

### Configuration Generation (from Doc 4 WS4)
- Generate time2work configurations from validated requirements
- Follow known patterns from the [[knowledge-engine/README|Knowledge Engine]]
- Human review for edge cases and client-specific exceptions
- Audit trail for every generated configuration

### Data Import/Validation (User Loader v2)
- Bulk data operations with validation
- Standardised templates for customer data
- Intelligent data validation and transformation
- The User Loader v2 PRD exists (separate document — not in vault yet)

### Release Management (from Doc 2 §2.4)
- Controlled deployment: development → UAT → production
- Each release versioned, tested, documented before promotion
- UAT validation must pass before production deployment
- Rollback capability
- Audit trail for every configuration change and deployment

### UAT-to-Production Promotion
- Move tested configurations safely between environments
- Change detection — identify what changed between versions
- Client visibility into what changed and why at every step

### Living Documentation (from Doc 2 §2.5)
- Documentation generated from actual project state, not written from memory
- Every configuration change, test result, deployment captured
- Client-facing documentation in plain language
- Always current — updates when the system updates
- Multi-format: Word docs, Confluence pages, PDFs, web pages

### Template Library
- Reusable configuration templates by industry vertical
- Each client implementation builds the library for the next one
- Healthcare templates, higher ed templates, government templates, etc.

## Monash POC (from Doc 2)

Monash is the first proof of concept — proving the entire pipeline on one client.

**Why Monash:**
- Existing client, trust established
- Complex enough to prove value (multiple EAs, casual academics, semester patterns)
- Creates a repeatable template for future clients

**Timeline:** 8-10 weeks from approval
| Phase | Weeks | Deliverable |
|-------|-------|------------|
| Knowledge Engine setup | 1-2 | time2work knowledge base, API integration, Monash data ingested |
| Requirements & Architecture | 2-4 | Structured requirements, security architecture, integration design |
| Configuration & Testing | 4-6 | Rules configured, pay scenarios validated, iterative testing |
| Release & Documentation | 6-8 | First release through UAT, living docs, release notes |
| Production & Handover | 8-10 | Production deployment, client training, subscription begins |

**Success criteria:**
- [ ] Requirements collated in hours, not weeks
- [ ] Rule configs generated and validated automatically
- [ ] Pay scenario testing catches errors before go-live
- [ ] Documentation generated from actual project state
- [ ] Monash considers the service worth the monthly subscription
- [ ] Client would recommend the approach to others

## The Compounding Effect (from Doc 2 §5)

| Phase | Timeline | What Happens |
|-------|----------|-------------|
| Monash POC | Months 1-3 | Prove pipeline on one client |
| Second client | Months 4-6 | Apply template, Knowledge Engine gets smarter |
| Standardise | Months 6-9 | Package repeatable elements, reduce setup time |
| Scale | Months 9-12 | 3-5 active clients, each teaches the system |
| Vertical depth | Year 2 | Deep capability in healthcare, higher ed, government |

> "Every client makes the system smarter. Monash teaches us higher education. The next client teaches us healthcare. By client five, the Knowledge Engine has patterns that no individual consultant could carry in their head."

## Productivity Impact (from Doc 1 §4.1)

> A 10% productivity improvement across a 20-person PS team = equivalent of 2 additional FTEs — without recruitment cost, onboarding time, or salary overhead.

Other benefits:
- Knowledge retention when consultants leave
- Consistency across implementations
- Faster onboarding of new staff (months → weeks)
- Reduced rework and error rates
- Audit-ready documentation for regulated industries

## Dependencies

- Requires [[knowledge-engine/README|Knowledge Engine]] — knowledge drives config generation
- Requires [[integration-hub/README|Integration Hub]] — time2work API for config deployment, Jira for tracking
- Feeds [[quality-compliance/README|Quality & Compliance]] — configs need testing
- Feeds [[support-defect-intel/README|Support & Defect Intelligence]] — implementation context for support

## Open Questions

- [ ] Is Monash the right first POC? Who engages the client?
- [ ] What Monash-specific documentation and config details exist?
- [ ] Is the proposed 8-10 week timeline realistic given Monash's availability?
- [ ] Where does the User Loader v2 PRD live? Needs to be brought into vault.

---
*Source: Doc 1 §5 | Doc 2 (all) | Doc 4 §3.2 WS4, WS6 | Created: 2026-02-19*

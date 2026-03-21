---
tags:
  - project/Project-Metis
  - scope/system
  - type/feature-catalogue
created: 2026-02-26
updated: 2026-03-07
---

# METIS Feature Catalogue

10 user-facing features with concrete nimbus/Monash examples. Each feature describes: who uses it, what they see, what happens behind the scenes, and a real-world example.

**Relationship to Gate Framework:** These features are inputs to Gate 1 (Process Inventory, Actor Map) and Gate 2 (BPMN, Journey Maps, Data Model). Each feature implies processes, actors, data entities, and business rules that must be captured in the gate deliverables. See `design-lifecycle.md` for the full gate framework (Gates 0-4, 31 deliverables).

## Feature 1: Ask the Knowledge Engine a Question

**Who:** Everyone — consultants, support staff, project managers, developers.

**What they see:** Chat-style interface. Type a question, get an answer with source citations and confidence indicator. Sources are clickable. For code queries, results include symbol signatures, file locations, and dependency context.

**Behind the scenes:**
1. Haiku classifier checks on-topic (Layer 3 constrained deployment)
2. Query to /ask endpoint
3. Vector search finds top-N relevant knowledge items AND code symbols (shared embedding space)
4. Graph walk (1-2 hops) finds structurally connected items; for code, recursive CTE traverses call chains and dependencies
5. Claude assembles answer from retrieved context (documents + code)
6. Confidence score from similarity scores + source count
7. Response with source citations, confidence badge, feedback button
8. Query, results, feedback logged for evaluation

**Content types:** The Knowledge Engine supports pluggable content types (Decision #4). Documents and code share the same pipeline pattern (parse → chunk/extract → embed → store → search → rank) with different parsers per type. Documents use sentence-boundary chunking; code uses tree-sitter AST parsing into `code_symbols` with structural `code_references`. Both use Voyage AI embeddings in the same vector space, enabling cross-content-type semantic search.

**nimbus/Monash example (documents):** Consultant asks: "How do I configure penalty rates for casual academics under the Monash EA?" Engine retrieves: Monash EA rule types, time2work API endpoint for penalty rate config, two implementation patterns from previous higher-ed setups. Answer explains which rule types, which parameters, links to API docs. Confidence: HIGH. Consultant completes in 20 min instead of 2 hours.

**nimbus/Monash example (code):** Developer asks: "Where is holiday loading calculated?" Engine retrieves: `calculateHolidayLoading()` in payroll-engine, its callers, the Award rule type it implements, plus the Monash EA business rule. Developer sees both the code AND the business logic in one answer.

---

## Feature 2: Ingest New Knowledge

**Who:** Senior consultants, administrators, system auto-ingestion.

**What they see:** Ingestion form or API call. Select knowledge type, paste/upload content, add tags. System shows category, validation tier, next steps.

**Behind the scenes:**
1. Content received, type determined (document, API spec, code repository, etc.)
2. Parser selected per content type: sentence-boundary chunking for documents, tree-sitter AST parsing for code
3. Voyage AI generates embeddings (shared vector space across all content types)
4. Documents stored in `knowledge_items`/`knowledge_chunks`; code stored in `code_symbols`/`code_references`
5. Validation tier routing: T1 auto-approve, T2 senior review queue, T3 searchable with low-confidence flag, T4 always flagged
6. AI suggests relationships to existing knowledge (background); for code, cross-references (calls, imports, extends) auto-extracted from AST
7. Audit trail logged

**Code ingestion specifics:** When a code repository is onboarded, tree-sitter parses source files into symbols (functions, classes, methods, interfaces). Structural references between symbols are extracted automatically. File hashes enable incremental re-indexing — unchanged files are skipped. Auto-indexed on project onboard (Decision #3: opt-in = forgotten). Multi-language: Python, TypeScript, JavaScript, C#, Rust.

**nimbus/Monash example (documents):** time2work v14.2 releases new bulk rostering API endpoint. Swagger spec uploaded, auto-chunked per endpoint, Tier 1 auto-approved. Minutes later, any consultant asking about bulk rosters gets the new endpoint. Separately, a senior consultant documents a semester scheduling pattern — goes in as Tier 2, queued for peer validation.

**nimbus/Monash example (code):** Nimbus onboards their time2work integration codebase. Tree-sitter indexes 2,400 symbols across 180 files. METIS discovers 3 duplicate implementations of penalty rate calculation, flags them via collision detection. Next developer session, METIS automatically provides the canonical implementation instead of letting a 4th copy be written.

---

## Feature 3: Create a Client Engagement and Configure the Delivery Pipeline

**Who:** Project managers, delivery leads.

**What they see:** Setup wizard. Select customer, create engagement, specify pipeline stages (requirements, config, testing, deployment, documentation). Configure BPMN gates per stage.

**Behind the scenes:**
1. Engagement record created with client isolation
2. Client-specific knowledge scope created
3. Delivery pipeline instantiated from template (BPMN process #2)
4. Connector configured for client's systems
5. Constrained deployment configured with client-specific context
6. Audit trail begins

**nimbus/Monash example:** John creates Monash engagement. Selects "Higher Education" vertical template — pre-configures academic calendar awareness, casual scheduling patterns, multi-EA support. Monash knowledge scope created, Jira connected, 5-stage pipeline with first gate requiring signed-off requirements document.

---

## Feature 4: Generate Configuration from Requirements

**Who:** Implementation consultants.

**What they see:** Structured requirements doc + "Generate Configuration" button. System produces proposed config with traceability: requirement → configuration → reasoning. Review, adjust, approve.

**Behind the scenes:**
1. Requirements parsed into structured format
2. KE queried for matching implementation patterns
3. Configuration generated using API schema knowledge + patterns
4. Each config item traced to source requirement
5. Uncertainty flagged explicitly
6. Presented for human review
7. Approved config pushed to UAT via API connector

**nimbus/Monash example:** Requirement: "Casual academics after 6pm weekdays get 25% loading." System maps to Shift Allowance rule type, generates config with parameters, flags: "Confirm whether this applies during exam periods — previous implementations had an exception." Consultant confirms, config pushed to Monash UAT.

---

## Feature 5: Run Validation Tests and Review Results

**Who:** Testers, consultants, delivery leads.

**What they see:** Test dashboard: scenarios (generated from config), run status, pass/fail, expected vs actual with highlighted differences for failures.

**Behind the scenes:**
1. Test scenarios generated from configurations (inputs → expected outputs)
2. Submitted to time2work via API (or Playwright for UI tests)
3. Actual outputs captured
4. Expected vs actual comparison
5. Discrepancies flagged with severity and potential cause
6. Results logged for regression baseline
7. BPMN gate: critical tests must pass before deployment unlocked

**nimbus/Monash example:** Penalty rate config generates 8 scenarios. Six pass. Two fail: exam period exception not configured, Saturday casuals getting weekday rate. Both flagged with specific config mismatches. Consultant fixes, reruns, all pass. Deployment gate unlocked.

---

## Feature 6: Capture and Triage a Defect

**Who:** Anyone — consultants, testers, support staff, clients.

**What they see:** Defect capture form. Describe in natural language. System structures it (steps, expected, actual, environment, severity suggestion). Shows duplicates. Routes to queue.

**Behind the scenes:**
1. Natural language received
2. AI structures (steps, expected, actual, environment, module)
3. Semantic duplicate check
4. Cross-client impact check
5. Severity suggested from impact analysis
6. Routed via BPMN process #3
7. Linked to delivery pipeline if applicable
8. Synced to external Jira via connector

**nimbus/Monash example:** Monash HR reports: "Timesheets for public holiday casuals show $0 holiday loading." System structures it, identifies module (payroll → holiday loading), finds similar resolved issue from another client (rule priority fix). Suggests probable cause before consultant opens ticket.

---

## Feature 7: Generate Documentation from System State

**Who:** Delivery leads, consultants, client stakeholders.

**What they see:** "Generate Docs" action on engagement. Choose type (config summary, test report, release notes, full implementation docs). Output as Word, PDF, or Confluence page.

**Behind the scenes:**
1. Reads actual configuration from time2work via API
2. Maps config to requirements (traceability)
3. Pulls test results
4. Pulls release history
5. Assembles using audience-appropriate templates
6. Generated doc versioned and stored

**nimbus/Monash example:** Monash requests Configuration Compliance Report for audit. System generates 30-page doc: every Award rule configured, which EA clause it implements, test scenarios, results, who approved, deployment dates. Generated in minutes from actual system state, not written from memory.

---

## Feature 8: Review Project Health Dashboard

**Who:** Project managers, delivery leads, management.

**What they see:** Dashboard: engagement status across pipeline stages, open defects by severity, test coverage %, documentation completeness, KE query volume/accuracy, health score.

**Behind the scenes:**
1. Data aggregated from pipeline, defects, tests, docs, KE logs
2. Health score from weighted combination
3. Alerts for stale defects, failed tests, doc gaps, declining accuracy
4. Drill-down to any metric

**nimbus/Monash example:** Management views Monash dashboard. Score: 82/100. Green on testing (95% pass), green on docs (auto-generated). Amber on defects (3 open, 1 stale 5 days). Red flag: config deployed without completing UAT gate (BPMN violation). Real-time visibility from actual system data, not consultant status reports.

---

## Feature 9: Promote Knowledge from Client to Product Level

**Who:** Senior consultants, knowledge managers.

**What they see:** "Promote" action on client-specific knowledge. System shows: this pattern was used for Monash but applies generically. Review generalised version, approve, becomes available across all engagements.

**Behind the scenes:**
1. Client-specific item selected for promotion
2. System generates generalised version (strips client details, keeps pattern)
3. Presented to senior reviewer
4. If approved: new product-level item with `supersedes` relationship
5. Future engagements in same vertical benefit
6. Original client-specific item remains (client-isolated)

**nimbus/Monash example:** Consultant discovers 13-week planning horizon aligned to semesters with 2-week exam buffer works best. Promotes it: system generalises to "Higher Education Semester Scheduling Pattern." Available to every future university client. By client #5, the KE has a comprehensive university playbook built from real engagements.

---

## Feature 10: Configure a Constrained Deployment for a Specific Role

**Who:** Platform administrators, deployment leads.

**What they see:** Deployment config screen. Select audience (consultants, support, clients), knowledge scope (all nimbus, Monash-only, support-only), tools (full/read-only/none), personality (technical/plain-language/formal).

**Behind the scenes:**
1. System prompt assembled from template + configuration
2. Knowledge scope defined (categories + client scopes)
3. Cached system prompt populated (up to 200K tokens)
4. Haiku classifier configured for scope
5. Tool restriction applied
6. Tested with 5 evaluation questions
7. Published to channel (web UI, Slack, API)

**nimbus/Monash example:** Three deployments created: (1) Internal Support Assistant — full knowledge, all tools, technical tone. For consultants. (2) Monash Support Bot — Monash knowledge only, read-only, plain language. For Monash HR staff. (3) Sales Demo Assistant — product knowledge + case studies, no client data, confident tone. For pre-sales. Same platform, same KE, three constrained deployments.

---

## Feature → Phase Mapping

| Feature | Phase 1 | Phase 2 (MVP) | Phase 3 |
|---------|---------|---------------|---------|
| F1: Ask KE | ✅ Full | — | — |
| F2: Ingest Knowledge | ✅ Full | Governed (BPMN) | — |
| F3: Create Engagement | — | ✅ Full | — |
| F4: Generate Config | — | ✅ Full | — |
| F5: Validation Tests | — | ✅ Full | — |
| F6: Defect Triage | — | ✅ Full | — |
| F7: Generate Docs | — | ✅ Full | — |
| F8: Health Dashboard | — | Data exists | ✅ Full |
| F9: Promote Knowledge | — | — | ✅ Full |
| F10: Constrained Deploy | ✅ Basic | Monash-specific | Multi-role |

---
**Version**: 1.1
**Created**: 2026-02-26
**Updated**: 2026-03-22
**Location**: knowledge-vault/10-Projects/Project-Metis/feature-catalogue.md

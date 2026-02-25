---
tags:
  - project/Project-Metis
  - area/delivery-accelerator
  - scope/system
  - type/brainstorm
  - phase/2
projects:
  - Project-Metis
created: 2026-02-24
synced: false
---

# Delivery Accelerator — Brainstorm Capture

> The engine that runs client delivery work through the platform. Requirements → configuration → test → deploy → documentation.

**Date:** 2026-02-24
**Session:** Focused brainstorm within Area 2-5 sweep

---

> **DESIGN PRINCIPLES — READ BEFORE EDITING**
>
> 1. **This is a generic product design.** The pipeline serves any development house delivering any product. Customer-specific examples (nimbus, Monash) are illustrations only.
> 2. **BPMN-driven pipeline.** The delivery pipeline is a BPMN process definition, not hardcoded logic. Configurable within system-enforced boundaries.
> 3. **AI does the repetitive work, humans handle judgement.** Every AI output has a human review checkpoint before it reaches a client.
> 4. **Every engagement teaches the system.** Knowledge compounds — patterns from one client benefit the next through the Knowledge Engine promotion mechanism.
> 5. **Documentation is generated from system state, not written from memory.** But "living" means "never more than a day out of date," not real-time magic.

---

## 1. The Generic Pipeline

Every client delivery engagement follows this shape, regardless of product or industry:

```
Requirements → Configuration → Validation/Test → Deployment → Documentation → Support Handoff
```

Not every engagement needs every stage. The pipeline is BPMN-defined and configurable.

### Pipeline Stages (Generic)

| Stage | What Happens | AI Role | Human Role |
|-------|-------------|---------|------------|
| **Requirements** | Gather, structure, validate client needs | Collate from meetings/emails/docs, flag gaps and ambiguities | Validate with client, make judgement calls on ambiguities |
| **Configuration** | Generate product configuration from requirements | Generate config from requirements + known patterns (KMS) | Review generated config, handle edge cases and exceptions |
| **Validation/Test** | Verify configuration produces correct outcomes | Generate test scenarios, run them, compare expected vs actual | Review discrepancies, approve test coverage, sign off |
| **Deployment** | Move validated config through environments | Package changes, manage versions, deploy through UAT → prod | Approve promotion to production, monitor post-deployment |
| **Documentation** | Generate project docs and release notes | Generate from actual system state (DB, config, test results) | Review for accuracy, add context only humans know |
| **Support Handoff** | Transfer implementation context to support | Full engagement history available in KMS | Confirm handoff completeness |

### How It Ties to Lifecycle Tiers (Chat #9)

The Delivery Accelerator is the engine that runs **Tier 2** and **Tier 3** work:

- **Tier 2 (structured with sign-off):** Customer deliverables go through this pipeline. Client approval is the gate. Sign-off doc is what you invoice against.
- **Tier 3 (rigid pipeline):** Code and deployment work goes through this pipeline PLUS the five-layer validation stack (DDD → BPMN → DMN → Ontology → Event Sourcing).
- **Tier 2 can escalate to Tier 3** if signed-off work requires code changes.

Tier 1 work (knowledge queries, low risk) does NOT go through this pipeline — it's handled directly by the Knowledge Engine.

---

## 2. Three-Tier Gate Model

Pipeline stages have gates. Gates have three tiers of rigidity — decided Feb 24 brainstorm with John:

### Mandatory Gates (System-Enforced)
- Cannot be disabled by customer
- Protect the integrity of the platform and the delivery
- Examples: "configuration must be validated before deployment", "sign-off required before production", "test results must exist before UAT promotion"
- BPMN enforced — the process literally will not advance without these

### Default-On, Toggleable Gates
- Enabled by default because best practice
- Customer can choose to disable for specific engagements
- Examples: "generate documentation after deployment" (strongly recommended but maybe a small engagement doesn't need full docs), "automated regression test before release"
- Configured per customer deployment, not per engagement (engagement can request toggle but customer admin approves)

### Optional/Addable Gates
- Not in the default pipeline but available to enable
- Customer-specific needs: extra compliance approval gate, data migration validation step, third-party review checkpoint
- Added by extending the BPMN definition for that customer's deployment

### Who Controls What

| Tier | Who Can Change | How |
|------|---------------|-----|
| Mandatory | Platform team only | New platform version |
| Default-on | Customer admin (with platform team guidance) | Customer deployment configuration |
| Optional | Customer admin (with platform team guidance) | Customer deployment configuration |
| Custom stages | Platform team builds, customer admin enables | BPMN process extension |

**Year 2+ vision:** Expose more configurability to customers directly. "At their own peril" — but only after the system is proven stable and there's enough guardrails.

---

## 3. Living Documentation — Honest Model

"Living documentation" does NOT mean real-time magic. It means documentation that's generated from actual system state on a defined schedule, never more than a day out of date, and always flagged for human review before reaching clients.

### Three-Speed Update Model

**Real-time (as work happens)**
- Decisions written to DB as they're made
- Configuration changes recorded when applied
- Test results stored when tests run
- Engagement activity logged continuously
- This is just normal system operation — the DB is always current

**Periodic (triggered or scheduled, ~4x daily)**
- New knowledge items get RAG embeddings generated
- Knowledge relationships reassessed when new items are added
- Cross-references updated
- Triggered by ingestion events, or on schedule if batch ingestion

**Nightly batch**
- Code checked in during the day gets reviewed and documented
- KMS updated with new patterns, resolutions, learnings from the day
- RAG embeddings reassessed for changed content
- User-facing articles, manuals, and documentation regenerated from current system state
- Links and relationships reviewed
- **Everything flagged for human review** — system generates, human confirms
- Client-facing documentation only updated after human approval

### What This Means in Practice

- A consultant makes configuration changes during the day → DB records them immediately
- At night, the system regenerates the client's configuration documentation from the DB
- Next morning, the documentation is flagged for the consultant to review
- Once approved, it's the current, accurate documentation
- If the consultant changed something yesterday that conflicts with a previous decision, the system flags that too

### Dependencies
- Requires Orchestration (Area 7) for scheduling batch jobs
- Requires Knowledge Engine (Area 1) for embedding and relationship management
- Requires Project Governance (Area 6) for work item tracking and sign-off workflows

---

## 4. Template Library

Every engagement builds the library for the next one. This is the compounding effect.

- The system ships with empty templates (pipeline structure, document formats, test frameworks)
- First customer engagement populates templates with real content
- Patterns promoted from engagement → client → product level via Knowledge Engine promotion mechanism
- Over time, vertical-specific templates emerge (healthcare, education, government, retail)
- Templates are starting points, not rigid moulds — every engagement can customise

### How Templates Connect to Knowledge Engine

Templates ARE knowledge items in the KMS (Category C: Delivery Knowledge). They follow the same scope hierarchy, validation tiers, and promotion mechanism. No separate template system needed.

---

## 5. Example: How This Works for a Customer (nimbus/Monash)

> This section illustrates the generic pipeline with a specific customer example. The pipeline shape is the same for any customer.

**Customer:** nimbus (workforce management software company)
**Product:** time2work (scheduling and payroll)
**Client:** Monash University
**Engagement:** Initial AI-assisted implementation

| Generic Stage | nimbus-Specific Implementation |
|--------------|-------------------------------|
| Requirements | Gather Monash's EA requirements, scheduling patterns, casual academic rules |
| Configuration | Generate time2work rule configurations from Monash requirements + known Award patterns |
| Validation/Test | Generate pay scenarios from rule configs, run through time2work API, compare expected vs actual payroll outcomes |
| Deployment | Promote validated config through Monash UAT → production environments |
| Documentation | Generate Monash-specific configuration docs, release notes from actual system state |
| Support Handoff | Full Monash engagement context available in KMS for support team |

**Success criteria (from Doc 2):**
- Requirements collated in hours, not weeks
- Rule configs generated and validated automatically
- Pay scenario testing catches errors before go-live
- Documentation generated from actual project state
- Client considers the service worth the monthly subscription

---

## 6. Open Questions

- [ ] What's the minimum viable pipeline for the first customer? (All 6 stages, or start with a subset?)
- [ ] How does the BPMN pipeline definition get created for a new customer? Manual by platform team, or semi-automated from customer profile?
- [ ] Template library cold-start problem — first customer has no templates. How much manual seeding is needed?
- [ ] How does the platform handle products without APIs? (Manual configuration only, no automated deployment stage)
- [ ] Data import/validation (User Loader v2 concept) — is this a stage in the pipeline or a standalone tool? User Loader v2 PRD exists separately, needs integrating.
- [ ] Multi-product customers — does each product get its own pipeline instance?

---

## 7. Decisions Made (This Session)

| Decision | Outcome | Reference |
|----------|---------|-----------|
| Pipeline gate model | Three tiers: mandatory (system-enforced), default-on (toggleable), optional (addable). BPMN-driven. | This doc §2 |
| Living documentation model | Three speeds: real-time DB writes, periodic embedding (~4x daily), nightly batch regen with human review flags | This doc §3 |
| Relationship to lifecycle tiers | Delivery Accelerator runs Tier 2 and Tier 3 work. Tier 1 bypasses it. | This doc §1 |
| Customer pipeline control | Platform team controls mandatory gates. Customer admin configures toggleable/optional. Full customisation is Year 2+ | This doc §2 |
| Templates are KMS items | Templates live in Knowledge Engine as Category C knowledge. No separate template system. | This doc §4 |
| Monash as example only | All design is generic. nimbus/Monash is an illustrative example, not the design target. | This doc §5 |

---

*Source: Focused brainstorm session Feb 24 2026 with John*
*Parent: [[ps-accelerator/README|Delivery Accelerator README]]*
*Next: Update README with decisions, update decisions tracker*

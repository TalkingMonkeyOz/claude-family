---
tags:
  - session-handoff
  - scope/system
projects:
  - Project-Metis
created: 2026-02-23
---

# ⚠️ READ THIS FIRST — Session Handoff Protocol

**Why these handoffs exist:** Claude has no memory between chats. Each new conversation starts blank. These handoffs are the bridge — they carry context, decisions, and status forward so the next session doesn't repeat work or contradict previous decisions.

**What to do at the START of every new chat:**
1. Read the **latest session handoff** from this folder (most recent date)
2. Read the **Master Tracker** (`nimbus_master_tracker.docx` in the claude.ai project files)
3. Read the **area-specific vault folder** for whatever topic you're working on
4. Read the **Product Definition** (`system-product-definition.md`) if framing system-level work

**What to do at the END of every chat:**
1. Write a session handoff to this folder: `C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\session-handoffs\`
2. Write/update the area brainstorm capture in the relevant vault subfolder
3. Update the memory graph with key decisions and status changes
4. Note what the next session should pick up

**Where things live:**
- **Vault (source of truth for design):** `C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\`
- **Project docs (polished documents):** claude.ai project files (Doc 1-6, Master Tracker, Meeting Handout)
- **Memory graph:** Persistent across chats — use for key facts, decisions, status

---

# Session Handoff: BPMN / SOP & Enforcement (Area 9)

**Date:** 2026-02-23
**Session:** Focused Chat #1 — Enforcement layer & workflows
**Chat:** Claude Desktop (claude.ai project)

## What Happened This Session

1. **Area 9 brainstorm completed** — full capture of the enforcement layer design at appropriate depth for brainstorm phase.

2. **Two levels of enforcement identified:**
   - Level 1: User/business workflows (process maps for humans and systems)
   - Level 2: AI process enforcement (making Claude agents follow processes reliably)

3. **Three-tier enforcement model designed (B/C/E Hybrid):**
   - Tier 1: SpiffWorkflow runtime — high stakes (compliance, deployments, client data)
   - Tier 2: Checklist + validation gates — structured, lower stakes
   - Tier 3: Prompt + conventions — low stakes, human evaluates output

4. **Three components designed together:**
   - Component 1: Persistent Workflow Engine (SpiffWorkflow + PostgreSQL state)
   - Component 2: DMN Decision Tables (rules out of code, into structured tables)
   - Component 3: Gap Detection & Compliance Metrics (feedback loop)

5. **SpiffWorkflow research completed** — confirmed as the right tool. Already in Claude Family (50 processes, 490 tests). Key gaps: no persistence, DMN installed but unused.

6. **SpiffWorkflow chosen over Camunda** — already proven, pure Python, lightweight, open source.

7. **9 candidate processes mapped** across platform areas with tier assignments.

## Files Created/Updated

- **CREATED:** `bpmn-sop-enforcement/brainstorm-capture-enforcement-layer.md` — full Area 9 brainstorm with frontmatter
- **UPDATED:** Memory graph — nimbus_ai_platform and SpiffWorkflow Integration entities

## Key Decisions

| Decision | Outcome |
|----------|---------|
| Enforcement engine | SpiffWorkflow (over Camunda) — already proven in Claude Family |
| Enforcement model | Three-tier: SpiffWorkflow / Checklist+validation / Prompt+conventions |
| DMN activation | Recommended — installed but unused, natural fit for routing/classification |
| Persistence gap | Biggest weakness identified — SpiffWorkflow can serialize, but not wired up |
| Five-layer stack | Start with BPMN + DMN, add Ontology + Event Sourcing later (open question) |

## What's Next

**Next session: Chat #2 — Knowledge Engine Deep Dive**
- Domain structure implementation detail
- Ingestion pipeline specifics (Swagger, OData, Playwright, Award rules)
- Retrieval tuning (existing RAG system evolution)
- Multi-domain operations
- Read: this handoff + `knowledge-engine/` vault folder + Doc 5 (Knowledge Engine Architecture)

## Open Questions Carried Forward

- How many BPMN processes does MVP actually need?
- Minimum viable enforcement for Monash POC specifically?
- Who maintains BPMN diagrams long-term?
- L0/L1/L2 hierarchy mapping to platform areas?
- BPMN + DMN first, or design all five layers from the start?

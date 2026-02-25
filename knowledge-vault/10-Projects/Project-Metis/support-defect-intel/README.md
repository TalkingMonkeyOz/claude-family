---
tags:
  - project/Project-Metis
  - area/support-defect-intel
  - scope/system
  - level/1
  - phase/3
projects:
  - Project-Metis
created: 2026-02-19
updated: 2026-02-24
synced: false
---

# Support & Defect Intelligence

> **Scope:** system (generic platform capability — triage rules, defect tracking, and resolution patterns configured per customer deployment)
>
> **Design Principles:**
> - The System is the primary defect management layer — syncs outward to customer defect trackers, not the other way around
> - Defect preparation acceleration is the core value — turning vague reports into structured, replicated, de-duplicated tickets fast
> - Every resolved ticket is a candidate for knowledge — but human decides what's worth keeping
> - Semantic matching for duplicates, not just keyword matching
> - Pattern detection surfaces systemic issues for human review — AI does not auto-escalate
> - Environment-aware: AI knows per-customer what environments exist and what access level it has

> AI triage, defect preparation, duplicate detection, pattern recognition, defect collation, knowledge promotion.

**Priority:** MEDIUM — Phase 3
**Parent:** [[Project-Metis/README|Level 0 Map]]
**Status:** ✓ FIRST PASS

## What This Area Covers

All defect/issue intelligence regardless of source — customer-reported support tickets AND internal defects from development/testing. Area 4 (Quality & Compliance) finds problems through testing and compliance checks. Area 5 manages them once found. Customer-reported issues skip Area 4 detection and land directly here.

## Decisions Made

1. **Scope:** Area 5 owns all defect/issue intelligence regardless of source. Area 4 detects, Area 5 manages. Customer reports skip detection, land directly in Area 5.
2. **Generic framing:** Customer's defect tracker (Jira, Azure DevOps, etc.) is a connector via Integration Hub, not hardcoded. The System is source of truth for defect intelligence.
3. **System as primary:** Defects captured in The System first → AI structures, checks duplicates, suggests severity → human reviews → System creates ticket in customer's tracker AND maintains its own linked record. Two-way sync after creation.
4. **Area 4/5 feedback loop:** Area 5 detects cross-ticket patterns → flags to human → human decides whether to escalate to Area 4 (add proactive quality check), request product fix, update documentation, or other action. AI surfaces, human decides.
5. **Knowledge promotion:** Human-driven, not automatic. End-of-day/sprint/engagement review process. AI summarises what was resolved, suggests candidates for KMS capture, pulls together context (tickets, code changes, config details), drafts KMS entry. Human approves/rejects/modifies. Approved items enter KMS at appropriate tier.
6. **Core value proposition:** Defect preparation acceleration. AI takes vague customer report, asks clarifying questions based on customer config, cross-references KMS for similar issues, helps set up replication scenario, auto-structures the ticket (steps to reproduce, expected vs actual, environment, severity, related tickets). Turns 30-60 min defect prep into 5 min review-and-submit.
7. **Environment awareness:** AI needs to know per-customer what environments exist (demo, separate instance, customer test system) and what access level it has to each. Stored in KMS Category D (Customer Context). Replication environment is variable, not fixed.

## Support Triage

### Current Pain Point
- Client reports a problem vaguely ("this filter doesn't work")
- Consultant has to figure out what they actually mean — which filter, which screen, what data, what they expected
- Replicate the issue in a test environment (could be demo, separate instance, or customer test system)
- Document properly — steps to reproduce, expected vs actual, environment, severity, screenshots
- Lodge the ticket
- Process takes 30-60 minutes per defect, repeated constantly

### AI-Assisted Flow
- Client describes issue in plain language (or via customer's defect tracker)
- AI asks clarifying questions based on what it knows about that customer's configuration
- AI cross-references against [[knowledge-engine/README|Knowledge Engine]]: has this been seen before? What was the fix?
- AI checks client's specific configuration — is this a known interaction?
- AI suggests or generates the replication scenario using known environment access
- AI pre-populates defect ticket: steps to reproduce, expected vs actual, environment details, severity suggestion, related tickets
- Suggested resolution provided before a human even opens the case
- Human reviews and approves — submit to both System and customer's tracker

### Pattern Detection
- AI identifies recurring issues across customers — not just same bug, but same configuration mistake
- Pattern detected → flagged to human for review (AI does NOT auto-escalate)
- Human decides: escalate to Area 4 (proactive quality check), request product fix, update documentation, training, etc.
- Cross-customer pattern analysis respects data isolation — patterns anonymised, specific customer data never crosses boundaries

## Defect Management

### Intelligent Defect Capture
- Consultant or tester describes defect in natural language
- AI structures it: steps to reproduce, expected vs actual, environment details, severity suggestion
- AI checks for duplicates — semantic match, not just keyword match
- AI attaches relevant context: customer configuration, affected module, related tickets
- The System creates and tracks the defect internally, syncs to customer's external tracker

### Defect Lifecycle
- The System monitors defect status across all tracked items (internal DB is source of truth)
- Automated periodic digest: defects needing attention, why, and suggested priority
- Cross-customer impact analysis: "This defect affects N other customers with similar configurations"
- Before project status update, AI scans all open defects and generates summary
- Two-way sync with customer's external defect tracker (status, comments, resolution)

### Knowledge Promotion (Learning Loop)
- End-of-day/sprint/engagement: AI summarises what was resolved
- AI suggests candidates that look like new knowledge (pattern matching against existing KMS)
- Human reviews suggestions: yes / no / modify
- For approved items: AI pulls together context (tickets, code changes, config details), drafts KMS entry
- Human reviews draft, approves → enters KMS as Category F (Operational), Tier 3 (experiential, confidence-flagged)
- De-duplication against existing knowledge before promotion

## Area 4/5 Relationship

```
Area 4 (Quality)              Area 5 (Support & Defect Intel)
─────────────────              ──────────────────────────────
DETECTS problems               MANAGES problems once found
- Testing                      - Customer reports (direct)
- Compliance checks            - Internal defects (from Area 4)
- Background analysis          - Triage & preparation
- Change-triggered             - Lifecycle tracking
  re-validation                - Pattern detection
                               - Knowledge promotion
        │                              │
        │  problems found              │  patterns detected
        └──────────► Area 5            └──────► Human review
                                                   │
                                          escalate to Area 4?
                                          product fix?
                                          documentation?
                                          training?
```

## Dependencies

- Requires [[knowledge-engine/README|Knowledge Engine]] — knowledge lookup for triage, KMS promotion target
- Requires [[integration-hub/README|Integration Hub]] — customer defect tracker connectors (Jira, Azure DevOps, etc.)
- Feeds [[project-governance/README|Project Governance]] — defect status feeds project health reporting
- Receives from [[quality-compliance/README|Quality & Compliance]] — defects found during testing/compliance land here
- Feeds back to [[quality-compliance/README|Quality & Compliance]] — detected patterns may trigger new proactive checks (via human review)
- KMS Category D (Customer Context) — environment access details per customer

## Open Questions

- [ ] How many support tickets per month currently? Volume matters for learning loop
- [ ] What's the current escalation rate? Baseline to measure against
- [ ] How are defects currently collated for project updates? (The 10+ hour/week pain point)
- [ ] Two-way sync design: conflict resolution when defect updated in both System and external tracker simultaneously
- [ ] Knowledge promotion criteria: what heuristics does AI use to suggest "this resolution is worth keeping"?

---
*Source: Doc 1 §5.3, §5.4 | Doc 4 §3.2 WS7 | Brainstorm session 2026-02-24 | Created: 2026-02-19*

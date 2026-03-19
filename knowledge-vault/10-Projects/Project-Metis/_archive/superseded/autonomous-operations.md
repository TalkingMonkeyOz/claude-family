---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - topic/autonomous-operations
  - level/2
projects:
  - Project-Metis
created: 2026-02-19
synced: false
---

# Autonomous Operations

> What runs without a human sitting there, and how.

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]

## The Gap

The brainstorm docs assume development-time agent work — John opens Claude Code, agents build things, session ends. But several platform capabilities need to run autonomously:

## What Needs to Run Autonomously

### Event-Driven (reacts to something happening)
- **Support triage** — Jira ticket created → AI picks it up, suggests resolution
- **Defect duplicate detection** — new defect logged → AI checks for semantic matches
- **Configuration change detection** — time2work config changes → flag and document

### Scheduled (runs on a timer)
- **Defect monitoring** — daily/weekly scan of Jira boards for stale tickets, blockers
- **Weekly digest generation** — "here are the 5 defects that need attention"
- **Documentation freshness** — check if configs changed but docs didn't
- **Pattern detection** — scan across clients for recurring issues
- **Health scoring** — pull from Salesforce/Jira/Confluence, update dashboards
- **Compliance monitoring** — ongoing Award rule change checking

### On-Demand but Unattended (human triggers, walks away)
- **Pay scenario batch runs** — kick off 100 test scenarios, come back to results
- **Knowledge ingestion** — ingest a large doc set, process overnight
- **Regression suite** — run full test suite after a time2work release

## Infrastructure Options

| Option | How It Works | Cost | Complexity |
|--------|-------------|------|-----------|
| Azure VM with cron/scheduler | Always-on VM runs Python/Node services on schedule | ~$30-60/month | Low-medium |
| Azure Functions (serverless) | Functions trigger on schedule or webhooks, pay per execution | Variable, potentially cheaper at low volume | Medium |
| n8n / Temporal (orchestrator) | Visual workflow tool, handles scheduling, retries, human-in-loop | n8n self-hosted ~free, Temporal more complex | Medium-high |
| Simple webhook listener | Express/Fastify server listens for Jira webhooks, triggers agents | Runs on existing VM | Low |

## Cost Implications

Autonomous agents consume API tokens without a human watching. Need:
- **Per-run cost caps** — each autonomous run has a token budget it cannot exceed
- **Daily/monthly cost caps** — hard ceiling on total autonomous spend
- **Alerting** — notify John if spend hits thresholds
- **Efficient model selection** — scheduled tasks use Haiku ($1/$5 per MTok) or Sonnet ($3/$15), never Opus unless justified
- **Prompt caching** — autonomous agents re-use the same system prompts, so caching gives 70-80% savings

## Guardrails for Autonomous Operation

1. **Read-only by default.** Autonomous agents can read from systems freely but need explicit permission config to write
2. **Cost caps per run.** Each scheduled/triggered task has a max token budget
3. **Human approval for write operations.** Queue write actions for human review unless explicitly whitelisted
4. **Kill switch.** Ability to stop all autonomous operations instantly
5. **Audit trail.** Every autonomous action logged — what ran, when, what it did, what it cost
6. **Escalation path.** If an autonomous agent hits uncertainty, it queues for human review rather than guessing
7. **Dead man's switch.** If the system hasn't checked in for X hours, alert John

## Open Decisions

- [ ] #decision What hosting model for autonomous operations? (VM + cron vs serverless vs orchestrator)
- [ ] #decision What's the autonomous agent monthly budget cap?
- [ ] #decision Which operations are safe for autonomous write access? (e.g. Jira comments yes, production deploys no)
- [ ] #decision Event-driven: Jira webhooks or polling?

## Phasing

This isn't Phase 0-1 work. The autonomous operations layer comes after we've proven the capabilities work interactively:

1. **Phase 1-2:** Everything runs on-demand (human triggers)
2. **Phase 2-3:** Add scheduled batch runs (regression testing, digests)
3. **Phase 3+:** Add event-driven triggers (Jira webhooks, config change detection)
4. **Phase 4+:** Full autonomous support triage and pattern detection

Build it manually first, automate it once you trust it.

---
*Source: Gap identified during decision review session 2026-02-19 | Created: 2026-02-19*

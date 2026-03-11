---
tags:
  - project/Project-Metis
  - scope/system
  - type/gate-zero
  - gate/zero
created: 2026-03-07
updated: 2026-03-07
status: validated
---

# Problem Statement

Gate Zero Document 1.

## What Is METIS?

METIS is an enterprise AI platform that learns what your organisation does — your domain, your processes, your history — and uses that knowledge to do the work, not just answer questions about it.

## The Problem

Every enterprise has deep domain knowledge — how their product works, how their processes run, what's gone wrong before, what their customers need. Right now that knowledge lives in people's heads, scattered documents, and disconnected systems. When people leave, the knowledge leaves with them. When new people start, they rebuild it from scratch.

Off-the-shelf AI tools don't solve this. They're generic — they don't know your product, your processes, your history. They can answer general questions but can't do your actual work because they don't understand your specific domain deeply enough to be trusted with it.

For AI to add significant enterprise value, it needs to understand what the enterprise does — deeply, specifically, and in a way that compounds over time. Not just answer questions about it, but actually do the work: analyse data, generate documentation, detect patterns, learn from outcomes.

This is true regardless of industry. A software development house needs the AI to understand its codebase, pipelines, and support tickets. A t-shirt company needs it to understand ordering patterns, delivery failures, and customer support. The domain content changes. The need doesn't.

## The Question METIS Answers

How do you give an enterprise an AI capability that truly understands its domain, learns from every engagement, and can do the work — not just talk about it?

## Scope

### In Scope

- A platform that ingests and learns an enterprise's domain knowledge — whatever that domain is
- AI that retrieves that knowledge in context and can do actual work with it (analysis, documentation, pattern detection, data work)
- Skills that shape the platform's behaviour for a specific enterprise type — a development house gets development-oriented skills, a solo contractor gets analysis and design skills, a logistics company gets operations skills
- Knowledge that compounds across engagements — what's learned on project A is available on project B
- nimbus as the first customer deployment (workforce management software — code, pipelines, support tickets)

### Not In Scope

- Building custom LLMs — METIS uses existing models (currently Claude, provider-agnostic by design)
- Replacing existing enterprise tools — METIS sits alongside existing systems, connecting to them rather than replacing them
- General-purpose chatbot or consumer AI — METIS is enterprise-grade, domain-specific, structured

---

*Gate Zero Doc 1 | Validated: 2026-03-07 | Author: John de Vere + Claude Desktop*

---
**Version**: 1.0
**Created**: 2026-03-07
**Updated**: 2026-03-07
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-zero/problem-statement.md

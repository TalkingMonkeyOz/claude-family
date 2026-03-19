---
projects:
- claude-family
tags:
- vision
- architecture
---

# Claude Family — Vision Document

**A coordinated team of AI instances that learn, remember, and deliver together.**

---

## 1. The Problem

Building software with AI coding assistants is powerful — until you try to do it seriously. Anyone who has used an AI assistant across multiple projects and sessions will recognise these problems:

### Knowledge Evaporates

Every session starts from zero. The decisions you made yesterday, the architecture you agreed on last week, the gotcha that cost you two hours — all gone. You re-explain context, re-state preferences, and re-discover problems that were already solved. The AI has no memory. Your most valuable asset — accumulated project knowledge — is invisible to the tool that needs it most.

### Quality Is Inconsistent

Without enforcement, AI assistants cut corners. They skip tests, use inconsistent naming, write to the wrong database tables, and produce work that varies wildly in quality between sessions. There is no governance layer. The AI does whatever seems reasonable in the moment, with no awareness of your standards, your processes, or what happened in the last session.

### Every Instance Is an Island

If you run multiple AI assistants — across different projects, different tasks, or different team members — they cannot coordinate. They cannot share knowledge, delegate work, or build on each other's findings. Each instance operates in complete isolation, duplicating effort and missing opportunities.

### Projects Lack Structure

Documentation is scattered or missing. File organisation varies by project. There are no standard operating procedures. When an AI assistant starts work on a project, it has no consistent foundation to build on. Every project is a blank slate, every time.

### Data Degrades Silently

Work tracking tables fill with inconsistent values. Test data mixes with real data. Status fields contain values that no one defined. Without validation at the database level, data quality erodes until the tracking systems become unreliable — and then unused.

---

## 2. The Solution

Claude Family is a coordinated team of Claude instances with shared memory, enforced procedures, and persistent knowledge. It transforms AI-assisted development from ad-hoc prompting into a governed, learning system.

### Shared Memory That Persists

Every Claude instance writes to and reads from a shared knowledge base. Decisions, patterns, gotchas, and lessons learned survive across sessions and across projects. A discovery made by one instance is available to all. Knowledge compounds over time instead of evaporating.

### Enforced Procedures

Hook scripts intercept Claude's actions at key points — before writing files, before committing code, before updating data. They enforce coding standards, validate data against a registry of allowed values, block invalid state transitions, and ensure documentation stays current. This is not advisory. Invalid actions are blocked.

### Coordinated Work

Claude instances can send messages, delegate tasks, and hand off work to each other. A planning instance can break a feature into tasks and assign them to specialist instances. A review instance can check work before it ships. The system coordinates through a message bus backed by the shared database.

### Consistent Structure

Every project starts from a template: standard folder structure, required documents (CLAUDE.md, PROBLEM_STATEMENT.md, ARCHITECTURE.md), pre-configured hooks and rules. A `/project-init` command scaffolds everything in minutes. Every Claude instance knows where to find what it needs.

### Quality Data by Default

A column registry defines valid values for every constrained field. Database constraints reject invalid writes. Workflow state machines enforce valid status transitions (you cannot mark a task "completed" without first moving it through "in_progress"). The data stays clean because the system will not accept dirty data.

---

## 3. How It Works

The system is built on four pillars: a database-driven configuration layer, a hook-based enforcement system, MCP tool servers, and a tiered knowledge architecture.

### Database-Driven Configuration (Self-Healing)

The PostgreSQL database (`ai_company_foundation`, schema `claude`, 58+ tables) is the single source of truth for all configuration. Project settings, hook configurations, skills, rules, and coding standards are stored in the database and deployed to the filesystem on every session start.

This makes the system self-healing. If a config file is corrupted, deleted, or manually edited — it regenerates from the database automatically. There is no configuration drift. The database always wins.

Key tables: `workspaces` (project registry), `config_templates` (shared settings), `skills` (32 reusable skill definitions), `rules` (enforcement rules), `instructions` (coding standards), `profiles` (CLAUDE.md content).

### Hook-Based Enforcement

Eleven hook scripts intercept Claude's actions at defined points in the session lifecycle:

| Phase | What Happens |
|-------|-------------|
| **Session Start** | Log session, load state, check messages, regenerate config |
| **Every Prompt** | RAG search for relevant knowledge, inject core protocol |
| **Before Writing** | Validate content against standards, inject coding instructions |
| **After Tool Use** | Sync todos to DB, log MCP usage, track tasks |
| **Before Compaction** | Preserve active work items in compressed context |
| **Session End** | Auto-close session, save state |

Hooks operate on a fail-open principle — if a hook crashes, it logs the failure and lets Claude continue. Failures are automatically filed as feedback items for self-repair.

### MCP Tool Servers

Five MCP (Model Context Protocol) servers provide Claude with structured tools:

| Server | Purpose |
|--------|---------|
| **project-tools** | 60+ tools for work tracking, memory, messaging, config |
| **postgres** | Direct SQL access with query analysis |
| **bpmn-engine** | Process model navigation and validation |
| **sequential-thinking** | Multi-step reasoning for complex problems |
| **playwright** | Browser automation for testing |

The project-tools server is the primary interface. It provides workflow-aware tools (`start_work`, `complete_work`, `advance_status`) that enforce state machines, check dependencies, and log audit trails. Raw SQL is available but discouraged for writes — the tools handle validation.

### Three-Tier Memory

Knowledge is stored in three tiers, each serving a different purpose:

| Tier | Scope | Examples | Lifecycle |
|------|-------|----------|-----------|
| **SHORT** | Current session | Credentials, endpoints, decisions | Expires with session |
| **MID** | Cross-session | Learned facts, decisions, findings | Promoted from SHORT if reused |
| **LONG** | Permanent | Patterns, procedures, gotchas | Promoted from MID after 5+ accesses |

The `remember()` tool auto-routes content to the correct tier. A quality gate rejects entries under 80 characters or junk patterns (task acknowledgements, progress notes). Deduplication merges entries above 75% similarity. Every 24 hours, a consolidation job promotes, decays, and archives entries based on access patterns.

Above the tiers sits the **Knowledge Vault** — an Obsidian-based collection of long-form documents (procedures, domain knowledge, patterns, research) indexed with semantic embeddings for RAG retrieval. When Claude receives a prompt, the RAG hook searches the vault and silently injects relevant documents into context.

---

## 4. The Desktop App — Claude Manager

Claude Manager is the control plane — a desktop application built with MUI that provides visibility and management over all Claude instances and their work.

### What It Shows

- **Build Board** — streams, features, and tasks across all projects with dependency tracking and status
- **Session Monitor** — active Claude instances, what they are working on, and their message traffic
- **Knowledge Explorer** — browse, search, and manage the three-tier memory and vault documents
- **Config Manager** — edit project settings, skills, rules, and instructions with live deployment
- **Health Dashboard** — database health, hook success rates, embedding coverage, and system alerts

### Why a Desktop App

Claude Code runs in the terminal. It has no UI for oversight. Without a visual control plane, the operator (John) has no way to see what multiple Claude instances are doing, whether work is on track, or where problems are emerging. Claude Manager fills that gap — it reads from the same database that powers the Claude instances, providing a real-time view of the entire system.

---

## 5. Where We're Going — Project METIS

Claude Family started as internal tooling — infrastructure to make one person's AI-assisted development more effective. But the problems it solves are not unique.

Every professional services firm runs on knowledge. Every engagement generates insights — what worked, what didn't, which configurations solve which problems. But that knowledge lives in people's heads, scattered documents, and disconnected tools. When a senior consultant leaves, their knowledge walks out the door. When a new engagement starts, the team rebuilds understanding from scratch.

**METIS** is the product evolution of Claude Family: an AI-powered delivery platform for professional services firms.

### From Internal Tooling to Product

| Claude Family (Internal) | METIS (Product) |
|--------------------------|-----------------|
| Single user (John) | Multi-tenant, multi-user |
| Local development | Cloud-hosted (Azure) |
| CLI-only interaction | Web application + API |
| Ad-hoc project structure | Governed delivery workflows |
| General-purpose knowledge | Domain-specific knowledge bases |

### What METIS Adds

- **Domain Learning** — ingest product documentation, process guides, and engagement history to build a domain-specific knowledge base that compounds in value over time
- **Governed Delivery Workflows** — AI agents follow defined delivery stages with human checkpoints and quality gates. The AI cannot skip steps or bypass reviews
- **Knowledge Isolation** — each customer's data is fully isolated. Product-level knowledge (shared) separates cleanly from client-level knowledge (private)
- **Continuous Improvement** — each engagement teaches the system. Patterns that work for one client can be promoted to benefit all future engagements

### The Trajectory

1. **Now** — Claude Family proves the model internally. Coordinated AI instances, persistent knowledge, enforced quality
2. **Next** — Claude Manager provides the visual control plane. Work tracking, config management, and monitoring through a desktop UI
3. **Then** — METIS takes the proven patterns and rebuilds them as a multi-tenant, cloud-hosted platform for professional services delivery

The core insight remains the same at every stage: **AI that knows your domain, follows your processes, and gets smarter over time is fundamentally more valuable than AI that starts from zero every session.**

---

## Summary

Claude Family exists because AI-assisted development should be more than isolated conversations with a stateless model. It should be a system — one that remembers, coordinates, enforces quality, and learns. That system is what we have built, what we are refining, and what METIS will bring to market.

The technology works. The architecture is proven across 58+ database tables, 60+ MCP tools, 11 hook scripts, 32 skills, and months of daily use. The question is no longer whether coordinated AI instances can deliver governed, knowledge-aware work. The question is how far this model can scale.

---

**Version**: 1.0
**Created**: 2026-03-19
**Updated**: 2026-03-19
**Location**: knowledge-vault/10-Projects/claude-family/vision.md

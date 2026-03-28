---
projects:
- claude-family
- project-metis
tags:
- research
- architecture
- coding-intelligence
- projectional-editing
- CKG
- patterns
---

# Semantic Code Engine — Research Document

## Problem Statement

AI coding agents (Claude) experience 7 failure modes that cause multi-day iteration sessions:

| Failure Mode | Pain Weight | Description |
|---|---|---|
| Pattern Inconsistency | ×3 | Two ways to do same thing, AI picks wrong one |
| Error Cascade | ×3 | One wrong assumption snowballs into days of fixing |
| Context Loss | ×2 | Can't hold full codebase picture |
| Accumulated Drift | ×2 | Each session adds slightly inconsistent code |
| Missing Constraints | ×2 | Valid code that uses wrong approach |
| Discovery Overhead | ×1.5 | 60% time reading, 40% writing |
| Cross-File Coordination | ×1.5 | Sequential changes invalidate each other |

**Root cause**: Source code is designed for humans. AI is forced to work with human-centric text files, reconstructing understanding from scratch every session.

## Core Insight

**AI-only development removes the #1 barrier** that killed every prior projectional editing system. Human programmers hate editing ASTs. But when the developer IS an AI, the UX barrier is irrelevant.

Source code should be an OUTPUT FORMAT for AI — like machine code is for compilers.

## Prior Art

| System | Year | Approach | Why It Failed |
|---|---|---|---|
| Smalltalk | 1970s | Image-based (no files) | Binary images opaque to external tools |
| Intentional Programming | 1995 | Semantic tree + projections | Shelved for C#, human UX barrier |
| JetBrains MPS | 2003+ | AST editing, no parser | Small community, tooling lock-in |
| Unison | 2019+ | Content-addressed code | Niche language, adoption |
| Darklang | 2019+ | AST in browser, deployless | Being rewritten, limited scope |
| Moderne/OpenRewrite | 2024+ | Lossless Semantic Tree + AI | Commercially successful (refactoring focus) |

**All failed because humans didn't want to change.** In AI-only development, this objection doesn't exist.

## 6 Implementation Approaches

See [[SCE Approaches Detail]] for full specifications.

### Comparison Table (Weighted by Pain)

| Approach | Score /46.5 | Sessions | Value/Session | Category |
|---|---|---|---|---|
| 1. Enhanced CKG | 21 | 2.5 | 8.4 | Engineering |
| 2. Semantic Layer | 35 | 6.5 | 5.4 | Engineering |
| 3. Intent-Based | 45 | 40+ | 1.1 | Research |
| 4. Components | 34.5 | 5 | 6.9 | Engineering |
| 5. AIR | 45 | 40+ | 1.1 | Research |
| 6. Patterns | 35 | 3.5 | 10.0 | Engineering |

### Recommended Build Path

**Phase A** (engineering, 5-6 sessions): Approaches 1 + 6
**Phase B** (engineering, 5-8 sessions): Approaches 2 + 4
**Phase C** (research, open-ended): Approaches 3 + 5

## Pattern System Design

### Lifecycle (BPMN-worthy)

1. **Discovery** — AI detects from CKG analysis + manual definition
2. **Registration** — Template + constraints + anti-patterns + examples
3. **Application** — Intent matching → template instantiation → validation
4. **Update** — Change template once → regenerate ALL instances
5. **Retirement** — Deprecate → migration path → gradual replacement

### Per-Project Libraries

| Project | Patterns | Coverage |
|---|---|---|
| nimbus-mui | 6-8 (OData, components, Tauri wrappers) | ~60-70% |
| claude-family | 4-5 (MCP tools, hooks, migrations) | ~50% |
| trading-intelligence | 3-4 (API endpoints, services, jobs) | ~40% |

## Infrastructure Requirements

No GPU required. All operations use existing infrastructure:
- Tree-sitter (parsing, CPU only)
- PostgreSQL (storage/queries, already running)
- Template engine (generation, CPU only)
- Voyage AI embeddings (semantic matching, API)

## Metis Integration Potential

The SCE is a core differentiator for Project Metis. No existing AI coding tool provides structured code representations optimized for AI agents. If demonstrated to improve code quality and reduce iteration time, this is both a technical contribution and a commercial advantage.

## References

- Unison: unison-lang.org/docs/the-big-idea/
- JetBrains MPS: jetbrains.com/mps/
- Moderne LST: moderne.ai/technology
- Codified Context: arXiv:2602.20478 (Feb 2025)
- Tratt: tratt.net/laurie/blog/2024/structured_editing_and_incremental_parsing.html
- Awesome Structure Editors: github.com/yairchu/awesome-structure-editors

---
**Version**: 1.0
**Created**: 2026-03-25
**Updated**: 2026-03-25
**Location**: knowledge-vault/20-Domains/coding-intelligence/semantic-code-engine-research.md

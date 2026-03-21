---
projects:
  - Project-Metis
tags:
  - project/metis
  - area/knowledge-engine
  - scope/system
  - type/design
  - phase/1
created: 2026-03-22
updated: 2026-03-22
status: validated
---

# Coding Intelligence — METIS Design

> **Scope:** Platform capability within the Knowledge Engine (F119)
> **Prototype:** Claude Family CKG (F156, completed 2026-03-21)
> **Status:** All 5 design decisions validated (2026-03-22)

---

## 1. The Problem

AI-assisted coding has measurable, compounding quality issues:

| Metric | Source | Finding |
|--------|--------|---------|
| Code duplication | GitClear (211M lines, 2020-2024) | Copy/paste up 48% (8.3%→12.3%), refactoring collapsed 25%→<10% |
| Issue density | CodeRabbit (470 PRs) | AI code has 1.7x more issues, +75% logic bugs, +3x readability problems |
| Developer speed | METR (16 devs, 246 tasks) | Experienced devs 19% SLOWER with AI (but perceive 20% faster) |
| Security | Apiiro (Fortune 50) | 10x spike in security findings per month |
| Trust | Industry survey 2025 | Developer trust dropped 43%→29% despite 84% adoption |

**Root cause:** Every AI session starts from scratch. No persistent code memory, no semantic search, no enforced standards. Same problem solved 3 different ways across sessions.

**The fix:** Context engineering. Anthropic's 2026 report: context-aware projects see **40% fewer errors, 55% faster completion**.

## 2. The Key Insight: Document→Code Parallel

METIS already has a proven pattern for making information searchable:

```
Documents: raw docs → chunk (sentences) → embed (Voyage AI) → store → search → rank → assemble
Code:      source files → parse (tree-sitter) → embed (Voyage AI) → store → search → rank → assemble
```

Same pattern, different parser. The design-coherence skill (cross-reference large document sets, detect contradictions) is conceptually identical to CKG collision detection (cross-reference code symbols, detect duplication).

**This makes METIS a platform with pluggable content types, not a single-purpose tool.** Decision #8 (content-aware chunking per content type) taken to its logical conclusion.

## 3. Architecture: Option C (Hybrid)

Knowledge Engine (F119) owns the backbone pipeline. Code intelligence adds specialized ingestion + storage + retrieval.

| Layer | Documents | Code |
|-------|-----------|------|
| **Parser** | Sentence-boundary chunker | Tree-sitter AST (Python, TS, JS, C#, Rust) |
| **Storage** | `knowledge_items` + `knowledge_chunks` | `code_symbols` + `code_references` (dedicated) |
| **Embeddings** | Voyage AI, shared vector space | Voyage AI, same vector space |
| **Retrieval** | Semantic search, RAG | find_symbol, check_collision, find_similar |
| **Ranking** | Single ranking pipeline (D10) | Same pipeline, code signals added |
| **Context assembly** | Knowledge context | Dossier (aggregates CKG + standards + memory) |

**Why dedicated tables for code:** Code has structural relationships (calls, imports, extends, parent symbols) that `knowledge_items` doesn't model. Claude Family proved this with `claude.code_symbols` (17 cols) + `claude.code_references` (6 cols).

## 4. Schema: Flat Tables + Recursive CTEs

**Apache AGE rejected.** Research findings (2026-03-22):

| Concern | AGE | Flat Tables + CTEs |
|---------|-----|-------------------|
| Backup/restore | Breaks on pg_dump (OID-encoded graphids) | Standard pg_dump works |
| Performance | 1.5-3.7ms, sometimes 40x slower | 0.8ms with BTREE indexes |
| Maintenance | Core dev team dismissed Oct 2024 | Pure PostgreSQL |
| Cloud support | No AWS RDS | Works everywhere (D6) |

**Schema additions** (to deliverable-05b):

`code_symbols`: symbol_id, org_id, product_id, client_id, engagement_id (scope chain), project_name, name, kind, file_path, line_number, end_line, scope, visibility, signature, parent_symbol_id, language, file_hash, embedding, last_indexed_at, created_at, updated_at.

`code_references`: ref_id, from_symbol_id, to_symbol_id, to_symbol_name, ref_type, created_at.

Indexes: BTREE on (project_name, name), (file_path), (parent_symbol_id); HNSW on embedding; BTREE on code_references (from_symbol_id), (to_symbol_id).

## 5. Validated Decisions (2026-03-22)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Architecture | Option C: Hybrid | Knowledge Engine backbone + dedicated code tables. Single ranking pipeline shared |
| 2 | Storage | Flat tables + recursive CTEs | AGE has backup issues, worse performance, uncertain maintenance |
| 3 | Indexing | Auto-index on project onboard | Opt-in = forgotten. Augment/Copilot auto-index. Separate DB = no cross-tenant risk |
| 4 | Content types | Extensible parser pipeline | Pluggable parsers (docs, code now; transcripts, Jira, Confluence later) |
| 5 | Dog-fooding | Index METIS's own code from day one | Validates pipeline, catches our drift, proves system before selling (D3) |

## 6. Phasing

**Phase 1 (Core):**
- code_symbols + code_references tables in schema
- Tree-sitter ingestion pipeline (multi-tenant, multi-language)
- Basic retrieval tools: find_symbol, check_collision, find_similar
- Dog-food: index METIS codebase as first project

**Phase 2 (Advanced):**
- Deep dependency graph traversal (recursive CTEs at depth 5+)
- CI/CD auto-reindex on commit
- Dossier auto-population (aggregated component context)
- Cross-project symbol search
- Coding standards enforcement hooks

## 7. Competitive Positioning

| Tool | Code Context | Domain Knowledge | Process Enforcement |
|------|:-----------:|:----------------:|:-------------------:|
| Augment Code | Yes | No | No |
| GitHub Copilot | Yes | No | No |
| Sourcegraph Cody | Yes | No | No |
| **METIS** | **Yes** | **Yes** | **Yes** |

No competitor combines code + domain + process. For a development house like Nimbus, METIS knows the code AND the business rules AND enforces quality gates. That's the moat.

## 8. Related Work

- **Prototype:** Claude Family CKG (F156) — [[coding-intelligence-research|Research]] / [[coding-intelligence-why|Why]]
- **Feature:** F119 (Area 1: Knowledge Engine)
- **Data model:** [[deliverable-05b-data-model-platform|Deliverable 05b]] (2 tables to add)
- **Competitive research:** [[coding-intelligence-competitive-analysis|Competitive Analysis]]
- **Build tasks:** BT446-BT448 (under F119)

---
**Version**: 1.0
**Created**: 2026-03-22
**Updated**: 2026-03-22
**Location**: knowledge-vault/10-Projects/Project-Metis/coding-intelligence-design.md

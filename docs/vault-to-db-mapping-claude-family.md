# Vault-to-DB Mapping: claude-family

Parent: [vault-to-db-mapping.md](vault-to-db-mapping.md)

## DB Knowledge (15 entries, all confidence=100)

| Title | Type |
|-------|------|
| Document-Project Junction Table Pattern | fact |
| Core Documents Pattern | fact |
| CLAUDE.md stored in profiles.config->behavior, not filesystem | gotcha |
| Agent Health Check redesign decision | pattern |
| Bulk Document Classification via SQL | pattern |
| Project Scaffolding Script | pattern |
| PostgreSQL audit_log schema - correct columns for INSERT | fact |
| generate_project_settings.py preserves existing permissions | gotcha |
| Review Local LLM Usage job audit decision | learned |
| Document Scanner job audit decision | learned |
| Orchestrator agent MCP tool permissions - dual permission system | pattern |
| Dynamic Identity Lookup by Platform Instead of Hard-Coding | pattern |
| Identity: Project-Aware Not Platform-Based | fact |
| Isolated agents cannot use permission_mode "default" | gotcha |
| Windows PowerShell UTF-8 Encoding Fix | pattern |

## Domain Concepts (1 entity)

- Claude Family Memory System

## Workfiles (10 active)

| Component | Title |
|-----------|-------|
| system-audit | critical handoff 2026-04-11 post-fix |
| system-audit | fix progress and remaining work |
| system-audit | full system audit 2026-04-10 |
| knowledge-pipeline | critical handoff 2026-04-10 late |
| knowledge-pipeline | regression investigation 2026-04-10 |
| connected-knowledge-architecture | design decisions |
| knowledge-architecture | F190 session progress 2026-04-10 |
| knowledge-architecture | F189 session wrap-up 2026-04-10 |

## Vault Topics with NO DB Equivalent

- Application Layer v2/v3 -- app layer design
- architecture-details-part1/part2 -- architecture internals
- cognitive-memory-processes -- cognitive memory design
- database-schema/ (4 files) -- schema documentation
- hook-system-requirements -- hook system design
- Identity System (2 files) -- identity docs (only a gotcha in DB)
- messaging-system-requirements -- messaging design
- session-user-stories/ (6 files) -- user stories
- unified-storage/ (18+ files) -- storage design docs
- vision.md -- project vision

## Vault Topics WITH DB Equivalents

- knowledge-pipeline-*.md -- covered by workfiles (knowledge-pipeline component)
- info-architecture-audit -- partially covered by system-audit workfiles

---

**Version**: 1.0
**Created**: 2026-04-11
**Updated**: 2026-04-11
**Location**: docs/vault-to-db-mapping-claude-family.md

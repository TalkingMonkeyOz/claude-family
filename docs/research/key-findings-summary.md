---
projects:
- claude-family
- project-metis
tags:
- research
- findings
- summary
synced: false
---

# Key Findings: External Memory Systems Research

Complete findings from [[research-external-memory-systems]].

## The 12 Key Insights

1. **Mem0 is the market leader** (48.9k stars, v1.0.5, Apache-2.0) with native pgvector support and MCP integration for Claude Code.

2. **SimpleMem's semantic lossless compression** (Jan 2026 research) achieves 26.4% F1 improvement over Mem0 with 30x fewer tokens. This algorithmic approach is the highest-value improvement.

3. **The tiered memory pattern is academically validated** by Tsinghua survey (Dec 2025). Our short/mid/long tiers map to working/episodic/semantic.

4. **Zep/Graphiti's bi-temporal model** (valid_from/valid_to on edges) is architecturally superior for evolving facts but requires Neo4j. Temporal validity concept is worth implementing in PostgreSQL.

5. **Hybrid search (BM25 + vector + RRF fusion) is solved** in PostgreSQL. This is the single highest-impact retrieval improvement with zero external dependencies.

6. **pgvector 0.8's iterative index scans** solve filtered HNSW query reliability. Previously returned fewer results than requested.

7. **Dossier/workfile pattern maps to Zettelkasten's index note concept**. Our `project_workfiles` table was designed for this but adoption is near-zero. Solution: simplify to single `dossier()` tool.

8. **CrewAI memory is local-only** (wiped on redeployment). **Motorhead is abandoned** (2023). Neither viable.

9. **Claude Code's MEMORY.md is fundamentally limited** — flat file, no search, linear token consumption. Our hook-based system is more capable; problem is complexity (15+ mechanisms), not capability.

10. **Winning formula for 2026**: Extract automatically (Mem0 pattern), store in PostgreSQL with hybrid indexes, retrieve with RRF fusion, consolidate with LLM-assisted compression (SimpleMem pattern), expose through 3-5 simple tools.

11. **Semantic deduplication at scale requires clustering** before pairwise comparison. Current approach (check all memories) won't scale. Partition by component/topic first.

12. **pg_cron for autonomous maintenance** removes dependency on Claude sessions for consolidation, decay, cleanup. Makes system self-maintaining.

## Immediate Actions (2-4 weeks)

- [ ] Implement automatic fact extraction on session end
- [ ] Upgrade pgvector to 0.8+ with iterative scans
- [ ] Add tsvector + RRF fusion for hybrid search
- [ ] Estimate adoption: High impact, moderate effort

## Medium-term Actions (1-2 months)

- [ ] Implement SimpleMem's semantic lossless compression
- [ ] Simplify to 3-5 tools (from 15+)
- [ ] Estimated adoption: High impact, significant effort

## Long-term Actions (2-3 months)

- [ ] Add pg_cron for autonomous maintenance
- [ ] Evaluate ParadeDB pg_search (if needed)

## What NOT to Do

Do not adopt Neo4j, Redis, external vector stores, or separate search engines. PostgreSQL + pgvector + Voyage AI is sufficient.

---

**Sources**:
- Mem0: https://github.com/mem0ai/mem0
- SimpleMem: https://arxiv.org/abs/2601.02553
- pgvector: https://github.com/pgvector/pgvector
- ParadeDB: https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\research\key-findings-summary.md

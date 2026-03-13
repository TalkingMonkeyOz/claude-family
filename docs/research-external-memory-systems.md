---
projects:
- claude-family
- project-metis
tags:
- research
- memory-systems
- external-frameworks
synced: false
---

# Research: External Memory Systems for AI Agents

## Executive Summary

The AI agent memory landscape in 2025-2026 has matured significantly. Several production-ready frameworks now exist, most converging on similar patterns: extract facts from conversations, embed them, store in vector databases, retrieve via semantic search, and optionally layer a knowledge graph on top.

**Key finding**: Our existing PostgreSQL + pgvector + Voyage AI stack is more capable than we are using it. The gap is not in storage infrastructure but in the **extraction, consolidation, and retrieval pipeline**. The most impactful improvements come from adopting proven patterns (semantic lossless compression, hybrid BM25+vector search, confidence-weighted decay) rather than adding new external dependencies.

**What fits our stack directly**:
- **Mem0** (v1.0.5, 48.9k stars) — best-in-class agent memory with native pgvector support, MCP integration for Claude Code, and graph memory. The closest match to what we need.
- **SimpleMem** (research, Jan 2026) — semantic lossless compression achieves 26.4% F1 improvement over Mem0 with 30x fewer tokens. The algorithmic approach is what we should adopt.
- **ParadeDB pg_search** — BM25 hybrid search inside PostgreSQL, no external dependencies. Direct upgrade path for our retrieval.
- **pgvector 0.8** — iterative index scans solve our filtered search problems.

**What requires external infrastructure** (probably not worth it for us):
- **Zep/Graphiti** — excellent temporal knowledge graphs but requires Neo4j/FalkorDB (not PostgreSQL)
- **Cognee** — knowledge graph engine, uses LanceDB/Kuzu internally, PostgreSQL only for metadata
- **Microsoft GraphRAG** — powerful but heavy; requires significant LLM compute for indexing

**Recommended direction**: Simplify to 3 tools (`remember`, `recall`, `dossier`) backed by PostgreSQL-native hybrid search (pgvector + BM25), adopting Mem0's extraction patterns and SimpleMem's compression approach without adding external dependencies.

---

## 1. Framework Comparison Table

| Framework | Approach | Storage Backend | pgvector Support | GitHub Stars | Version | License | Maturity | Fit (1-5) |
|-----------|----------|-----------------|------------------|-------------|---------|---------|----------|----------:|
| **Mem0** | Extract-embed-store memory layer | pgvector, Qdrant, Chroma, Pinecone, + graph (Neo4j/FalkorDB) | **Native** | 48.9k | v1.0.5 (Mar 2026) | Apache-2.0 | Production | **5** |
| **Zep/Graphiti** | Temporal knowledge graph | Neo4j 5.26+, FalkorDB, Kuzu | No (graph-first) | 23.5k | v0.28.1 | Apache-2.0 | Production | 2 |
| **SimpleMem** | Semantic lossless compression | SQLite (reference impl) | Not yet (portable) | ~200 | Research (Jan 2026) | Apache-2.0 | Research | **4** |
| **LangGraph** | State machine + checkpoints | PostgresSaver, SQLite, MongoDB | Via PostgresSaver | N/A | v1.0 (2025) | MIT | Production | 3 |
| **LlamaIndex** | Index + retrieval framework | pgvector, 40+ vector stores | **Native** | 40k+ | v0.12+ | MIT | Production | 3 |
| **Microsoft GraphRAG** | LLM-extracted graph communities | Multiple (Cosmos DB, PG) | Via accelerator | 25k+ | v2.x (2026) | MIT | Production | 2 |
| **CrewAI** | Short/Long/Entity/Contextual | ChromaDB (short), SQLite (long) | No | 27k+ | v0.100+ | MIT | Production | 1 |
| **mcp-memory-service** | MCP server + sqlite-vec | SQLite + sqlite-vec | No | ~2k | Active (Mar 2026) | MIT | Community | 2 |
| **OpenMemory (Mem0)** | MCP memory for Claude/Cursor | Mem0 backend (local or cloud) | Via Mem0 | Part of Mem0 | Active (2026) | Apache-2.0 | Production | **4** |
| **Motorhead** | Redis-based chat memory | Redis | No | ~500 | Stale (2023) | Apache-2.0 | Abandoned | 0 |

**Key insight**: Mem0 is the clear leader (48.9k stars, v1.0 stable, native pgvector, production-deployed). The only framework that directly supports our PostgreSQL stack without modifications. SimpleMem offers superior algorithmic approach (26.4% F1 improvement over Mem0, 30x token reduction).

---

## 2. PostgreSQL-Native Improvements (Immediate Actions)

### pgvector 0.8 — Iterative Index Scans
Solves "overfiltering" problem where filtered HNSW queries return fewer results than requested.

```sql
SET hnsw.iterative_scan = relaxed_order;
SELECT content FROM claude.knowledge
WHERE tier = 'long' AND project_id = $1
ORDER BY embedding <=> query_vec LIMIT 10;
```

**Action**: Upgrade to pgvector 0.8 if not already there.

### Hybrid Search — BM25 + Vector with RRF Fusion
Two approaches, both PostgreSQL-native. Option A (tsvector + pgvector) requires no extensions. Option B (ParadeDB pg_search) requires extension but better ranking.

**Expected improvement**: 15-30% better retrieval accuracy for keyword-specific queries.

## Detailed Analysis

See these linked documents for deep dives:
- [[research/external-memory-systems-overview]] — Executive summary and framework comparison
- [[research/memory-patterns-tiering-dedup]] — Tiered memory, deduplication, cross-session continuity
- [[research/dossier-topic-pattern]] — The "open topic, jot, file, find later" pattern
- [[research/implementation-roadmap]] — Implementation actions and timeline

---

## Document Navigation

This is the main research document. For organized access to all sections, see:
- [[research/README]] — Complete index
- [[research/key-findings-summary]] — 12 key insights + actions
- [[research/external-memory-systems-overview]] — Executive summary

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\research-external-memory-systems.md
**Related**: research/ subdirectory for detailed topics

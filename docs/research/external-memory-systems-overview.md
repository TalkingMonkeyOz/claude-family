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

# Research: External Memory Systems for AI Agents - Overview

## Executive Summary

The AI agent memory landscape in 2025-2026 has matured significantly. **Mem0** (v1.0.5, 48.9k GitHub stars) is the market leader. **SimpleMem** (Jan 2026 research) offers the best algorithmic approach: semantic lossless compression achieving 26.4% F1 improvement over Mem0 with 30x fewer tokens.

**Key finding**: Our PostgreSQL + pgvector + Voyage AI stack is more capable than we're using it. The gap is not infrastructure but the extraction/consolidation/retrieval pipeline.

**Our path forward**: No external dependencies needed. Adopt:
1. Mem0's automatic fact extraction pattern
2. SimpleMem's semantic lossless compression algorithm
3. pgvector 0.8's iterative index scans + hybrid BM25+vector search
4. Simplify to 3-5 tools (from 15+ overlapping mechanisms)

## Framework Comparison

| Framework | Approach | pgvector Support | GitHub Stars | Version | License | Fit (1-5) |
|-----------|----------|-----------------|-------------|---------|---------|----------:|
| **Mem0** | Extract-embed-store memory layer | **Native** | 48.9k | v1.0.5 (Mar 2026) | Apache-2.0 | **5** |
| **SimpleMem** | Semantic lossless compression | Not yet (portable) | ~200 | Research (Jan 2026) | Apache-2.0 | **4** |
| **Zep/Graphiti** | Temporal knowledge graph | No (Neo4j-only) | 23.5k | v0.28.1 | Apache-2.0 | 2 |
| **LangGraph** | State machine checkpoints | Via PostgresSaver | N/A | v1.0 (2025) | MIT | 3 |
| **CrewAI** | Short/Long/Entity memory | No | 27k+ | v0.100+ | MIT | 1 |
| **Motorhead** | Redis-based chat memory | No | ~500 | Stale (2023) | Apache-2.0 | 0 |

**Key insights**:
- Motorhead is dead (2023), CrewAI memory is local-only (wiped on redeployment)
- Zep/Graphiti architecturally superior but requires Neo4j (incompatible with PostgreSQL commitment)
- Mem0 is production-ready with everything we need
- SimpleMem's algorithm is the pattern to study

See [[research-memory-patterns]], [[research-dossier-pattern]], [[research-recommendations]] for details.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\research\external-memory-systems-overview.md

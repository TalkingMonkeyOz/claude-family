---
projects:
- claude-family
- project-metis
tags:
- research
- index
synced: false
---

# External Memory Systems Research — Complete Index

Complete research on production-ready agent memory frameworks and recommendations for Claude Family.

## Quick Start

1. **Start here**: [[key-findings-summary]] (12 key insights + immediate actions)
2. **High-level overview**: [[external-memory-systems-overview]] (executive summary + framework comparison)
3. **Main document**: [[../research-external-memory-systems]] (framework details and pgvector options)

## Detailed Topics

### Pattern Analysis
- [[memory-patterns-tiering-dedup]] — How tiered memory works, deduplication at scale, cross-session continuity
- [[dossier-topic-pattern]] — The "open topic, jot, file, find" pattern (Zettelkasten, PARA method)

### Implementation
- [[implementation-roadmap]] — Timeline and phases (immediate, medium-term, long-term)

## Research Date

**Conducted**: 2026-03-12 by agent research_external_memory_systems
**Frameworks evaluated**: 10+ (Mem0, SimpleMem, Zep/Graphiti, LangGraph, CrewAI, LlamaIndex, Motorhead, mcp-memory-service, OpenMemory, Microsoft GraphRAG)
**Focus**: PostgreSQL + pgvector + Voyage AI compatibility

## Key Takeaway

**No external dependencies needed.** Our PostgreSQL + pgvector stack is sufficient. Adopt:
1. Mem0's automatic extraction pattern
2. SimpleMem's semantic lossless compression algorithm
3. pgvector 0.8's iterative index scans
4. Hybrid BM25+vector search
5. Simplify to 3-5 tools (from 15+)

Expected impact: 26.4% F1 improvement, 30x token reduction, better user experience through simpler tool interface.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\research\README.md

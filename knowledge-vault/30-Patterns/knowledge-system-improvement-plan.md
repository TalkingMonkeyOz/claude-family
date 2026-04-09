---
projects:
- claude-family
tags:
- knowledge-management
- rag
- architecture
- improvement-plan
---

# Knowledge System Improvement Plan

Companion to [[knowledge-system-audit-2026-04-09]]. Based on internal audit + industry research (2025-2026).

## Industry Best Practices (Research Summary)

### RAG Architecture
- **Hybrid search (vector + BM25) is table stakes** — beats pure vector by ~18% recall
- **Re-ranking** via cross-encoder after hybrid retrieval is now standard
- **Semantic chunking** (split on meaning boundaries) achieves 87% accuracy vs 13% for fixed-size
- Sources: Firecrawl 2025, Pinecone chunking strategies, RAGFlow 2025 review

### Multi-Store Search
- **Unified source selection** during retrieval (UniMS-RAG), not per-store queries
- Atlassian Rovo uses "Teamwork Graph" — relationships across all products
- **Intent recognition** shifts retrieval strategy (informational vs action-driven)
- **Feedback loops** track which knowledge helped, feed back into ranking

### Context Management
- JetBrains: **observation masking beats summarization** (52% cost cut, 2.6% higher solve rates)
- Every LLM degrades with more context — shorter, precise injection wins
- Our budget-capped approach is directionally correct

### Storage & Indexing
- pgvector sufficient at our scale (471 QPS at 99% recall on 50M vectors)
- Voyage AI outperforms alternatives for code/technical content
- **Hierarchical chunking**: parent chunks (full section) + child chunks (256-512 tokens)

## Proposed Phases

### Phase 1: Quick Wins (This Week)
1. **Fix Knowledge Curator SQL bug** — cast `applies_to_projects` to `text[]` properly
2. **Add nimbus-mui to NIMBUS_PROJECTS** in `scripts/rag_queries.py`
3. **Add entity catalog search** to RAG hook pipeline
4. **Add workfile search** to RAG hook pipeline
5. **Fix PostgreSQL Backup** Windows task (exit code -196608)

### Phase 2: Unified Retrieval (1-2 Weeks)
Replace per-source priority system with Reciprocal Rank Fusion (RRF):
- Fan out to all 5 stores in parallel
- Normalize scores to [0,1] across sources
- Source diversity guarantee (1+ from each matching store)
- Budget-fill by unified relevance score

### Phase 3: Knowledge Compiler (2-4 Weeks)
Extend Knowledge Curator to compile fragments into vault articles:
- Identify topic clusters across all stores (not just knowledge table)
- Use domain_concept entities as cluster anchors
- LLM-compose coherent vault documents from scattered fragments
- Weekly batch job after curator completes

### Phase 4: Hierarchical Chunking (2-4 Weeks, parallel)
Upgrade `embed_vault_documents.py`:
- Split by `##` headers (parent) then 256-512 token sub-chunks (child)
- Add `parent_chunk_id` to vault_embeddings
- Search children for precision, return parents for context
- Re-embed all 890 vault documents

### Phase 5: Feedback Loops (Longer Term)
- Log retrieval events (what was injected)
- Track usage signals (explicit `recall_entities()` = RAG miss signal)
- Boost frequently-useful knowledge, decay retrieved-but-ignored

## What NOT to Change

- 5-store architecture (sound design)
- Markdown for vault (human-readable, git-trackable, Obsidian-compatible)
- pgvector (massively sufficient at our scale)
- Voyage AI embeddings (top performer for code/technical)
- 3-tier lifecycle with decay/promotion (aligned with best practices)
- `remember()` routing logic (dedup/contradiction detection is good)

## Key References

- [[knowledge-system-audit-2026-04-09]] — current state audit
- JetBrains: Efficient Context Management (Dec 2025)
- UniMS-RAG: Unified Multi-source RAG (arXiv 2401.13256)
- Rovo AI Search Architecture (Atlassian)
- RAGFlow 2025 Year-End Review

---
**Version**: 1.0
**Created**: 2026-04-09
**Updated**: 2026-04-09
**Location**: knowledge-vault/30-Patterns/knowledge-system-improvement-plan.md

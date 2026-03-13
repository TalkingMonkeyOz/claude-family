---
projects:
- claude-family
- project-metis
tags:
- research
- memory-patterns
- tiering
synced: false
---

# Memory Patterns: Tiering, Deduplication, and Consolidation

Detailed analysis from [[research-external-memory-systems]].

## Tiered Memory — Academic Validation

A December 2025 Tsinghua University survey validates our three-tier model:

| Academic Category | Our Tier | Description | Mem0 | SimpleMem |
|-------------------|----------|-------------|------|-----------|
| **Working** | SHORT | Current context, credentials | Context window | Context window |
| **Episodic** | MID | Past interactions, decisions | LLM-extracted facts | Entropy-filtered units |
| **Semantic** | LONG | Facts, patterns, procedures | Graph relationships | Recursive consolidation |

**Key insight**: The three-tier pattern is validated. What differs is the promotion mechanism.

**Our gap**: Our promotion pipeline (access_count >= 5, age >= 7d) lacks LLM-assisted consolidation. SimpleMem's recursive consolidation is the pattern to adopt.

## Semantic Deduplication at Scale

Production deduplication follows three stages:

1. **Fast string matching** — Levenshtein/Jaccard distances (cheap)
2. **Embedding similarity** — Cluster with k-means, then pairwise within clusters
3. **LLM adjudication** — For borderline cases

**NVIDIA's SemDeDup**: Clustering reduces O(n²) comparisons to manageable sizes.

**Our current approach** (cosine > 0.75 across all memories) won't scale past thousands. **Action**: Partition by component/topic first, then deduplicate within partitions.

## Cross-Session Continuity

| Pattern | Mem0 | SimpleMem | Zep | Our System |
|---------|------|-----------|-----|-----------|
| **Fact extraction** | Auto, LLM | Auto, entropy-aware | Manual | Manual (gap) |
| **Consolidation** | Update existing | Recursive merge | Temporal validity | Tier-based |
| **Session bridge** | Memory vectors | Compressed memories | Time-travel queries | Session notes |

**What works best**: Automatic extraction + structured session notes. Mem0 does extraction; we do notes. Combine both.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\research\memory-patterns-tiering-dedup.md

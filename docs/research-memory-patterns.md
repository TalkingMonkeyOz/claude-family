---
projects:
- claude-family
- project-metis
tags:
- research
- memory-systems
- patterns
synced: false
---

# Memory System Patterns: Tiered Memory, Deduplication, and Consolidation

Detailed analysis from [[research-external-memory-systems]].

## Tiered Memory — Academic Validation

A December 2025 Tsinghua University survey validates our three-tier model (working/episodic/semantic):

| Academic Category | Our Tier | Description | Mem0 Approach | SimpleMem Approach |
|-------------------|----------|-------------|---------------|--------------------|
| **Working Memory** | SHORT | Current context, credentials, configs | Context window | Context window |
| **Episodic Memory** | MID | Past interactions, decisions, what happened | LLM-extracted facts, merged | Entropy-filtered units |
| **Semantic Memory** | LONG | Facts, patterns, procedures, domain knowledge | Graph relationships | Recursive consolidation |

**Key insight**: The three-tier pattern is well-validated across all major frameworks. What differs is the **promotion mechanism**.

**Our gap**: Our promotion pipeline (access_count >= 5, age >= 7d) is reasonable but lacks LLM-assisted consolidation. SimpleMem's recursive consolidation is the pattern to adopt.

## Semantic Deduplication at Scale

Production approaches follow a three-stage funnel:

1. **Fast string matching** — Levenshtein/Jaccard distances, cheap, catches obvious duplicates
2. **Embedding similarity** — Cluster with k-means, compute pairwise cosine similarity within clusters (SemDeDup algorithm)
3. **LLM adjudication** — For borderline cases, use LLM to determine true duplicate vs. subtle difference

**NVIDIA's SemDeDup**: Clustering step reduces O(n²) comparisons to manageable sizes. Our threshold of 0.75 is reasonable; production systems use 0.80-0.85.

**Our current approach** (cosine > 0.75 across all memories) will not scale past thousands of entries. **Action**: Partition by component/topic first, then deduplicate within partitions.

## Cross-Session Continuity Patterns

| Pattern | Description | Mem0 | SimpleMem | Zep | Our System |
|---------|-------------|------|-----------|-----|-----------|
| **Fact extraction** | Auto, LLM-based | Yes, automatic | Yes, entropy-aware | Manual | Manual (gap) |
| **Consolidation** | Merge/evolve memories | Update existing | Recursive merge | Temporal validity | Tier-based (brittle) |
| **Session bridge** | How context survives | Memory vectors | Compressed memories | Time-travel queries | Session notes (works) |

**What works best**: Automatic extraction + structured session notes. Mem0 does extraction automatically; we use manual notes. Combine both.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\research-memory-patterns.md

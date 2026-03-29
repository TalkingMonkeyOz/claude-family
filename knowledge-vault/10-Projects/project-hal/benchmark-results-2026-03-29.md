---
projects:
- project-hal
tags:
- benchmark
- research
- ckg
- pattern-generation
---

# HAL Benchmark Results -- 2026-03-29

## Experiment Design

- 3 conditions: Vanilla (no context), CKG (structured codebase context ~684 tokens), Pattern (Jinja2 template generation)
- 4 OData fetcher tasks (BM-001 easy, BM-002 medium w/ filter, BM-003 medium modification, BM-004 hard w/ extra params)
- Element-presence conformance scoring (binary: expected string found in output)
- Both AI conditions: raw API call, single shot, no tools/memory/skills/MCP -- ONLY difference is system prompt content
- Pattern condition: no AI at all, pure Jinja2 template instantiation
- Models tested: Haiku 4.5 ($1/M), Sonnet 4.6 ($3/M), Opus 4.6 ($5/M)
- Runs: n=5 per task per condition per model for AI conditions; n=1 for pattern (deterministic)
- Temperature: 1.0 for AI conditions

## 2-Way Results (CKG vs Vanilla, n=5)

| Model | Vanilla | CKG | Delta | All sig? |
|-------|---------|-----|-------|----------|
| Haiku 4.5 | 53.4% | 92.2% | +38.8pp | YES (4/4) |
| Sonnet 4.6 | 57.9% | 94.7% | +36.8pp | YES (4/4) |
| Opus 4.6 | 54.6% | 90.3% | +35.7pp | YES (4/4) |

## 3-Way Results (Sonnet 4.6, n=3)

| Approach | Conformance | Cost | Speed | Variance |
|----------|------------|------|-------|----------|
| Vanilla | 56.6% | $$$ (API) | 2-15s | High |
| CKG context | 93.5% | $$ (API + 684 tokens) | 4-5s | Low |
| Pattern gen | 100.0% | Free (no API) | 0.08s | Zero |

## Token Efficiency

- Vanilla: avg 138 input, 1181-1330 output (verbose, improvising)
- CKG: avg 824 input, 514-528 output (focused, pattern-following)
- Context adds 684 input tokens but REDUCES output by ~700 tokens -- net cost neutral

## Key Findings

1. CKG effect is large (+35-39pp), consistent, model-independent
2. Vanilla scores DON'T improve with model size (53-58% across all tiers)
3. Haiku+CKG (92.2%) beats Opus vanilla (54.6%) -- 5x cheaper model wins
4. Pattern generation hits 100% on ALL tasks including ones CKG missed
5. CKG persistent misses: $filter=Deleted eq false (0%), $expand=AwardRuleDetailList (20-40%)
6. Pattern generation closes all gaps -- 100% on every element, every task

## Raw Data Files

- benchmarks/results/2026-03-29_haiku_n1.json (pilot)
- benchmarks/results/2026-03-29_5_n5_t1.0.json (Haiku n=5)
- benchmarks/results/2026-03-29_6_n5_t1.0.json (Sonnet n=5, Opus n=5)
- benchmarks/results/2026-03-29_6_n3_t1.0.json (3-way Sonnet n=3)

---
**Version**: 1.0
**Created**: 2026-03-29
**Updated**: 2026-03-29
**Location**: knowledge-vault/10-Projects/project-hal/benchmark-results-2026-03-29.md

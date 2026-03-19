---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/9
  - type/testing
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Gate 2 Deliverable 9: Test Strategy

## Overview

Testing in METIS covers two distinct domains: **platform testing** (does the software work?) and **knowledge quality testing** (are the AI answers good?). Both use BPMN models as the primary test generation source.

---

## 1. BPMN-to-Test Generation

### The Loop (CRITICAL — Not One-Shot)

BPMN testing is **iterative, minimum 2 cycles:**

```
Model BPMN → Generate Tests → Run Tests → Identify Gaps
     ↑                                          │
     └──── Fix Model ← Regenerate Tests ←───────┘
```

Repeat until clean. The BPMN model and tests improve each other through iteration. A passing test suite against a first-draft BPMN is suspect — gaps haven't been found yet.

### Generation Pipeline

1. **Path extraction** — Walk BPMN model, extract every possible path: happy path + each gateway branch + error events. Each path = one test scenario skeleton.
2. **Input generation** — Two sources:
   - DMN decision tables (if gateway references DMN → input/output columns define test data)
   - Knowledge base (if no DMN → query for expected inputs, generate from examples)
3. **Expected output derivation** — BPMN end events + intermediate outputs define success criteria per path.
4. **Test case assembly** — Name (from path), inputs (from DMN/knowledge), expected outputs (from model), steps to execute.

### Human Review Model

- **Default:** AI-assisted — system generates draft test cases, human reviews/adjusts before activation
- **Override:** Configurable auto-approve for customers/admins who trust the system (RBAC permission)
- **Growth:** As confidence builds, auto-approval can expand to low-risk paths
- Same RBAC override pattern as retention and token budgets

Approved tests become the **regression baseline**.

---

## 2. RAG Quality Metrics (Full Suite from Day One)

All six metrics measured from launch. The feedback loop is core — human reviews improve confidence over time, reducing future review volume.

| Metric | What | How | Target |
|--------|------|-----|--------|
| **Retrieval Relevance** | Did we find the right knowledge? | Top-5 items judged relevant (LLM + human) | > 80% |
| **Groundedness** | Is the answer supported by citations? | Every claim traceable to source | > 90% |
| **Hallucination Rate** | Did the system invent facts? | Claims without source support | < 5% |
| **Answer Correctness** | Is the answer actually right? | Human/LLM judge against gold standard | > 85% |
| **Freshness Accuracy** | Using current knowledge? | Retrieved items' freshness vs source reality | > 90% |
| **Coverage** | Missed relevant knowledge? | Known-relevant items not retrieved | < 15% missed |

### Automation vs Human Judgment

| Metric | Automatable? | Notes |
|--------|-------------|-------|
| Retrieval Relevance | Partially — LLM-as-judge, calibrated with human review | |
| Groundedness | Yes — check citations exist in retrieved context | |
| Hallucination | Partially — LLM cross-check against sources | |
| Correctness | No — requires domain expert or gold standard | |
| Freshness | Yes — compare freshness_score to source timestamp | |
| Coverage | Partially — requires known-relevant set | |

All targets are internal quality metrics needing calibration with real production data.

---

## 3. Test Coverage Dimensions

| Dimension | What | Measurement | Primary? |
|-----------|------|-------------|----------|
| **BPMN Path Coverage** | Every path through every process has tests | Paths tested / total paths | **Yes — primary metric** |
| **Knowledge Type Coverage** | Each of 6 knowledge types has retrieval tests | Types tested / 6 | Secondary |
| **Scope Level Coverage** | Tests at org, product, client, engagement levels | Levels tested / 4 | Secondary |
| **Error Path Coverage** | Error events and failure branches tested | Error paths tested / total | Secondary |
| **Connector Coverage** | Each active connector type has integration tests | Connectors tested / active | Secondary |

**Target:** BPMN path coverage > 80% as the gate. All targets configurable per engagement via admin centre.

---

## 4. Testing Pyramid

### Platform Testing (Does the software work?)

| Layer | Tool | Scope | DB? |
|-------|------|-------|-----|
| **Unit** | Vitest (TS) / pytest (Python) | Pure logic, no IO | No |
| **Integration** | Testcontainers (C1-4) | API + DB + embeddings | Real PG18+pgvector |
| **E2E** | TBD (Playwright likely) | Full user workflows | Real instance |

### Knowledge Quality Testing (Are the answers good?)

| Layer | What | How Often |
|-------|------|-----------|
| **Evaluation Suite** | 50+ test questions per engagement | Every deployment |
| **Regression** | Baseline comparison for answer drift | Every knowledge change |
| **Live Monitoring** | RAG quality metrics on production queries | Continuous |
| **Feedback Loop** | User corrections → improvement → retest | Ongoing |

---

## 5. CI/CD Quality Gates (Prior Design)

5-stage pipeline with quality gates:

| Stage | Gate | Blocks? |
|-------|------|---------|
| 1. Build | Compilation, lint, type check | Yes |
| 2. Unit Test | All unit tests pass | Yes |
| 3. Integration Test | Testcontainers tests pass | Yes |
| 4. Knowledge Quality | Evaluation suite meets thresholds | Yes |
| 5. Deploy | Manual approval (MVP) → auto (later) | Configurable |

---

## 6. When Human Review Goes to Humans

Items sent for human review must include:
- **Explanation** — why the system flagged this
- **Suggestions** — what the system thinks the answer/fix should be
- **Confidence** — how sure it is

UX design for the human review experience is a separate deliverable (tied to Journey Maps, Deliverable #10).

---

## 7. Open Items (Gate 3)

- [ ] Evaluation suite question design (50+ per engagement)
- [ ] E2E test framework selection
- [ ] Regression detection sensitivity tuning
- [ ] Human review UX/workflow design
- [ ] Test data generation strategy for non-production environments
- [ ] Performance/load testing approach

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-09-test-strategy.md

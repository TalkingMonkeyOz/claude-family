---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/4
  - type/dmn
status: complete
---

# Gate 2 Deliverable 4: Decision Models (DMN)

Formalises business rules from the [[gate-one/business-rules-inventory|Business Rules Inventory]] (52 rules, 7 categories) and Gate 2 design decisions into implementable DMN decision tables. Each table replaces prose descriptions with explicit, testable, auditable rules. See [[deliverable-04-dmn-decisions-detail|Detail File]] for tables DT-05 through DT-08.

---

## DMN Approach

**Hit Policies Used:**
- **U (Unique):** Exactly one rule matches. Input combinations are exhaustive and non-overlapping.
- **F (First):** Rules evaluated top-to-bottom; first match wins. Order is significant.
- **C (Collect):** All matching rules fire; outputs collected into list.

**Validated Decisions That Constrain These Tables:**
- Decision #9: No keyword matching — embeddings only for retrieval
- Decision #11: Event-driven freshness, not time-based decay
- Rules AG-01, AG-12 (PR-02): DMN governs all decision points, not embedded prompts

---

## Decision Table Index

| ID | Name | Hit Policy | Rules | Source Rules |
|----|------|-----------|-------|--------------|
| DT-01 | Knowledge Validation Tier | U | 4 | DG-01 to DG-05 |
| DT-02 | Scope Promotion Eligibility | U | 6 | DG-06 to DG-11 |
| DT-03 | Retrieval Ranking Signal Weights | F | 6 | QU-07, AR-09, Decision #9 |
| DT-04 | Content Chunking Strategy | U | 5 | Decision #8, QU-06 |
| DT-05 | Agent Autonomy Level | U | 9 | AG-01, AG-13, SE-03 |
| DT-06 | Token Budget Enforcement Action | F | 4 | C6-2, AG-14 |
| DT-07 | Data Retention Category | U | 9 | DG-17, C2-5, C6-4 |
| DT-08 | Quality Gate Pass/Fail | U | 6 | QU-04, deliverable-09 |

---

## DT-01: Knowledge Validation Tier Assignment

**Decision ID:** DT-01
**Hit Policy:** U (Unique)
**Source:** DG-01 to DG-05

Determines the validation path every knowledge item must follow before activation.

**Inputs:**

| source_type | content_category | is_ai_generated |
|---|---|---|
| `enum` | `enum` | `boolean` |

**Output:**

| validation_tier | auto_approved | requires_human_review | trust_level |
|---|---|---|---|
| `string` | `boolean` | `boolean` | `string` |

**Rules:**

| # | source_type | content_category | is_ai_generated | validation_tier | auto_approved | requires_human_review | trust_level |
|---|---|---|---|---|---|---|---|
| 1 | `api_doc`, `config_snapshot`, `metadata` | any | `false` | T1 | true | false | high |
| 2 | `human_authored` | `compliance`, `rules`, `procedures` | `false` | T2 | false | true | high |
| 3 | `human_authored` | any | `false` | T2 | false | true | medium |
| 4 | `support_resolution`, `decision_record` | any | `false` | T3 | true | false | low |
| 5 | any | any | `true` | T4 | false | true | none |
| 6 | `promoted` | any | any | T2 | false | true | medium |

---

## DT-02: Scope Promotion Eligibility

**Decision ID:** DT-02
**Hit Policy:** U (Unique)
**Source:** DG-06 to DG-11

Determines whether a knowledge item may be promoted to a higher scope level.

**Inputs:**

| knowledge_type | contains_client_config | is_confidential | has_anonymisation | current_scope |
|---|---|---|---|---|
| `enum` | `boolean` | `boolean` | `boolean` | `enum` |

**Output:**

| promotion_eligible | blocked_reason | requires_approval |
|---|---|---|
| `boolean` | `string` | `boolean` |

**Rules:**

| # | knowledge_type | contains_client_config | is_confidential | has_anonymisation | current_scope | promotion_eligible | blocked_reason | requires_approval |
|---|---|---|---|---|---|---|---|---|
| 1 | any | true | any | any | any | false | CLIENT_CONFIG_NEVER_PROMOTES | — |
| 2 | any | any | true | any | any | false | CONFIDENTIAL_BLOCKED | — |
| 3 | `client_context` | any | any | any | any | false | CLIENT_CONTEXT_NEVER_PROMOTES | — |
| 4 | `decision_record` | any | any | any | any | false | DECISION_RECORDS_NEVER_PROMOTE | — |
| 5 | any | false | false | false | `client` | false | ANONYMISATION_REQUIRED | — |
| 6 | any | false | false | true | `client` | true | — | true |

---

## DT-03: Retrieval Ranking Signal Weights

**Decision ID:** DT-03
**Hit Policy:** F (First)
**Source:** QU-07, AR-09, Decision #9 (no keyword matching)

Returns signal weights for the ranking pipeline. Order matters — more specific contexts override general. Weights sum to 1.0 and are applied to the composite score. **Note:** Weights are configurable per deployment; table values are defaults.

**Inputs:**

| query_context | agent_type | user_has_feedback_history |
|---|---|---|
| `enum` | `enum` | `boolean` |

**Output:**

| w_semantic | w_freshness | w_validation_tier | w_scope_specificity | w_coaccess | w_user_feedback | note |
|---|---|---|---|---|---|---|
| `float` | `float` | `float` | `float` | `float` | `float` | `string` |

**Rules:**

| # | query_context | agent_type | user_has_feedback_history | w_semantic | w_freshness | w_validation_tier | w_scope_specificity | w_coaccess | w_user_feedback | note |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `compliance` | any | any | 0.35 | 0.30 | 0.20 | 0.10 | 0.05 | 0.00 | Freshness critical for compliance |
| 2 | `technical_config` | any | any | 0.40 | 0.25 | 0.15 | 0.15 | 0.05 | 0.00 | Config accuracy prioritised |
| 3 | any | `conversational` | true | 0.40 | 0.15 | 0.15 | 0.15 | 0.05 | 0.10 | Personalise with feedback |
| 4 | any | `conversational` | false | 0.45 | 0.20 | 0.15 | 0.15 | 0.05 | 0.00 | No feedback history yet |
| 5 | any | `workflow` | any | 0.35 | 0.20 | 0.20 | 0.20 | 0.05 | 0.00 | Scope specificity matters in workflows |
| 6 | any | any | any | 0.40 | 0.20 | 0.15 | 0.15 | 0.10 | 0.00 | Default weights |

---

## DT-04: Content Chunking Strategy

**Decision ID:** DT-04
**Hit Policy:** U (Unique)
**Source:** Decision #8 (content-aware chunking), QU-06 (natural boundaries)

Assigns chunking strategy per content type. Fixed token counts are never used (Decision #8). **Note:** `max_chunk_tokens` values are configurable per deployment; table values are defaults.

**Inputs:**

| content_type | avg_section_tokens | has_structured_sections |
|---|---|---|
| `enum` | `int` | `boolean` |

**Output:**

| strategy | boundary_signal | max_chunk_tokens | overlap_tokens | preserve_structure |
|---|---|---|---|---|
| `string` | `string` | `int` | `int` | `boolean` |

**Rules:**

| # | content_type | avg_section_tokens | has_structured_sections | strategy | boundary_signal | max_chunk_tokens | overlap_tokens | preserve_structure |
|---|---|---|---|---|---|---|---|---|
| 1 | `code` | any | any | semantic_unit | function/class boundary | 500 | 0 | true |
| 2 | `table` | any | any | whole_table | table end | 800 | 0 | true |
| 3 | `api_reference` | any | any | endpoint_per_chunk | endpoint separator | 600 | 50 | true |
| 4 | `markdown` | ≤ 400 | true | section_boundary | heading level 2/3 | 600 | 100 | false |
| 5 | `markdown` | > 400 | any | paragraph_boundary | blank line | 400 | 75 | false |
| 6 | `prose` | any | any | paragraph_boundary | blank line | 400 | 75 | false |
| 7 | `mixed` | any | any | hybrid | heading then blank line | 500 | 75 | false |

See [[deliverable-04-dmn-decisions-detail|Detail File]] for DT-05 (Agent Autonomy), DT-06 (Token Budget), DT-07 (Data Retention), DT-08 (Quality Gate).

---

**Version**: 1.1
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-04-dmn-decisions.md

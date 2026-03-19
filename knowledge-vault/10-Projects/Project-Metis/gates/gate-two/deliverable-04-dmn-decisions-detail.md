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

# Gate 2 Deliverable 4: Decision Models (DMN) — Detail

Continuation of [[deliverable-04-dmn-decisions|Deliverable 4 Main File]] (DT-01 to DT-04 there).

---

## DT-05: Agent Autonomy Level

**Decision ID:** DT-05
**Hit Policy:** U (Unique)
**Source:** AG-01 (autonomy is earned), AG-13 (read-only by default), SE-03 (agent access ceiling)

Determines what an agent is permitted to do without explicit human approval in the current context. **Note:** The 90% `approval_rate_pct` threshold (rule 4) is configurable per deployment.

**Inputs:**

| operation_type | agent_tier | approval_rate_pct | explicit_whitelist | human_present |
|---|---|---|---|---|
| `enum` | `enum` | `int (0-100)` | `boolean` | `boolean` |

**Output:**

| autonomy_level | can_execute | requires_queue | action |
|---|---|---|---|
| `string` | `boolean` | `boolean` | `string` |

**Rules:**

| # | operation_type | agent_tier | approval_rate_pct | explicit_whitelist | human_present | autonomy_level | can_execute | requires_queue | action |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `read` | any | any | any | any | full | true | false | EXECUTE |
| 2 | `gate_skip` | any | any | any | any | none | false | false | HARD_BLOCK — agents never skip gates (AG-02) |
| 3 | `write` | any | any | true | any | whitelisted | true | false | EXECUTE — explicitly whitelisted |
| 4 | `write` | `system` | ≥ 90 | false | any | earned | true | false | EXECUTE — proven competence |
| 5 | `write` | any | any | false | true | supervised | false | true | QUEUE_FOR_HUMAN — human present |
| 6 | `write` | any | any | false | false | supervised | false | true | QUEUE_FOR_HUMAN — unattended |
| 7 | `delete` | any | any | any | any | none | false | true | QUEUE_FOR_HUMAN — deletes always queued |
| 8 | `config_change` | any | any | any | false | none | false | true | QUEUE_FOR_HUMAN — unattended config |
| 9 | `config_change` | any | any | true | true | whitelisted | true | false | EXECUTE — whitelisted + supervised |

---

## DT-06: Token Budget Enforcement Action

**Decision ID:** DT-06
**Hit Policy:** F (First)
**Source:** C6-2 (graduated 4-level hierarchy), AG-14 (cost cap per autonomous run)

Determines enforcement action at each budget check. First matching rule wins — thresholds are evaluated top-down (most severe first).

**Inputs:**

| budget_pct_used | budget_level | is_autonomous_run |
|---|---|---|
| `int (0-100)` | `enum` | `boolean` |

**Output:**

| action | context_adjustment | alert_admin | user_message |
|---|---|---|---|
| `string` | `string` | `boolean` | `string` |

**Rules:**

| # | budget_pct_used | budget_level | is_autonomous_run | action | context_adjustment | alert_admin | user_message |
|---|---|---|---|---|---|---|---|
| 1 | ≥ 100 | any | true | HARD_STOP | none | true | Autonomous run terminated — cost cap reached. |
| 2 | ≥ 100 | any | any | REJECT | none | true | Budget exceeded. Request rejected. Contact admin to increase allocation. |
| 3 | ≥ 95 | `request` | any | WARN_REJECT | none | true | Approaching limit. Completing this request but alerting admin. |
| 4 | ≥ 80 | any | any | SLIM_DOWN | shorter_context, summarised_knowledge, reduced_history | false | Optimising response to stay within budget. |

---

## DT-07: Data Retention Category Assignment

**Decision ID:** DT-07
**Hit Policy:** U (Unique)
**Source:** DG-17 (tiered audit retention), C2-5 (tiered presets), C6-4 (log retention)

Assigns a retention tier and default days to each data category. Customer can override within floor/ceiling via `customer_retention_config`.

**Inputs:**

| data_category | is_security_event | is_compliance_flagged |
|---|---|---|
| `enum` | `boolean` | `boolean` |

**Output:**

| retention_tier | default_days | floor_days | ceiling_days | customer_adjustable |
|---|---|---|---|---|
| `string` | `int or null` | `int` | `int or null` | `boolean` |

**Rules:**

| # | data_category | is_security_event | is_compliance_flagged | retention_tier | default_days | floor_days | ceiling_days | customer_adjustable |
|---|---|---|---|---|---|---|---|---|
| 1 | any | true | any | permanent | null | null | null | false |
| 2 | any | any | true | permanent | null | null | null | false |
| 3 | `knowledge_item` | false | false | permanent | null | 365 | null | false |
| 4 | `workflow_step_log` | false | false | extended | 1095 | 730 | null | true |
| 5 | `audit_log` | false | false | extended | 1095 | 730 | null | false |
| 6 | `session_activity` | false | false | standard | 365 | 90 | null | true |
| 7 | `agent_interaction` | false | false | short | 90 | 30 | null | true |
| 8 | `llm_call_log` | false | false | short | 30 | 7 | null | true |
| 9 | `application_log` | false | false | short | 90 | 30 | null | true |
| 10 | `performance_metric` | false | false | standard | 365 | 90 | null | true |
| 11 | `embedding` | false | false | match_source | null | 0 | null | false |

---

## DT-08: Quality Gate Pass/Fail

**Decision ID:** DT-08
**Hit Policy:** U (Unique)
**Source:** QU-04 (5-question minimum), deliverable-09 RAG metrics, CI/CD pipeline gates

Determines whether a quality gate passes, fails, or triggers a warning. Gates are evaluated per stage; each row is a standalone gate check. **Note:** Thresholds are configurable per engagement; table values are defaults.

**Inputs:**

| gate_type | metric_name | measured_value | threshold |
|---|---|---|---|
| `enum` | `enum` | `float` | `float` |

**Output:**

| result | blocks_pipeline | action | detail |
|---|---|---|---|
| `string` | `boolean` | `string` | `string` |

**Rules:**

| # | gate_type | metric_name | measured_value | threshold | result | blocks_pipeline | action | detail |
|---|---|---|---|---|---|---|---|---|
| 1 | `knowledge_publish` | eval_question_count | < 5 | 5 | FAIL | true | BLOCK | Minimum 5 evaluation questions required (QU-04) |
| 2 | `rag_quality` | retrieval_relevance | < 0.80 | 0.80 | FAIL | true | BLOCK | < 80% retrieval relevance |
| 3 | `rag_quality` | groundedness | < 0.90 | 0.90 | FAIL | true | BLOCK | < 90% groundedness |
| 4 | `rag_quality` | hallucination_rate | > 0.05 | 0.05 | FAIL | true | BLOCK | Hallucination rate exceeds 5% |
| 5 | `rag_quality` | answer_correctness | < 0.85 | 0.85 | WARN | false | FLAG_FOR_REVIEW | < 85% correctness — human review |
| 6 | `bpmn_coverage` | path_coverage_pct | < 0.80 | 0.80 | FAIL | true | BLOCK | BPMN path coverage < 80% |
| 7 | `ci_pipeline` | unit_tests | < 1.00 | 1.00 | FAIL | true | BLOCK | All unit tests must pass |
| 8 | `ci_pipeline` | integration_tests | < 1.00 | 1.00 | FAIL | true | BLOCK | All integration tests must pass |
| 9 | any | any | ≥ threshold | threshold | PASS | false | PROCEED | Gate cleared |

---

## Implementation Notes

**Design principle:** All operational parameters have sensible defaults but are configurable via the admin centre per deployment/engagement. Table values throughout this document are defaults, not fixed constants.

**Evaluation order for DT-08:** Check FAIL rules before PASS — a metric can trigger multiple rows in theory, so FAIL takes precedence. Apply F (First) semantics if refactoring to strict DMN.

**DT-03 weight calibration:** Initial weights are design estimates. Recalibrate after 30 days of production queries using co-access signals from `activity_access_log`.

**DT-05 approval_rate_pct tracking:** Computed per `(agent_tier, operation_type)` pair from `audit_log` over rolling 90-day window. Not per-agent-instance — per tier.

**DT-07 null default_days:** Null means permanent (no expiry). Soft-delete job skips rows with null retain_days.

---

**Version**: 1.1
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-04-dmn-decisions-detail.md

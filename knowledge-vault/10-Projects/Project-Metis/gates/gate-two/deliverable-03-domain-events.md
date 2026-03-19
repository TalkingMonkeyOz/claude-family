---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/3
  - type/ddd
created: 2026-03-15
updated: 2026-03-15
status: draft
---

# Domain Events Catalogue

Parent: [[gate-two/deliverable-03-domain-model|Domain Model]]

## Event Index

### Knowledge Store Events

| Event | Payload | Consumers | Trigger |
|-------|---------|-----------|---------|
| `KnowledgeIngested` | item_id, scope, knowledge_type, source | Work Context, Test Assets | New knowledge item stored and embedded |
| `KnowledgePromoted` | item_id, from_scope, to_scope, promoted_by | Delivery Pipeline | Knowledge promoted from client → product level |
| `KnowledgeSuperseded` | old_id, new_id, reason | All consumers | Knowledge item replaced by newer version |
| `KnowledgeFreshnessUpdated` | item_id, new_score, event_source | Work Context | Freshness score changed (event-driven, Decision #11) |

### Delivery Pipeline Events

| Event | Payload | Consumers | Trigger |
|-------|---------|-----------|---------|
| `GatePassed` | pipeline_id, gate_id, engagement_id | Work Management, Test Assets | Gate validation succeeded |
| `GateFailed` | pipeline_id, gate_id, failure_reasons | Defect Intelligence | Gate validation failed |
| `ReleaseDeployed` | release_id, engagement_id, environment | Knowledge Store | Release pushed to environment → freshness event |
| `PipelineInstantiated` | pipeline_id, template_id, engagement_id | Work Management | New pipeline created for engagement |

### Test Assets Events

| Event | Payload | Consumers | Trigger |
|-------|---------|-----------|---------|
| `TestFailed` | test_id, scenario_id, expected, actual | Defect Intelligence | Test execution failed |
| `RegressionDetected` | baseline_id, failing_tests, change_ref | Work Management | Regression found against baseline |
| `TestSuiteGenerated` | suite_id, source_bpmn, scenario_count | Agent Runtime | New test suite auto-generated from BPMN |

### Defect Intelligence Events

| Event | Payload | Consumers | Trigger |
|-------|---------|-----------|---------|
| `DefectResolved` | defect_id, resolution, resolved_by | Knowledge Store | Defect fixed — resolution is learning candidate |
| `PatternDetected` | pattern_id, defect_ids, confidence | Knowledge Store | Cross-customer pattern identified |
| `IssueThreadClosed` | thread_id, defects_resolved, duration | Work Management | All children closed + verified |

### Agent Runtime Events

| Event | Payload | Consumers | Trigger |
|-------|---------|-----------|---------|
| `SessionStarted` | session_id, user_id, scope, agent_type | Work Context | Agent session begins |
| `SessionEnded` | session_id, summary, learnings | Knowledge Store, Work Context | Session closes |
| `ComplianceViolation` | session_id, rule, severity, detail | Agent Runtime (self), AuditLog | Agent drifted from protocol |

### Work Context Events

| Event | Payload | Consumers | Trigger |
|-------|---------|-----------|---------|
| `ActivityStateChanged` | activity_id, old_state, new_state | Agent Runtime | Activity lifecycle transition |
| `WorkflowStepCompleted` | instance_id, step_name, actor | Agent Runtime, AuditLog | Write-through from engine (C2-4) |
| `WorkflowFailed` | instance_id, step_name, error | Defect Intelligence | Workflow execution error |

### Integration Events

| Event | Payload | Consumers | Trigger |
|-------|---------|-----------|---------|
| `SourceDataChanged` | connector_id, change_type, refs | Knowledge Store | External system data changed → re-ingest |
| `ConnectorHealthChanged` | connector_id, status, error | Agent Runtime | Connector went up/down |

### Commercial Events

| Event | Payload | Consumers | Trigger |
|-------|---------|-----------|---------|
| `EngagementCreated` | engagement_id, client_id, product_id | Tenant & Scope, Delivery Pipeline | New engagement provisioned |
| `SubscriptionChanged` | contract_id, changes | Tenant & Scope | Contract modified (features, limits) |

---

## Implementation Notes

- **Phase 1:** In-process event bus (simple pub/sub within the application). Sufficient for single-instance deployment.
- **Phase 2+:** Consider message queue (RabbitMQ, NATS) when cross-service communication needed or event replay required.
- **All events are logged** to the audit trail automatically.
- **Events are immutable** — once published, never modified.
- **Idempotent consumers** — handlers must tolerate duplicate delivery.

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-03-domain-events.md

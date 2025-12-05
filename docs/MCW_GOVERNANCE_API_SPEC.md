# MCW Governance API Specification

**Document Type**: API Specification
**Created**: 2025-12-04
**For**: mission-control-web

---

## Overview

API endpoints for MCW to display governance data and trigger actions.

---

## Endpoints

### GET /api/governance/compliance

Returns compliance status for all active projects.

**Response**:
```json
{
  "projects": [
    {
      "project_id": "uuid",
      "project_name": "string",
      "phase": "implementation",
      "has_claude_md": true,
      "has_problem_statement": true,
      "has_architecture": true,
      "compliance_pct": 100,
      "compliance_status": "compliant"
    }
  ],
  "summary": {
    "total_projects": 4,
    "compliant": 4,
    "partial": 0,
    "non_compliant": 0
  }
}
```

**SQL**:
```sql
SELECT
    project_id,
    project_name,
    phase,
    has_claude_md,
    has_problem_statement,
    has_architecture,
    compliance_pct,
    CASE
        WHEN compliance_pct = 100 THEN 'compliant'
        WHEN compliance_pct >= 50 THEN 'partial'
        ELSE 'non_compliant'
    END as compliance_status
FROM claude.v_project_governance
ORDER BY compliance_pct ASC, project_name;
```

---

### GET /api/governance/actions

Returns available governance actions.

**Query Params**:
- `requires_project`: boolean (optional) - filter by project requirement

**Response**:
```json
{
  "actions": [
    {
      "action_id": "uuid",
      "action_name": "project-init",
      "action_type": "project",
      "display_name": "Initialize New Project",
      "description": "Creates a new project with governance-compliant structure",
      "slash_command": "/project-init",
      "requires_project": false,
      "requires_confirmation": true,
      "parameters": {
        "required": ["project_name", "project_type"],
        "properties": {
          "project_name": {"type": "string"},
          "project_type": {"type": "string", "enum": ["web", "cli", "library", "infrastructure"]}
        }
      }
    }
  ]
}
```

**SQL**:
```sql
SELECT
    action_id,
    action_name,
    action_type,
    display_name,
    description,
    slash_command,
    requires_project,
    requires_confirmation,
    parameters
FROM claude.actions
WHERE available_in_mcw = true
ORDER BY action_type, action_name;
```

---

### POST /api/governance/actions/:action_name/execute

Trigger an action execution.

**Request**:
```json
{
  "project_id": "uuid (optional)",
  "parameters": {
    "key": "value"
  }
}
```

**Response**:
```json
{
  "status": "queued",
  "execution_id": "uuid",
  "message": "Action queued for execution"
}
```

**Implementation Note**:
For now, this can create a message in `claude.messages` that Claude will pick up on next session. Future: WebSocket or polling for real-time execution.

**SQL** (queue action):
```sql
INSERT INTO claude.messages (
    message_type,
    to_project,
    subject,
    body,
    priority,
    status
) VALUES (
    'task_request',
    $project_name,
    'Action: ' || $action_name,
    jsonb_build_object(
        'action_name', $action_name,
        'parameters', $parameters
    )::text,
    'normal',
    'pending'
)
RETURNING message_id;
```

---

### GET /api/documents/core

Returns core documents only.

**Query Params**:
- `project_id`: uuid (optional) - filter by project

**Response**:
```json
{
  "documents": [
    {
      "doc_id": "uuid",
      "doc_title": "Claude Family - Infrastructure Project",
      "doc_type": "CLAUDE_CONFIG",
      "file_path": "C:\\Projects\\claude-family\\CLAUDE.md",
      "status": "ACTIVE",
      "project_name": "claude-family",
      "is_core": true,
      "core_reason": "Claude configuration - applies to all sessions"
    }
  ],
  "count": 12
}
```

**SQL**:
```sql
SELECT
    doc_id,
    doc_title,
    doc_type,
    file_path,
    status,
    project_name,
    is_core,
    core_reason
FROM claude.v_core_documents
WHERE ($project_name IS NULL OR project_name = $project_name)
ORDER BY doc_type, doc_title;
```

---

### GET /api/projects/:id/work-summary

Returns work item summary for a project.

**Response**:
```json
{
  "project_id": "uuid",
  "project_name": "string",
  "phase": "implementation",
  "features": {
    "total": 24,
    "active": 1
  },
  "tasks": {
    "total": 0,
    "open": 0
  },
  "feedback": {
    "new": 1
  },
  "last_session": "2025-12-04T08:17:21Z"
}
```

**SQL**:
```sql
SELECT * FROM claude.v_project_work_summary
WHERE project_id = $project_id;
```

---

## UI Components

### Governance Dashboard

```
┌─────────────────────────────────────────────────────────┐
│ Governance Compliance                                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ●●●● 4/4 Projects Compliant                           │
│                                                         │
│  ┌─────────────┬─────────┬─────┬─────┬─────┬─────────┐ │
│  │ Project     │ Phase   │ C.md│ P.S.│ Arch│ Status  │ │
│  ├─────────────┼─────────┼─────┼─────┼─────┼─────────┤ │
│  │ claude-fam  │ impl    │ ✓   │ ✓   │ ✓   │ 100% 🟢 │ │
│  │ ATO-Tax     │ impl    │ ✓   │ ✓   │ ✓   │ 100% 🟢 │ │
│  │ MCW         │ impl    │ ✓   │ ✓   │ ✓   │ 100% 🟢 │ │
│  │ nimbus      │ impl    │ ✓   │ ✓   │ ✓   │ 100% 🟢 │ │
│  └─────────────┴─────────┴─────┴─────┴─────┴─────────┘ │
│                                                         │
│  [Scan Documents] [Check All]                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Action Buttons

For project detail page:
```
┌─────────────────────────────────────────┐
│ Actions                                  │
├─────────────────────────────────────────┤
│ [Check Compliance] [Retrofit Project]   │
│ [Scan Documents]                         │
└─────────────────────────────────────────┘
```

---

## Color Coding

| Compliance % | Color | Status |
|--------------|-------|--------|
| 100% | Green (#22c55e) | Compliant |
| 50-99% | Yellow (#eab308) | Partial |
| 0-49% | Red (#ef4444) | Non-compliant |

---

## TypeScript Types

```typescript
interface GovernanceCompliance {
  project_id: string;
  project_name: string;
  phase: 'idea' | 'research' | 'planning' | 'implementation' | 'maintenance' | 'archived';
  has_claude_md: boolean;
  has_problem_statement: boolean;
  has_architecture: boolean;
  compliance_pct: number;
  compliance_status: 'compliant' | 'partial' | 'non_compliant';
}

interface GovernanceAction {
  action_id: string;
  action_name: string;
  action_type: 'project' | 'document' | 'work' | 'system' | 'governance';
  display_name: string;
  description: string;
  slash_command: string | null;
  requires_project: boolean;
  requires_confirmation: boolean;
  parameters: {
    required: string[];
    properties: Record<string, { type: string; enum?: string[] }>;
  };
}

interface CoreDocument {
  doc_id: string;
  doc_title: string;
  doc_type: 'CLAUDE_CONFIG' | 'ARCHITECTURE' | 'ADR';
  file_path: string;
  status: string;
  project_name: string;
  is_core: boolean;
  core_reason: string;
}
```

---

**Version**: 1.0
**Related**: `claude.actions`, `claude.v_project_governance`, `claude.v_core_documents`

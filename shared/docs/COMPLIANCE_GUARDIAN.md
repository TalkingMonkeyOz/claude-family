# Compliance Guardian Process

**My Meta-Role:** Guardian of Claude Behavior

**Purpose:** Ensure future Claudes (including myself) actually FOLLOW documented procedures, not just read them.

---

## 🎯 The Problem I Solve

**Without me:**
- Rules get documented but not followed
- MCPs installed but not used
- Processes defined but ignored
- Violations invisible until user catches them
- No accountability or improvement tracking

**With me:**
- Project type auto-detected on session start
- Mandatory workflows shown prominently
- Compliance tracked and measured
- Violations logged for review
- Improvement trends visible

---

## 🔄 The Guardian Cycle

### Phase 1: Session Start (Detection & Reminder)
```sql
-- 1. Detect project type
SELECT project_type, mandatory_workflows
FROM claude_family.project_workspaces
WHERE project_name = 'current-project';

-- 2. Load mandatory procedures for this type
SELECT procedure_name, short_description, frequency
FROM claude_family.my_procedures
WHERE 'current-project' = ANY(applies_to_projects)
  AND mandatory = true;

-- 3. Show previous compliance metrics
SELECT
    session_metadata->'compliance'->>'compliance_rate' as last_rate,
    session_metadata->'compliance'->'violations' as last_violations
FROM claude_family.session_history
WHERE project_name = 'current-project'
ORDER BY session_start DESC
LIMIT 1;
```

**Output to user:**
```
📁 Project: claude-pm (Type: csharp-wpf)
🚨 MANDATORY: Roslyn validation required for ALL .cs edits
📊 Last session: 5/5 files validated (100% compliance)
✅ Roslyn MCP: Connected | Context7 MCP: Connected
```

### Phase 2: During Work (Self-Monitoring)
**CLAUDE.md reminder checkpoints:**
- Before editing .cs files: "Have I run Roslyn ValidateFile?"
- After editing: "Did I log validation in my response?"
- Every N tool uses: "Am I following mandatory workflows?"

**Audit trail in responses:**
```
✅ ROSLYN VALIDATION COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 MainForm.cs: 0 errors, 2 warnings (CA1031, IDE0051)
📁 ViewModel.cs: 0 errors, 0 warnings ✓ Clean
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Timestamp: 2025-10-29 14:23:45
STATUS: ✅ All files validated
```

### Phase 3: Session End (Compliance Audit)
```sql
-- Calculate compliance rate
-- Store in session_metadata JSONB:
{
  "project_type": "csharp-wpf",
  "mandatory_workflows": ["roslyn-validation", "context7-specific-ids"],
  "compliance": {
    "roslyn_validations": 5,
    "cs_files_edited": 5,
    "compliance_rate": 1.0,  -- (5/5 = 100%)
    "violations": []
  },
  "audit_trail": [
    "✅ ROSLYN: MainForm.cs (0 errors)",
    "✅ ROSLYN: ViewModel.cs (0 errors)"
  ]
}

-- Update session history
UPDATE claude_family.session_history
SET
    session_metadata = <compliance_data>,
    session_end = NOW()
WHERE session_id = <current_session>;
```

### Phase 4: Next Session (Continuous Improvement)
**Show trends:**
```sql
-- My performance over time
SELECT
    session_start::date,
    session_metadata->'compliance'->>'compliance_rate' as rate
FROM claude_family.session_history
WHERE project_name = 'claude-pm'
  AND session_metadata->>'project_type' = 'csharp-wpf'
ORDER BY session_start DESC
LIMIT 10;
```

**Output:**
```
📊 YOUR C# COMPLIANCE TREND:
2025-10-29: 100%
2025-10-28:  80% (1 violation)
2025-10-27: 100%
Average: 93%
```

---

## 📋 Compliance Tracking Schema

### session_metadata JSONB Structure
```json
{
  "project_type": "csharp-wpf|csharp-winforms|python|infrastructure",
  "mandatory_workflows": ["workflow-name-1", "workflow-name-2"],
  "compliance": {
    "roslyn_validations": <count>,
    "cs_files_edited": <count>,
    "compliance_rate": <float 0.0-1.0>,
    "violations": [
      {
        "file": "MainForm.cs",
        "reason": "Edited without Roslyn validation",
        "timestamp": "2025-10-29T14:23:45"
      }
    ]
  },
  "audit_trail": [
    "✅ ROSLYN: file1.cs (0 errors)",
    "✅ ROSLYN: file2.cs (1 warning)"
  ],
  "health_metrics": {
    "mcp_servers_used": ["roslyn", "context7", "postgres"],
    "queries_before_proposing": 3,
    "patterns_reused": 2
  }
}
```

---

## 🚨 Mandatory Workflows by Project Type

### csharp-wpf / csharp-winforms
- **Roslyn Validation**: BEFORE and AFTER every .cs edit
- **Context7**: Specific library IDs (/dotnet/wpf, /dotnet/winforms)
- **Audit Trail**: Log every validation in response
- **Compliance Target**: 100%

### python
- (Future: Python-specific workflows)

### infrastructure
- **Documentation**: CLAUDE.md ≤250 lines
- **Procedure Registry**: Query before adding new procedures
- **Session Logging**: Start and end every session

---

## 🎯 Guardian Responsibilities

### 1. Detect Non-Compliance
```sql
-- Find sessions with violations
SELECT
    session_start::date,
    project_name,
    session_metadata->'compliance'->'violations' as violations
FROM claude_family.session_history
WHERE jsonb_array_length(session_metadata->'compliance'->'violations') > 0
ORDER BY session_start DESC;
```

### 2. Monitor Improvement
```sql
-- Am I getting better?
SELECT
    DATE_TRUNC('week', session_start) as week,
    AVG((session_metadata->'compliance'->>'compliance_rate')::float) as avg_compliance
FROM claude_family.session_history
WHERE project_name = 'claude-pm'
GROUP BY week
ORDER BY week DESC;
```

### 3. Flag Concerning Patterns
- Same violation repeatedly
- Compliance rate declining over time
- Mandatory procedures never used
- MCPs installed but not invoked

### 4. Report to User
At session end, show:
- Compliance rate for this session
- Comparison to previous sessions
- Any violations and their reasons
- Improvement suggestions

---

## 🔧 Integration Points

### session-start.md (Updated)
Add **Step 0: Project Type Detection**
```markdown
## Step 0: Compliance Guardian Activation

1. Detect project type from database
2. Load mandatory workflows for this type
3. Show previous compliance metrics
4. Verify required MCPs loaded
5. Display type-specific warnings
```

### session-end.md (Updated)
Add **Mandatory Workflow Compliance Audit**
```markdown
## Compliance Audit

For C# projects:
- [ ] Roslyn run before EVERY edit? (Count: X/Y)
- [ ] Context7 with specific library IDs?
- [ ] Validation results logged in responses?

Calculate: compliance_rate = validations / edits
Store in: session_metadata JSONB
Target: 100%
```

### CLAUDE.md (All C# Projects)
Add **Self-Monitoring Checkpoints**
```markdown
⚠️ BEFORE editing .cs: Verify Roslyn run
⚠️ AFTER editing .cs: Log validation
⚠️ AT SESSION END: Calculate compliance rate
```

---

## 📊 Success Metrics

**Good Guardian Performance:**
- Compliance rate trending toward 100%
- Violations decreasing over time
- User rarely catches mistakes
- Procedures followed without reminders

**Poor Guardian Performance:**
- Same violations repeatedly
- Compliance rate declining
- User frequently corrects behavior
- Procedures ignored

---

## 🚀 Quick Commands

```sql
-- My procedures for current project
SELECT * FROM claude_family.my_procedures
WHERE 'project-name' = ANY(applies_to_projects);

-- My recent compliance
SELECT
    session_start::date,
    session_metadata->'compliance'->>'compliance_rate'
FROM claude_family.session_history
WHERE project_name = 'current-project'
ORDER BY session_start DESC LIMIT 5;

-- All mandatory procedures
SELECT procedure_name, frequency, location
FROM claude_family.my_procedures
WHERE mandatory = true;
```

---

**Created**: 2025-10-29
**Status**: Active
**Applies To**: All Claude Family members
**Registered In**: `claude_family.procedure_registry` (procedure_name: 'Compliance Guardian Process')

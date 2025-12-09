# Claude Family Usage Workflows

**Document Type**: Operational Guide
**Version**: 1.0
**Created**: 2025-12-08
**Status**: Active
**Purpose**: Define WHO uses each capability, WHEN, and HOW - with enforcement

---

## The Problem

We have 50+ capabilities (commands, agents, hooks, jobs) but no clear:
- WHO should use them
- WHEN they should be used
- HOW to use them
- ENFORCEMENT that they ARE used

This document closes that gap.

---

## 1. Session Lifecycle (MANDATORY)

### WHO: All Claude instances (claude-code-unified, claude-mcw, claude-desktop)
### WHEN: Every session
### ENFORCEMENT: SessionStart/SessionEnd hooks

```
SESSION START                          SESSION END
─────────────                          ───────────
[Hook runs automatically]              [Hook prompts]
     ↓                                      ↓
Creates session record                 Reminder to run /session-end
     ↓                                      ↓
Loads previous state                   Saves todo list, focus, next steps
     ↓                                      ↓
Checks pending messages                Closes session in database
     ↓
Shows due jobs/reminders
```

### Enforcement Status
| Mechanism | Status | Gap |
|-----------|--------|-----|
| SessionStart hook | **ACTIVE** | None - auto-runs |
| Session auto-logging | **ACTIVE** | Fixed 2025-12-08 |
| SessionEnd reminder | **ACTIVE** | User can ignore |
| /session-end command | Available | Not enforced |

### Missing Enforcement
- [ ] Block session close without running /session-end
- [ ] Auto-save state if Claude disconnects unexpectedly

---

## 2. Code Changes (SHOULD ENFORCE)

### WHO: Any Claude making code changes
### WHEN: Before committing code
### ENFORCEMENT: PreCommit hook

```
WRITE CODE → PRE-COMMIT CHECK → COMMIT
                   ↓
         ┌─────────────────────┐
         │ Level 1 Tests:      │
         │ - Sensitive files   │
         │ - Schema validation │
         │ - Type checking     │
         └─────────────────────┘
                   ↓
            PASS? → Commit allowed
            FAIL? → Commit blocked
```

### Enforcement Status
| Project | PreCommit Hook | Testing |
|---------|----------------|---------|
| claude-family | **ACTIVE** | Level 1 |
| ATO-Tax-Agent | UNKNOWN | Need to verify |
| mission-control-web | UNKNOWN | Need to verify |
| nimbus-user-loader | UNKNOWN | Need to verify |

### Missing Enforcement
- [ ] Verify PreCommit deployed to all projects
- [ ] Add Level 2 tests before push
- [ ] Track test coverage metrics

---

## 3. Feature Development (WORKFLOW)

### WHO: Claude instances building features
### WHEN: When implementing new functionality
### ENFORCEMENT: Process router + standards injection

```
USER REQUEST
     ↓
[UserPromptSubmit hook]
     ↓
Process router detects task type
     ↓
┌─────────────────────────────────┐
│ Injects relevant standards:     │
│ - UI work → UI_COMPONENT_STANDARDS │
│ - API work → API_STANDARDS      │
│ - DB work → DATABASE_STANDARDS  │
│ - All code → DEVELOPMENT_STANDARDS │
└─────────────────────────────────┘
     ↓
Claude follows standards (advisory)
     ↓
PreCommit validates before commit
```

### Current Gap: No Testing Injection

Process router injects standards but NOT testing requirements.

**SHOULD ADD:**
```
If task involves code changes:
  → Inject SOP-006 testing requirements
  → Remind: "Run tests before committing"
  → After commit: "Consider spawning test-coordinator-sonnet"
```

---

## 4. Testing (SHOULD ENFORCE)

### WHO: Claude instances after code changes
### WHEN: Before commit (Level 1), Before push (Level 2), Before release (Level 3)
### ENFORCEMENT: Currently WEAK

```
LEVEL 1 (PreCommit)     LEVEL 2 (PrePush)      LEVEL 3 (Release)
──────────────────      ─────────────────      ─────────────────
Schema validation       Unit tests              E2E tests
Sensitive files         API smoke test          Cross-project check
Type checking           Integration tests       Data quality review
                                               Doc quality review

ENFORCEMENT:            ENFORCEMENT:            ENFORCEMENT:
PreCommit hook         NOT ENFORCED            NOT ENFORCED
```

### Who Uses Test Agents

| Agent | Trigger | Usage |
|-------|---------|-------|
| test-coordinator-sonnet | Manual spawn | Orchestrate full test suite |
| nextjs-tester-haiku | Manual spawn | E2E Next.js testing |
| debugger-haiku | Manual spawn | Analyze test failures |
| screenshot-tester-haiku | Manual spawn | Visual regression |

### Missing Enforcement
- [ ] Require Level 2 tests before push
- [ ] Auto-spawn test-coordinator after significant changes
- [ ] Block release without Level 3 pass

---

## 5. Quality Reviews (SCHEDULED)

### WHO: Automated (scheduled jobs) + Claude on-demand
### WHEN: Per schedule or when spawned
### ENFORCEMENT: Scheduler runs jobs, results stored

```
SCHEDULED JOBS                    REVIEW AGENTS
──────────────                    ─────────────
doc-staleness-review (weekly)     doc-reviewer-sonnet
data-quality-review (daily)       data-reviewer-sonnet
governance-compliance-check       reviewer-sonnet
Document Scanner (weekly)         security-sonnet
```

### Current State
- Jobs RUN but don't ENFORCE fixes
- Results stored but not ACTED on
- No escalation if issues found

### Missing Enforcement
- [ ] Send message to project when issues found
- [ ] Track remediation status
- [ ] Block releases if critical issues open

---

## 6. Communication (ACTIVE)

### WHO: All Claude instances
### WHEN: When needing to share info across projects
### ENFORCEMENT: Message system works, checking is on-demand

```
SENDER                          RECEIVER
──────                          ────────
/broadcast                      SessionStart hook checks
     ↓                              ↓
Message stored                  Shows pending count
     ↓                              ↓
                               /inbox-check to view
                                    ↓
                               Acknowledge messages
```

### Enforcement Status
- Messages are delivered (WORKING)
- SessionStart shows pending count (WORKING)
- No enforcement to ACT on messages (GAP)

---

## 7. Compliance Audits (NOT YET IMPLEMENTED)

### WHO: Automated scheduler → Project Claude instances
### WHEN: Weekly/monthly per schedule
### ENFORCEMENT: PLANNED but not built

### Proposed Flow
```
1. Scheduler marks project for audit
2. Message sent to project
3. Project Claude reads on SessionStart
4. /check-compliance runs automatically
5. Results stored in claude.compliance_audits
6. Dashboard shows status in MCW
```

---

## Enforcement Mechanisms Summary

| Mechanism | Type | Status |
|-----------|------|--------|
| SessionStart hook | Automatic | **ACTIVE** |
| SessionEnd hook | Prompt | **ACTIVE** |
| UserPromptSubmit hook | Automatic | **ACTIVE** |
| PreCommit hook | Blocking | **ACTIVE** (claude-family only) |
| PreToolUse validators | Blocking | **ACTIVE** |
| Scheduled jobs | Automatic | **ACTIVE** |
| Compliance audits | Automatic | NOT BUILT |
| Test enforcement | Manual | WEAK |
| Review enforcement | Manual | WEAK |

---

## Action Items to Close Gaps

### High Priority
1. **Verify PreCommit hook in all projects**
   - Check ATO-Tax-Agent, MCW, nimbus-user-loader
   - Deploy if missing

2. **Add testing to process_router.py**
   - Detect code change tasks
   - Inject testing requirements
   - Remind about test agents

3. **Create capability usage tracking**
   - Log when slash commands used
   - Log when agents spawned
   - Dashboard to show usage

### Medium Priority
4. **Implement compliance audit flow**
   - Scheduler triggers
   - Messages sent
   - Auto-run on session start
   - Store results

5. **Escalation for review findings**
   - Critical issues → Block
   - High issues → Message
   - Medium issues → Log

### Low Priority
6. **Auto-spawn test agents**
   - After significant changes, suggest/spawn test-coordinator
   - Make testing less manual

---

## Quick Reference: Who Uses What When

| Capability | Who | When | Enforcement |
|------------|-----|------|-------------|
| /session-start | All Claudes | Session begin | Hook auto-runs |
| /session-end | All Claudes | Session end | Hook prompts |
| PreCommit check | All Claudes | Before commit | Hook blocks |
| Standards injection | All Claudes | On prompt | Process router |
| Test agents | All Claudes | After code changes | Manual (GAP) |
| Review agents | Scheduler | Weekly | Scheduler runs |
| /broadcast | Any Claude | Cross-project comms | Available |
| /inbox-check | All Claudes | Session start | Hook shows count |
| Compliance audit | All Claudes | Per schedule | NOT BUILT |

---

**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-08 | Initial version - identified gaps |

---

**Location**: C:\Projects\claude-family\docs\USAGE_WORKFLOWS.md

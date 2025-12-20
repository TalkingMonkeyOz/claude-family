# Claude Family - System Architecture Diagrams

**Created**: 2025-12-16
**Purpose**: Visual documentation of how the Claude Family system works

---

## 1. System Overview

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          CLAUDE FAMILY ECOSYSTEM                               ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   ┌─────────────────────────────────────────────────────────────────────┐     ║
║   │                        USER INTERFACES                               │     ║
║   │                                                                      │     ║
║   │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │     ║
║   │   │   Claude     │   │   Claude     │   │   Mission    │           │     ║
║   │   │   Desktop    │   │   Code CLI   │   │   Control    │           │     ║
║   │   │   (GUI)      │   │   (Terminal) │   │   Web (MCW)  │           │     ║
║   │   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘           │     ║
║   │          │                  │                  │                    │     ║
║   └──────────┼──────────────────┼──────────────────┼────────────────────┘     ║
║              │                  │                  │                          ║
║              └────────────┬─────┴──────────────────┘                          ║
║                           │                                                    ║
║                           ▼                                                    ║
║   ┌─────────────────────────────────────────────────────────────────────┐     ║
║   │                     ORCHESTRATION LAYER                              │     ║
║   │                                                                      │     ║
║   │   ┌───────────────────────────────────────────────────────────┐     │     ║
║   │   │                    Process Router                          │     │     ║
║   │   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │     │     ║
║   │   │   │UserPrompt│  │Workflow │  │Standards│  │ Context │     │     │     ║
║   │   │   │ Submit   │  │ Trigger │  │Injection│  │ Loader  │     │     │     ║
║   │   │   │  Hook    │  │  Engine │  │         │  │         │     │     │     ║
║   │   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘     │     │     ║
║   │   └───────────────────────────────────────────────────────────┘     │     ║
║   │                                                                      │     ║
║   │   ┌───────────────────────────────────────────────────────────┐     │     ║
║   │   │                  Agent Orchestrator                        │     │     ║
║   │   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐     │     │     ║
║   │   │   │ coder-  │  │reviewer-│  │architect│  │researcher│     │     │     ║
║   │   │   │ haiku   │  │ sonnet  │  │  opus   │  │  opus   │     │     │     ║
║   │   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘     │     │     ║
║   │   └───────────────────────────────────────────────────────────┘     │     ║
║   │                                                                      │     ║
║   └─────────────────────────────────────────────────────────────────────┘     ║
║                                                                                ║
║   ┌─────────────────────────────────────────────────────────────────────┐     ║
║   │                        DATA LAYER                                    │     ║
║   │                                                                      │     ║
║   │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐           │     ║
║   │   │  PostgreSQL  │   │     MCP      │   │   File       │           │     ║
║   │   │  claude.*    │   │   Servers    │   │   System     │           │     ║
║   │   │              │   │              │   │              │           │     ║
║   │   │ - sessions   │   │ - postgres   │   │ - CLAUDE.md  │           │     ║
║   │   │ - knowledge  │   │ - memory     │   │ - TODO.md    │           │     ║
║   │   │ - feedback   │   │ - filesystem │   │ - .mcp.json  │           │     ║
║   │   │ - projects   │   │ - orchestr.  │   │ - commands/  │           │     ║
║   │   │ - documents  │   │ - python     │   │              │           │     ║
║   │   └──────────────┘   └──────────────┘   └──────────────┘           │     ║
║   │                                                                      │     ║
║   └─────────────────────────────────────────────────────────────────────┘     ║
║                                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SESSION LIFECYCLE                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────┐                                                               │
│   │  START  │                                                               │
│   └────┬────┘                                                               │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────┐                               │
│   │         /session-start                   │                               │
│   │                                          │                               │
│   │   1. Log session to PostgreSQL           │                               │
│   │   2. Load TODO_NEXT_SESSION.md           │                               │
│   │   3. Load CLAUDE.md (global + project)   │                               │
│   │   4. Check inbox for messages            │                               │
│   │   5. Display context summary             │                               │
│   │                                          │                               │
│   └────────────────────┬────────────────────┘                               │
│                        │                                                     │
│                        ▼                                                     │
│   ┌─────────────────────────────────────────┐                               │
│   │              WORK LOOP                   │                               │
│   │                                          │                               │
│   │   ┌──────────────────────────────────┐  │                               │
│   │   │                                   │  │                               │
│   │   │   Gather Context ───────────────────────> Process Router            │
│   │   │        │                          │  │         │                     │
│   │   │        ▼                          │  │         ▼                     │
│   │   │   Take Action ──────────────────────────> Standards Injection       │
│   │   │        │                          │  │         │                     │
│   │   │        ▼                          │  │         ▼                     │
│   │   │   Verify Work ──────────────────────────> TodoWrite Updates         │
│   │   │        │                          │  │                               │
│   │   │        ▼                          │  │                               │
│   │   │   [Repeat]                        │  │                               │
│   │   │                                   │  │                               │
│   │   └──────────────────────────────────┘  │                               │
│   │                                          │                               │
│   └────────────────────┬────────────────────┘                               │
│                        │                                                     │
│                        ▼                                                     │
│   ┌─────────────────────────────────────────┐                               │
│   │         /session-end                     │                               │
│   │                                          │                               │
│   │   1. Summarize work completed            │                               │
│   │   2. Record next steps                   │                               │
│   │   3. Update TODO_NEXT_SESSION.md         │                               │
│   │   4. Close session in PostgreSQL         │                               │
│   │   5. Optional: broadcast status          │                               │
│   │                                          │                               │
│   └────────────────────┬────────────────────┘                               │
│                        │                                                     │
│                        ▼                                                     │
│                   ┌─────────┐                                               │
│                   │   END   │                                               │
│                   └─────────┘                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Process Router Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROCESS ROUTER FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   USER PROMPT                                                                │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────────────────────────────────┐                               │
│   │         UserPromptSubmit Hook            │                               │
│   └────────────────────┬────────────────────┘                               │
│                        │                                                     │
│                        ▼                                                     │
│   ┌─────────────────────────────────────────┐                               │
│   │         Classify Prompt                  │                               │
│   │                                          │                               │
│   │   Keywords → Workflow Mapping            │                               │
│   │   - "bug", "fix" → Bug Fix Workflow      │                               │
│   │   - "feature", "add" → Feature Dev       │                               │
│   │   - "review", "PR" → Code Review         │                               │
│   │   - "test" → Testing Workflow            │                               │
│   │   - "deploy" → Deployment                │                               │
│   │                                          │                               │
│   └────────────────────┬────────────────────┘                               │
│                        │                                                     │
│           ┌────────────┼────────────┐                                       │
│           │            │            │                                       │
│           ▼            ▼            ▼                                       │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐                                │
│   │    UI     │ │   API     │ │ DATABASE  │                                │
│   │ Standards │ │ Standards │ │ Standards │                                │
│   └─────┬─────┘ └─────┬─────┘ └─────┬─────┘                                │
│         │             │             │                                       │
│         └──────────┬──┴─────────────┘                                       │
│                    │                                                         │
│                    ▼                                                         │
│   ┌─────────────────────────────────────────┐                               │
│   │         Inject Workflow Steps            │                               │
│   │                                          │                               │
│   │   <process-guidance>                     │                               │
│   │     [BLOCKING] Step 1: ...               │                               │
│   │     [BLOCKING] Step 2: ...               │                               │
│   │     Step 3: ...                          │                               │
│   │   </process-guidance>                    │                               │
│   │                                          │                               │
│   │   <standards-guidance>                   │                               │
│   │     Relevant standards checklist...      │                               │
│   │   </standards-guidance>                  │                               │
│   │                                          │                               │
│   └────────────────────┬────────────────────┘                               │
│                        │                                                     │
│                        ▼                                                     │
│              ENHANCED PROMPT TO CLAUDE                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Agent Orchestration Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATION PATTERN                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                        ┌─────────────────────┐                              │
│                        │    Lead Agent       │                              │
│                        │   (Claude Opus)     │                              │
│                        │                     │                              │
│                        │  - Analyze task     │                              │
│                        │  - Develop strategy │                              │
│                        │  - Delegate work    │                              │
│                        │  - Synthesize       │                              │
│                        └──────────┬──────────┘                              │
│                                   │                                          │
│                    ┌──────────────┼──────────────┐                          │
│                    │              │              │                          │
│                    ▼              ▼              ▼                          │
│   ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐     │
│   │   Subagent A       │ │   Subagent B       │ │   Subagent C       │     │
│   │   (coder-haiku)    │ │   (reviewer-sonnet)│ │   (web-tester)     │     │
│   │                    │ │                    │ │                    │     │
│   │   Task: Implement  │ │   Task: Review     │ │   Task: Test       │     │
│   │   feature code     │ │   code quality     │ │   E2E scenarios    │     │
│   │                    │ │                    │ │                    │     │
│   └────────┬───────────┘ └────────┬───────────┘ └────────┬───────────┘     │
│            │                      │                      │                  │
│            │   ┌──────────────────┼──────────────────────┘                  │
│            │   │                  │                                          │
│            ▼   ▼                  ▼                                          │
│   ┌─────────────────────────────────────────┐                               │
│   │         Message Bus / Results           │                               │
│   │                                          │                               │
│   │   - Subagent reports to lead agent      │                               │
│   │   - Results aggregated                  │                               │
│   │   - Lead synthesizes final output       │                               │
│   │                                          │                               │
│   └─────────────────────────────────────────┘                               │
│                                                                              │
│   KEY PRINCIPLES:                                                            │
│   ━━━━━━━━━━━━━━━                                                           │
│   • One agent, one job                                                       │
│   • Orchestrator maintains global plan                                       │
│   • Subagents work in parallel when possible                                │
│   • Clear task boundaries for each agent                                    │
│   • Results collected via message bus                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Data Flow Between Sessions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DATA FLOW BETWEEN SESSIONS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   SESSION N                           SESSION N+1                            │
│   ━━━━━━━━━                           ━━━━━━━━━━━                            │
│                                                                              │
│   ┌───────────────┐                   ┌───────────────┐                     │
│   │ Work Done     │                   │ Load Context  │                     │
│   │               │                   │               │                     │
│   │ - Code changes│                   │ ◄──────────────────┐                │
│   │ - DB updates  │                   │               │    │                │
│   │ - Decisions   │                   └───────┬───────┘    │                │
│   └───────┬───────┘                           │            │                │
│           │                                   │            │                │
│           ▼                                   │            │                │
│   ┌───────────────┐                           │            │                │
│   │ /session-end  │                           │            │                │
│   │               │                           │            │                │
│   │ Summarize:    │                           │            │                │
│   │ - Completed   │                           │            │                │
│   │ - Decisions   │                           │            │                │
│   │ - Next steps  │                           │            │                │
│   └───────┬───────┘                           │            │                │
│           │                                   │            │                │
│           ▼                                   │            │                │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                    PERSISTENCE LAYER                             │      │
│   │                                                                  │      │
│   │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐│      │
│   │   │   PostgreSQL    │  │TODO_NEXT_SESSION│  │    CLAUDE.md    ││      │
│   │   │                 │  │      .md        │  │                 ││      │
│   │   │ sessions:       │  │                 │  │ Project rules   ││      │
│   │   │ - summary       │  │ - Last updated  │  │ Conventions     ││      │
│   │   │ - next_steps    │  │ - Completed     │  │ Standards       ││      │
│   │   │                 │  │ - Next steps    │  │                 ││      │
│   │   │ knowledge:      │  │ - Notes         │  │                 ││      │
│   │   │ - lessons       │  │                 │  │                 ││      │
│   │   │ - patterns      │──┼─────────────────┼──┼─────────────────┼┼──────┘
│   │   │                 │  │                 │  │                 ││
│   │   └─────────────────┘  └─────────────────┘  └─────────────────┘│
│   │                                                                  │
│   └──────────────────────────────────────────────────────────────────┘
│                                                                              │
│   CONTEXT CARRYOVER:                                                         │
│   ━━━━━━━━━━━━━━━━━                                                         │
│   1. Session summary → Next session context                                  │
│   2. Knowledge entries → Cross-session learning                              │
│   3. TODO file → Immediate next steps                                        │
│   4. CLAUDE.md → Consistent project rules                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Feature Development Workflow (BPMN-style)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  FEATURE DEVELOPMENT WORKFLOW (BPMN)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   (○)─────► ┌──────────────┐                                                │
│   Start     │ 1. EXPLORE   │                                                │
│             │              │                                                │
│             │ • Read code  │                                                │
│             │ • Find gaps  │                                                │
│             │ • Questions  │                                                │
│             └──────┬───────┘                                                │
│                    │                                                         │
│                    ▼                                                         │
│             ┌──────────────┐         ┌─────────────────┐                    │
│             │ 2. RESOLVE   │◄────────┤ More questions? │                    │
│             │              │   Yes   │                 │                    │
│             │ • Real data  │         └────────┬────────┘                    │
│             │ • Validate   │                  │ No                          │
│             │ • Iterate    ├──────────────────┘                             │
│             └──────┬───────┘                                                │
│                    │                                                         │
│                    ▼                                                         │
│             ┌──────────────┐                                                │
│             │ 3. VALIDATE  │                                                │
│             │              │                                                │
│             │ • Data flow  │                                                │
│             │ • API/DB     │                                                │
│             │ • Patterns   │                                                │
│             └──────┬───────┘                                                │
│                    │                                                         │
│                    ▼                                                         │
│             ┌──────────────┐                                                │
│             │ 4. DESIGN    │                                                │
│             │              │                                                │
│             │ • UI spec    │                                                │
│             │ • Data mgmt  │                                                │
│             │ • Logging    │                                                │
│             └──────┬───────┘                                                │
│                    │                                                         │
│                    ▼                                                         │
│             ┌──────────────┐    ┌─────────────┐                             │
│             │ 5. TDD IMPL  │◄───┤ Tests pass? │                             │
│             │              │ No │             │                             │
│             │ • Write test │    └──────┬──────┘                             │
│             │ • Fail test  │           │ Yes                                │
│             │ • Implement  ├───────────┘                                    │
│             │ • Refactor   │                                                │
│             └──────┬───────┘                                                │
│                    │                                                         │
│                    ▼                                                         │
│             ┌──────────────┐    ┌─────────────┐                             │
│             │ 6. REVIEW    │◄───┤ Issues?     │                             │
│             │              │ Yes│             │                             │
│             │ • Walkthrough│    └──────┬──────┘                             │
│             │ • Code review│           │ No                                 │
│             │ • Checklist  ├───────────┘                                    │
│             └──────┬───────┘                                                │
│                    │                                                         │
│                    ▼                                                         │
│             ┌──────────────┐                                                │
│             │ 7. COMMIT    │─────────► (◉)                                  │
│             │              │           End                                  │
│             │ • Full tests │                                                │
│             │ • Create PR  │                                                │
│             │ • Merge      │                                                │
│             └──────────────┘                                                │
│                                                                              │
│   GATEWAY LEGEND:                                                            │
│   ◇ = Exclusive (XOR) gateway - one path                                    │
│   ○ = Start event                                                           │
│   ◉ = End event                                                             │
│   □ = Task/Activity                                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Agent Selection Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AGENT SELECTION DECISION TREE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         ┌─────────────────┐                                 │
│                         │   What's the    │                                 │
│                         │     task?       │                                 │
│                         └────────┬────────┘                                 │
│                                  │                                          │
│         ┌────────────────────────┼────────────────────────┐                │
│         │                        │                        │                │
│         ▼                        ▼                        ▼                │
│   ┌───────────┐           ┌───────────┐           ┌───────────┐           │
│   │   Code    │           │  Review   │           │ Research  │           │
│   │  Writing  │           │  /Analyze │           │ /Planning │           │
│   └─────┬─────┘           └─────┬─────┘           └─────┬─────┘           │
│         │                       │                       │                  │
│         ▼                       ▼                       ▼                  │
│   ┌───────────┐           ┌───────────┐           ┌───────────┐           │
│   │  Python   │           │   Code    │           │  Complex  │           │
│   │ specific? │           │  Quality? │           │ planning? │           │
│   └─────┬─────┘           └─────┬─────┘           └─────┬─────┘           │
│     Yes │ No                Yes │ No                Yes │ No              │
│         │                       │                       │                  │
│    ▼    ▼                  ▼    ▼                  ▼    ▼                  │
│  ┌────┐ ┌────┐          ┌────┐ ┌────┐          ┌────┐ ┌────┐              │
│  │py- │ │cod-│          │rev-│ │web-│          │arch│ │res-│              │
│  │cdr │ │er- │          │iew-│ │test│          │-   │ │ear-│              │
│  │haik│ │haik│          │son │ │haik│          │opus│ │opus│              │
│  └────┘ └────┘          └────┘ └────┘          └────┘ └────┘              │
│                                                                              │
│   AGENT SUMMARY:                                                            │
│   ━━━━━━━━━━━━━━                                                           │
│   coder-haiku:      General coding, TypeScript, JavaScript                  │
│   python-coder:     Python-specific tasks                                   │
│   reviewer-sonnet:  Code review, quality analysis                           │
│   web-tester-haiku: E2E testing, Playwright                                 │
│   architect-opus:   System design, complex planning                         │
│   researcher-opus:  Deep research, investigation                            │
│                                                                              │
│   COST CONSIDERATION:                                                        │
│   ━━━━━━━━━━━━━━━━━━                                                        │
│   Haiku  = Low cost, fast, good for routine tasks                           │
│   Sonnet = Medium cost, balanced, good for review                           │
│   Opus   = High cost, thorough, use for complex/critical                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Database Schema Overview (Core Tables)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DATABASE SCHEMA (CORE TABLES)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────┐         ┌─────────────────┐                           │
│   │   projects      │◄────────┤   sessions      │                           │
│   │─────────────────│         │─────────────────│                           │
│   │ project_id (PK) │         │ session_id (PK) │                           │
│   │ project_name    │         │ identity_id(FK) │                           │
│   │ status          │         │ project_name    │                           │
│   │ created_at      │         │ session_start   │                           │
│   └────────┬────────┘         │ session_end     │                           │
│            │                  │ session_summary │                           │
│            │                  └─────────────────┘                           │
│            │                           │                                     │
│            │                           │                                     │
│            ▼                           ▼                                     │
│   ┌─────────────────┐         ┌─────────────────┐                           │
│   │   features      │         │   identities    │                           │
│   │─────────────────│         │─────────────────│                           │
│   │ feature_id (PK) │         │ identity_id(PK) │                           │
│   │ project_id (FK) │         │ identity_name   │                           │
│   │ title           │         │ platform        │                           │
│   │ status          │         │ capabilities    │                           │
│   │ priority        │         │ status          │                           │
│   └────────┬────────┘         └─────────────────┘                           │
│            │                                                                 │
│            │                                                                 │
│            ▼                                                                 │
│   ┌─────────────────┐         ┌─────────────────┐                           │
│   │  build_tasks    │         │   feedback      │                           │
│   │─────────────────│         │─────────────────│                           │
│   │ task_id (PK)    │         │ feedback_id(PK) │                           │
│   │ feature_id (FK) │         │ project_id (FK) │                           │
│   │ title           │         │ feedback_type   │                           │
│   │ status          │         │ description     │                           │
│   │ priority        │         │ status          │                           │
│   └─────────────────┘         └─────────────────┘                           │
│                                                                              │
│                                                                              │
│   ┌─────────────────┐         ┌─────────────────┐                           │
│   │   knowledge     │         │   documents     │                           │
│   │─────────────────│         │─────────────────│                           │
│   │ knowledge_id    │         │ document_id     │                           │
│   │ knowledge_type  │         │ file_path       │                           │
│   │ title           │         │ doc_type        │                           │
│   │ description     │         │ status          │                           │
│   │ confidence_level│         │ updated_at      │                           │
│   │ times_applied   │         │                 │                           │
│   └─────────────────┘         └─────────────────┘                           │
│                                                                              │
│   ENFORCEMENT:                                                               │
│   ━━━━━━━━━━━━                                                              │
│   column_registry → CHECK constraints on status, priority                    │
│   Foreign keys → Referential integrity                                       │
│   Triggers → updated_at auto-update                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**Version**: 1.0
**Created**: 2025-12-16
**Location**: C:\Projects\claude-family\docs\ARCHITECTURE_VISUAL.md

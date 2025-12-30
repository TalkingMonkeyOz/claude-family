# Claude Agent Orchestrator - Architecture Overview

**Version:** 2.0 (split from main document)
**Split Date:** 2025-12-26
**Status:** Production-Ready Prototype
**Author:** Claude Technical Analyst

---

## Executive Summary

The Claude Agent Orchestrator is a process-level isolation system that spawns specialized Claude Code instances with minimal MCP configurations. It enables parallel execution of coding tasks with 3-5x speed improvements, 66% context reduction, and 67% cost savings compared to monolithic sessions.

**Key Capabilities:**
- Spawn isolated Claude Code processes with dedicated configurations
- 6 specialized agent types (coder, debugger, tester, reviewer, security, analyst)
- True parallelization (tested with 3+ concurrent agents)
- Workspace jailing and tool restrictions for security
- Model selection (Haiku for speed/cost, Sonnet for quality)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Design Principles](#design-principles)
3. [Document Structure](#document-structure)
4. [Quick Start](#quick-start)

---

## Architecture Overview

### High-Level Design

```
┌────────────────────────────────────────────────────────────────┐
│ Main Claude Session (Orchestrator)                             │
│ • Full MCPs: postgres, memory, filesystem, sequential-thinking │
│ • Coordinates work, spawns agents, aggregates results          │
│ • Identity: claude-code-unified                                 │
└──────────────────┬─────────────────────────────────────────────┘
                   │
                   │ spawn_agent(type, task, workspace)
                   │
    ┌──────────────┼──────────────┬──────────────────────┐
    │              │              │                      │
    ▼              ▼              ▼                      ▼
┌─────────┐  ┌──────────┐  ┌──────────┐         ┌──────────┐
│ Coder   │  │ Reviewer │  │ Security │   ...   │ Analyst  │
│ Haiku   │  │ Sonnet   │  │ Sonnet   │         │ Sonnet   │
└─────────┘  └──────────┘  └──────────┘         └──────────┘
   │              │              │                      │
   │ MCPs: None   │ tree-sitter  │ tree-sitter         │ seq-thinking
   │ RW: /src/    │ RO: /        │ + seq-thinking      │ + memory
   │              │              │ RO: /               │ RW: /docs/
   │              │              │                      │
   └──────────────┴──────────────┴──────────────────────┘
                   │
                   ▼
            stdout/stderr capture
```

### Design Principles

1. **Process Isolation**: Each agent runs in a separate OS process with independent memory space
2. **Minimal Context**: Agents load only required MCPs (0-2 servers vs 5+ in main session)
3. **Capability-Based Security**: Explicit allow/deny lists for tools and filesystem access
4. **Model Optimization**: Fast Haiku for routine tasks, powerful Sonnet for complex analysis
5. **Stateless Execution**: Agents complete tasks and terminate (no persistent state)
6. **Fail-Safe**: Agent failures don't crash the orchestrator

---

## Document Structure

This architecture document has been split into 4 focused files for easier navigation:

### 1. **ORCHESTRATOR_ARCH_Overview.md** (this file)
   - Executive summary and high-level design
   - Architecture diagram and design principles
   - Links to detailed documentation

### 2. **ORCHESTRATOR_ARCH_Core_Components.md**
   - Core Components section
   - Agent Types definitions (6 types)
   - Implementation details

### 3. **ORCHESTRATOR_ARCH_Isolation_Communication.md**
   - Isolation Mechanisms (7 types)
   - Communication Flow sequences
   - Expanding Agent Types guide

### 4. **ORCHESTRATOR_ARCH_Operations.md**
   - Performance Metrics
   - Security Model
   - Troubleshooting guide
   - Future Enhancements (5 phases)

---

## Quick Start

### Reading Path by Role

**🔧 I want to implement a new agent:**
1. Start here → Design Principles
2. Read → `ORCHESTRATOR_ARCH_Core_Components.md`
3. Follow → Expanding Agent Types guide in `ORCHESTRATOR_ARCH_Isolation_Communication.md`

**🛡️ I need to understand security:**
1. Read → Design Principles (this file)
2. Go to → `ORCHESTRATOR_ARCH_Isolation_Communication.md` (Isolation Mechanisms)
3. Review → `ORCHESTRATOR_ARCH_Operations.md` (Security Model & Troubleshooting)

**📊 I want performance data:**
1. Check → `ORCHESTRATOR_ARCH_Operations.md` (Performance Metrics section)
2. See → Cost Analysis and Scalability Metrics

**🐛 Something is broken:**
1. Go to → `ORCHESTRATOR_ARCH_Operations.md` (Troubleshooting section)

---

## Key Metrics at a Glance

| Metric | Value |
|--------|-------|
| Context Reduction | 66-100% per agent |
| Cost Savings | 67% average |
| Speed Improvement | 3-5x with 3-5 parallel agents |
| Concurrent Agents | 3-5 optimal, tested up to 3+ |
| Agent Types | 6 (coder, debugger, tester, reviewer, security, analyst) |
| Security Model | Workspace jailing + tool restrictions + read-only mode |

---

## Files Referenced

- **Implementation:** `mcp-servers/orchestrator/orchestrator_prototype.py`
- **Specifications:** `mcp-servers/orchestrator/agent_specs.json`
- **MCP Configs:** `mcp-servers/orchestrator/configs/*.mcp.json`
- **Test Results:** `docs/SUB_AGENT_TEST_RESULTS.md`

---

## See Also

- [[ORCHESTRATOR_ARCH_Core_Components]] - Core components and agent types
- [[ORCHESTRATOR_ARCH_Isolation_Communication]] - Isolation and communication details
- [[ORCHESTRATOR_ARCH_Operations]] - Performance, security, troubleshooting, and future work

---

**Version**: 2.0
**Split**: 2025-12-26
**Status**: Production-Ready Prototype
**Location**: docs/ORCHESTRATOR_ARCH_Overview.md

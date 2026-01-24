# Dynamic Skill Loading System Design

## Overview

Two-tier system for dynamic skill loading based on task context.

**Problem**: 26 skill_content entries (~297KB) silently injected, heavy tokens, no user control.

**Solution**: Lightweight suggestions → On-demand skill loading via Skill tool.

## Architecture

```
TIER 1: Suggestion (~50 tokens)
  Hook → Keyword Match → "RECOMMENDED: Load /architect skill"

TIER 2: Skill Files (on-demand)
  Claude decides → Skill tool → .claude/skills/{name}.md
```

## Key Documents

- [[Dynamic Skill System - BPMN Diagram]] - Full flow diagram
- [[Dynamic Skill System - Transformation Guide]] - How to convert awesome-copilot
- [[Dynamic Skill System - Implementation Plan]] - Phase-by-phase tasks

## Quick Reference

| Current | Proposed |
|---------|----------|
| Silent injection | Explicit suggestion |
| Full content (~25KB) | Metadata only (~50 tokens) |
| No user control | Claude/user decides |
| VS Code format | Claude Code native |

## Status

- [x] Audit complete (26 entries, 25 awesome-copilot)
- [x] Architecture designed
- [x] BPMN diagram created
- [x] Phase 1: Transform content (6 skills done)
- [x] Phase 2: Update hooks (RAG hook queries skill_content)
- [ ] Phase 3: Update CLAUDE.md

### Transformed Skills

| Original | New Location |
|----------|--------------|
| Senior Cloud Architect | `.claude/skills/architect.md` |
| debug | `.claude/skills/debug.md` |
| code-review-generic | `.claude/skills/code-review.md` |
| Implementation Plan | `.claude/skills/planner/skill.md` |
| Expert React | `.claude/skills/react-expert/skill.md` |
| sql-optimization | `.claude/skills/sql-optimization/skill.md` |

---

**Version**: 1.1
**Created**: 2026-01-24
**Updated**: 2026-01-24
**Location**: docs/DYNAMIC_SKILL_SYSTEM_DESIGN.md

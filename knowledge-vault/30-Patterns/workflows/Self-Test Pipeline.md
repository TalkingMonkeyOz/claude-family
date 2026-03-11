---
projects:
- claude-family
- claude-manager-mui
tags:
- testing
- playwright
- automation
- mcp
synced: false
---

# Self-Test Pipeline Pattern

Automated web application testing using Playwright MCP. Claude navigates, evaluates, and files bugs autonomously.

## Architecture

```
/self-test skill
    → Start dev server (if needed)
    → Playwright MCP (headless Chromium)
        → Navigate routes (URL or SPA click)
        → Capture accessibility snapshots
        → Read console logs
    → Evaluation engine
        → Check against criteria (a11y, layout, errors, navigation)
        → Generate findings with severity
    → Feedback integration
        → Auto-file critical/warning as feedback items
        → Deduplicate against existing items
    → JSON report saved to ~/.claude/self-test-reports/
```

## Components

| File | Purpose |
|------|---------|
| `scripts/self_test/runner.py` | Main orchestrator - MCP client, page navigation, report generation |
| `scripts/self_test/evaluation_schema.py` | Data models (Finding, PageResult, TestReport) + evaluation rules |
| `scripts/self_test/feedback_integration.py` | Auto-file findings as feedback items with deduplication |
| `.claude/commands/self-test.md` | Skill definition for `/self-test` command |
| `<project>/self-test/routes.json` | Per-project route manifest |

## Setup for a New Project

### 1. Create Route Manifest

Create `<project-root>/self-test/routes.json`:

```json
{
  "base_url": "http://localhost:3000",
  "project": "my-project",
  "routes": [
    {"path": "/", "name": "Home", "type": "url", "expected": ["heading"]},
    {"path": "/settings", "name": "Settings", "type": "click", "click_text": "Settings"}
  ]
}
```

### 2. Route Types

- **`url`**: Direct URL navigation. Use for initial page load or multi-page apps with URL routing.
- **`click`**: SPA click navigation. Finds element by `click_text` in accessibility snapshot and clicks it. Use for SPAs without URL routing.

### 3. Run

```bash
# From claude-family project root
python -m scripts.self_test.runner \
  --project my-project \
  --port 3000 \
  --manifest path/to/routes.json

# Or use the skill
/self-test my-project
```

## Evaluation Criteria

| Category | Checks | Severity |
|----------|--------|----------|
| Navigation | Route reachable, page not empty | Critical/Warning |
| Layout | Has headings, structured content | Info |
| Accessibility | Links have text, buttons have labels, images have alt | Warning |
| Console | JS errors, failed network requests | Critical/Warning |
| Functionality | Expected elements present (from manifest) | Warning |

## Feedback Auto-Filing

Findings with severity `critical` or `warning` are auto-filed:
- **Title**: `[self-test] <finding title> (<route>)`
- **Type**: Mapped from category (console→bug, layout→design, a11y→improvement)
- **Priority**: critical→high, warning→medium
- **Dedup**: Checks existing feedback by title substring match

## Limitations

- **No visual regression testing**: Uses accessibility snapshots, not screenshots for comparison
- **No complex interaction testing**: Can click but doesn't handle multi-step workflows (forms, drag-drop sequences)
- **Tauri apps**: Running outside Tauri shell produces `invoke` errors (expected, not real bugs)
- **Auth-gated pages**: Can't test pages behind login (would need pre-seeded session)
- **Timing-sensitive**: SPA rendering uses fixed 1.5s wait; fast/slow machines may need adjustment

## Performance

Tested against claude-manager-mui (5 routes): **17 seconds total** including MCP startup, navigation, evaluation, and report generation.

## MCP Configuration

Playwright MCP is configured in database (`workspaces.startup_config.mcp_configs`) and regenerated to `.mcp.json`:

```json
{
  "playwright": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@playwright/mcp@latest", "--headless"]
  }
}
```

Key flags: `--headless` (default), `--headed` (for debugging), `--viewport-size 1280x720`.

## Related

- [[Claude Hooks]] - Hook system that powers enforcement
- Feature F108 - Browser MCP Self-Testing Pipeline
- FB100 - Browser MCP Self-Testing (original idea)
- FB101 - Self-Diagnosis Skill (future extension)

---
**Version**: 1.0
**Created**: 2026-02-17
**Updated**: 2026-02-17
**Location**: knowledge-vault/30-Patterns/Self-Test Pipeline.md

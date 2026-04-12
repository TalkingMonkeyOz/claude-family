---
name: self-test
description: "Run automated app testing via Playwright — evaluates navigation, accessibility, console errors, and functionality"
user-invocable: true
disable-model-invocation: true
---

# Self-Test: Automated App Testing

Run the self-test pipeline against a web application.

**Usage**: `/self-test [project-name]` (defaults to current project)

---

## Step 1: Determine Target Project

If argument provided, use it. Otherwise, detect from current working directory.

Look up: dev server port (check `vite.config.ts`, `package.json`, or DB) and route manifest path (`<project-path>/self-test/routes.json`).

Common ports: claude-manager-mui: 1420 (Tauri/Vite), other Vite apps: 5173

## Step 2: Check Dev Server

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:<port>
```

If not running, start it and wait up to 15 seconds.

## Step 3: Run Self-Test

```bash
cd C:/Projects/claude-family && python -m scripts.self_test.runner \
  --project <project-name> \
  --port <port> \
  --manifest <project-path>/self-test/routes.json \
  --no-wait
```

Options: `--headed` (show browser), `--output <path>` (custom report path)

## Step 4: Display Results

Show: total routes tested, critical/warning/info finding counts, list each critical finding.

## Step 5: Offer to File Feedback

If findings exist, ask user whether to create feedback items. Use `work_create(type="feedback",` for each critical/warning finding.

## Route Manifest Format

Projects define testable routes in `self-test/routes.json`:
- `type: "url"` - Direct URL navigation
- `type: "click"` - SPA navigation by clicking element
- `expected` - Elements that should appear in accessibility snapshot

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/self-test/SKILL.md

**SELF-TEST - Automated App Testing via Playwright MCP**

Run the self-test pipeline against a web application to evaluate navigation, accessibility, console errors, and functionality.

**Usage**: `/self-test [project-name]` or `/self-test` (defaults to current project)

---

## Execute These Steps

### Step 1: Determine Target Project

If argument provided, use it as project name. Otherwise, detect from current working directory.

Look up project config to find:
- Dev server port (check `vite.config.ts`, `package.json`, or DB)
- Route manifest path: `<project-path>/self-test/routes.json`

Common ports:
- claude-manager-mui: 1420 (Tauri/Vite)
- Other Vite apps: 5173 (default)

### Step 2: Check Dev Server

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:<port>
```

If not running, start it:
```bash
cd <project-path> && npm run dev &
```

Wait up to 15 seconds for server to respond.

### Step 3: Run Self-Test

```bash
cd C:/Projects/claude-family && python -m scripts.self_test.runner \
  --project <project-name> \
  --port <port> \
  --manifest <project-path>/self-test/routes.json \
  --no-wait
```

Options:
- `--headed`: Show browser window (useful for debugging)
- `--output <path>`: Custom report output path

### Step 4: Display Results

Show the report summary:
- Total routes tested vs total defined
- Critical/warning/info finding counts
- List each critical finding with route and description

### Step 5: Offer to File Feedback

If critical or warning findings exist, ask user:
> "Found N critical and M warning findings. Create feedback items in DB?"

If user agrees, for each finding with severity critical or warning:

Use `mcp__project-tools__create_feedback` with:
- `project`: target project name
- `feedback_type`: finding's `feedback_type` (bug/design/improvement)
- `title`: finding's `title`
- `description`: Include route, description, console message (if any), and suggested fix
- `priority`: "high" for critical, "medium" for warning

### Step 6: Summary

Report:
- How many routes tested
- How many findings by severity
- How many feedback items created (if any)
- Link to full JSON report file

---

## Route Manifest Format

Projects define testable routes in `self-test/routes.json`:

```json
{
  "routes": [
    {"path": "/", "name": "Home", "type": "url", "expected": ["heading"]},
    {"path": "/settings", "name": "Settings", "type": "click", "click_text": "Settings"}
  ]
}
```

- `type: "url"` - Direct URL navigation
- `type: "click"` - SPA navigation by clicking element matching `click_text`
- `expected` - Elements that should appear in accessibility snapshot

---

**Version**: 1.0
**Created**: 2026-02-17
**Updated**: 2026-02-17
**Location**: .claude/commands/self-test.md

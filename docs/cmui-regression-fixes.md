# Claude Manager MUI — Regression Fixes

**Date**: 2026-03-21
**Project**: C:\Projects\claude-manager-mui

---

## Issue 1: Lowercase stub headings (App.tsx)

**File**: `src/App.tsx`

**Problem**: The monitoring placeholder block used `{monitoringSubView.replace('-', ' ')}` with `textTransform: 'capitalize'` to generate headings. This produced lowercase-looking labels ("sessions", "messages", "agents") and had no description text.

**Fix**: Added three explicit conditional blocks before the generic fallback, each rendering a proper heading and description paragraph:

- `monitoringSubView === 'sessions'` → heading "All Sessions" + description about viewing all Claude sessions
- `monitoringSubView === 'messages'` → heading "All Messages" + description about inter-Claude messages
- `monitoringSubView === 'agents'` → heading "Agents" + description about spawned agent activity

The generic fallback (for any future unhandled sub-views) remains intact after the three new conditionals.

---

## Issue 2: BPMN Processes bare error

**File**: `src/features/bpmn-processes/BpmnProcessesPage.tsx`

**Problem**: The early-return guard at the top of the component (line ~294) returned a bare `<Alert severity="error">` with no wrapper structure when `error && processes.length === 0`. This gave no heading or context when the backend was unavailable.

**Fix**: Wrapped the early-return in a `<Box sx={{ p: 3 }}>` containing:
- `<Typography variant="h5">BPMN Processes</Typography>`
- A description paragraph: "BPMN process models for the Claude Family ecosystem. Requires the bpmn-engine MCP server."
- The original `<Alert severity="error">` below

---

## Issue 3: App Logs bare error

**File**: `src/features/monitoring/AppLogViewer.tsx`

**Problem**: The error state returned a `<Box>` with no padding, rendering the heading and alert flush against the container edge. No description was present.

**Fix**: Added `sx={{ p: 3 }}` to the error-state Box and inserted a description paragraph between the heading and the alert:
- "Application and hook log entries from the Claude Family backend."

The heading "Application Logs" was already present and unchanged.

---

## Issue 4: Core Protocol hardcoded version chip

**File**: `src/features/claude-setup/ClaudeSetupPage.tsx`

**Problem**: The sidebar button for Core Protocol had a hardcoded `<Chip label="v6" size="small" color="primary" variant="outlined" />` next to the label. This was static and didn't reflect the actual active version loaded from the API.

**Fix**: Removed the hardcoded `<Chip label="v6" ...>` entirely. The actual version number is displayed inside `CoreProtocolPanel.tsx` as a dynamic chip (`v${activeVersion.version} (active)`) populated from API data, so no static version label is needed on the sidebar button.

---

**Version**: 1.0
**Created**: 2026-03-21
**Updated**: 2026-03-21
**Location**: docs/cmui-regression-fixes.md

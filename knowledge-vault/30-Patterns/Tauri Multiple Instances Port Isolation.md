---
title: Tauri Multiple Instances Port Isolation
created: 2026-01-02
updated: 2026-01-02
tags: [tauri, vite, port-conflict, multi-instance, windows]
category: patterns
status: active
---

# Tauri Multiple Instances Port Isolation

## Problem

Running multiple Tauri projects simultaneously on the same machine causes port conflicts because all projects default to port 1420. The dev server fails to start with "Port 1420 is already in use".

## Root Cause

Vite's default configuration uses a fixed port (1420) and `strictPort: true`, which means it fails instead of finding an available port when 1420 is occupied.

## Solution Pattern

Configure Vite to auto-increment ports when the default is unavailable:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    port: process.env.VITE_PORT ? parseInt(process.env.VITE_PORT) : 1420,
    strictPort: false, // Allow auto-increment for multiple instances
  },
  // ... rest of config
});
```

**Behavior**:
- First instance (any project): Uses port 1420
- Second instance (any project): Auto-increments to 1421
- Third instance: Uses 1422
- And so on...

## When to Apply

Apply this fix to **ALL Tauri + React projects** during project initialization or when encountering port conflicts.

### Projects Fixed

- ✅ nimbus-mui (2026-01-02)
- ✅ claude-manager-mui (needs verification)
- ⚠️ nimbus-import (check status)
- ⚠️ finance-mui (check status)

## Related Issues

### MCP Server Crashes

If Claude Code crashes when closing a dev server, it's likely the **MCP npx wrapper issue**, not Tauri port conflicts.

**Symptom**: Claude crashes when closing ANY dev server (not just Tauri)

**Cause**: MCP servers (memory, filesystem, sequential-thinking) run via `npx` and get killed when Windows terminates child processes

**Fix**: Use `cmd /c npx` wrapper in MCP configs. See [[MCP Windows npx Wrapper Pattern]]

## Validation

After applying the fix:

1. Start first Tauri project → Should use port 1420
2. Start second Tauri project (same or different) → Should auto-increment to 1421
3. Check terminal output: "Local: http://localhost:1421/"
4. Both projects run simultaneously without conflicts

## References

- [[Add MCP Server SOP]] - MCP configuration patterns
- Vite Documentation: https://vitejs.dev/config/server-options.html#server-port
- Related Commit: (Add commit hash when committing fix)

## Keywords

tauri, vite, port-conflict, multi-instance, windows, dev-server, 1420, strictPort

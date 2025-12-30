# MCP Server Research: Next.js + TypeScript + shadcn/ui Stack

**Date:** 2025-11-29  
**Requested By:** Inter-Claude message (MCP Server Requirements for Next.js + shadcn/ui Development)  
**Status:** Research Complete

---

## Executive Summary

Excellent news! There are **official and mature MCP servers** available for the Next.js + TypeScript + shadcn/ui stack. No need to build custom MCPs - we can leverage existing solutions.

### Priority Installation Order

| Priority | MCP Server | Package/Command | Status |
|----------|------------|-----------------|--------|
| 1 | **shadcn** (Official) | `npx shadcn@latest mcp` | Ready |
| 2 | **Next.js DevTools** | `npx next-devtools-mcp@latest` | Ready (Next.js 16+) |
| 3 | **ESLint** | `npx @eslint/mcp@latest` | Ready |
| 4 | **Tailwind CSS** | `npx tailwindcss-mcp-server` | Ready |

---

## 1. shadcn MCP Server (OFFICIAL)

**Source:** https://ui.shadcn.com/docs/mcp

### Quick Setup for Claude Code

```bash
# One-liner initialization
pnpm dlx shadcn@latest mcp init --client claude
```

### Manual Configuration

Add to `.mcp.json`:
```json
{
  "mcpServers": {
    "shadcn": {
      "command": "npx",
      "args": ["shadcn@latest", "mcp"]
    }
  }
}
```

### Features
- List all available components in registries
- Install components directly (`button`, `dialog`, `card`, etc.)
- Support for third-party registries
- Private registry support with auth tokens
- React, Svelte, Vue, React Native support

### Example Prompts
- "Show me all available components in the shadcn registry"
- "Add the button, dialog and card components to my project"
- "What components are available in the @acme registry?"

---

## 2. Next.js DevTools MCP

**Source:** https://github.com/vercel/next-devtools-mcp

### Requirements
- Node.js v20.19+
- Next.js 16+ (for full features)

### Configuration

Add to `.mcp.json`:
```json
{
  "mcpServers": {
    "next-devtools": {
      "command": "npx",
      "args": ["-y", "next-devtools-mcp@latest"]
    }
  }
}
```

Or install via CLI:
```bash
claude mcp add next-devtools npx next-devtools-mcp@latest
```

### Features
- **Error Detection:** Build errors, runtime errors, type errors
- **Live State Queries:** Real-time application state
- **Page Metadata:** Routes, components, rendering details
- **Server Actions:** Inspect Server Actions and hierarchies
- **Development Logs:** Dev server logs and console output
- **Knowledge Base:** Next.js documentation search

### Example Prompts
- "What errors exist in my application?"
- "Display my route structure"
- "Show development server logs"

---

## 3. ESLint MCP Server

**Source:** https://eslint.org/docs/latest/use/mcp

### Configuration

Add to `.mcp.json`:
```json
{
  "mcpServers": {
    "eslint": {
      "command": "npx",
      "args": ["@eslint/mcp@latest"]
    }
  }
}
```

### Features
- Lint files for errors
- Fix ESLint violations automatically
- Explain rule violations
- Check specific files or entire codebase

### Example Prompts
- "Check this file for linting errors"
- "Fix all ESLint issues in the current file"
- "Explain this ESLint error"

---

## 4. Tailwind CSS MCP Server

**Source:** https://www.npmjs.com/package/tailwindcss-mcp-server

### Configuration

Add to `.mcp.json`:
```json
{
  "mcpServers": {
    "tailwindcss": {
      "command": "npx",
      "args": ["tailwindcss-mcp-server"]
    }
  }
}
```

### Features
- `get_tailwind_utilities` - Retrieve utility classes by category
- `get_tailwind_colors` - Complete color palette with shades
- `get_tailwind_config_guide` - Framework-specific configs
- `search_tailwind_docs` - Documentation search
- `install_tailwind` - Generate installation commands
- `convert_css_to_tailwind` - CSS to Tailwind conversion

### Example Prompts
- "What Tailwind classes can I use for flexbox?"
- "Convert this CSS to Tailwind classes"
- "Show me the Tailwind blue color palette"

---

## 5. Additional Useful MCPs

### daisyUI Blueprint MCP (if using daisyUI)
- Source: https://daisyui.com/blueprint/
- Real-time daisyUI component context

### TypeScript Code Analysis Worker
- ESLint integration
- TypeScript compiler analysis
- TSQuery pattern matching
- Automated patch generation

---

## Recommended .mcp.json for Next.js + shadcn Projects

```json
{
  "mcpServers": {
    "shadcn": {
      "command": "npx",
      "args": ["shadcn@latest", "mcp"]
    },
    "next-devtools": {
      "command": "npx",
      "args": ["-y", "next-devtools-mcp@latest"]
    },
    "eslint": {
      "command": "npx",
      "args": ["@eslint/mcp@latest"]
    },
    "tailwindcss": {
      "command": "npx",
      "args": ["tailwindcss-mcp-server"]
    }
  }
}
```

---

## What We Already Have (No Changes Needed)

These MCPs from our current setup are still useful:
- **postgres** - Database operations
- **memory** - Knowledge graph
- **filesystem** - File operations
- **sequential-thinking** - Problem solving
- **orchestrator** - Multi-agent coordination

---

## What's NOT Needed

Based on research, these MCPs from the original request are **not necessary**:

| Requested MCP | Reason Not Needed |
|---------------|-------------------|
| Package Manager MCP | npm/pnpm commands work fine via bash |
| Git/GitHub Enhanced | Current `github` MCP + bash git is sufficient |
| Build/Dev Server MCP | `next-devtools-mcp` covers this |
| Browser DevTools MCP | Complex, defer to future |
| TanStack Query MCP | No dedicated MCP exists; not critical |
| API Testing MCP | Use fetch MCP or bash curl |

---

## Migration Checklist

### For New Next.js + shadcn Project:

1. [ ] Initialize Next.js project
2. [ ] Run `pnpm dlx shadcn@latest init`
3. [ ] Run `pnpm dlx shadcn@latest mcp init --client claude`
4. [ ] Add remaining MCPs to `.mcp.json`
5. [ ] Restart Claude Code
6. [ ] Test with `/mcp` command

### For Existing Projects:

1. [ ] Add `.mcp.json` to project root
2. [ ] Copy configuration from "Recommended .mcp.json" above
3. [ ] Restart Claude Code
4. [ ] Verify connections with `/mcp`

---

## Sources

- [shadcn MCP Server (Official)](https://ui.shadcn.com/docs/mcp)
- [Next.js DevTools MCP (Vercel)](https://github.com/vercel/next-devtools-mcp)
- [ESLint MCP Server](https://eslint.org/docs/latest/use/mcp)
- [Tailwind CSS MCP Server (npm)](https://www.npmjs.com/package/tailwindcss-mcp-server)
- [Community shadcn MCP](https://github.com/Jpisnice/shadcn-ui-mcp-server)
- [daisyUI Blueprint](https://daisyui.com/blueprint/)

---

## Conclusion

The Next.js + shadcn/ui ecosystem has **mature MCP support**. The official shadcn MCP server is particularly impressive - it's built by the shadcn team and integrates directly with the component registry.

**Recommended Action:** Install the 4 priority MCPs listed above for immediate productivity gains in GUI development.

---

---

## Appendix: shadcn Registry Best Practices

**Added:** 2025-11-29
**Source:** https://ui.shadcn.com/docs/registry/mcp

### What This Applies To

The shadcn registry best practices are for **publishing component registries** - how to structure UI components so AI assistants can install them. Most practices are specific to registry publishing, not custom MCP servers.

### Four Core Best Practices (for registry publishers)

1. **Clear Descriptions** - Add concise descriptions to help AI understand component purpose
2. **Proper Dependencies** - List all npm dependencies accurately
3. **Registry Dependencies** - Indicate relationships between components
4. **Consistent Naming** - Use kebab-case throughout

### What Applies to Our Custom MCPs

| Practice | Our Status | Notes |
|----------|------------|-------|
| Clear descriptions | Good | Using `_comment` in configs |
| Consistent naming | Good | kebab-case throughout |
| Documentation | Good | README.md files |
| Version tracking | Partial | In README, not in server metadata |

### What Doesn't Apply to Us

- Registry index files (`registry.json`) - We don't publish component registries
- Schema validation - Our MCPs aren't registries
- Registry dependencies - Not applicable to custom servers

### Action Items (Saved to claude_family.feature_backlog)

1. **MCP Config Comments** (Low, 1h) - Add `_comment` to all agent configs
2. **MCP Server Versioning** (Low, 0.5h) - Add version metadata to servers
3. **Central MCP Inventory** (Medium, 2h) - Document all MCPs used

### Conclusion

**No major changes needed.** The shadcn best practices are primarily for registry publishing. Our current MCP setup follows good practices. Minor improvements saved to backlog.

---

**Version:** 1.1
**Created:** 2025-11-29
**Updated:** 2025-11-29
**Author:** claude-code-unified (claude-family session)
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/MCP_RESEARCH_NEXTJS_SHADCN.md

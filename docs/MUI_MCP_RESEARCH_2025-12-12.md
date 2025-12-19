# MUI & React MCP Research Summary

**Date**: 2025-12-12
**Purpose**: Comprehensive research on MCP servers and AI tools for MUI/React development

---

## 1. Official MUI MCP Server

**Package**: `@mui/mcp`
**Source**: [MUI Official](https://mui.com/material-ui/getting-started/mcp/)

### Installation for Claude Code

```bash
# Local scope (current project)
claude mcp add mui-mcp -- npx -y @mui/mcp@latest

# User scope (all projects)
claude mcp add mui-mcp -s user -- npx -y @mui/mcp@latest
```

### Manual Configuration (.mcp.json)

```json
{
  "mcpServers": {
    "mui-mcp": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@mui/mcp@latest"]
    }
  }
}
```

### What It Provides

- Up-to-date MUI documentation directly in prompts
- Accurate, version-specific component information
- Prevents AI hallucination of non-existent docs/links
- Tools: `useMuiDocs`, `fetchDocs`

### Optional Configuration

- `preferred_theme`: Set light/dark preference
- `component_filter`: Filter to specific components

---

## 2. MUI X MCP Server

**Package**: `@mui/mcp` (covers both Core and X)
**Source**: [MUI X MCP](https://mui.com/x/introduction/mcp/)

Covers advanced components:
- DataGrid (Pro/Premium)
- Date/Time Pickers
- Charts
- Tree View

---

## 3. Alternative MUI MCP - Cloudflare Workers

**Source**: [GitHub - jgentes/mui-mcp-cloudflare](https://github.com/jgentes/mui-mcp-cloudflare)

### Quick Install (Public Server)

```bash
claude mcp add mui npx mcp-remote https://mui-mcp-cloudflare.jgentes.workers.dev/sse
```

### 6 Specialized Tools

| Tool | Purpose |
|------|---------|
| `list_components` | Browse 50+ MUI components |
| `get_component_info` | Get component details, imports, docs links |
| `search_components` | Find by use case (forms, navigation, feedback) |
| `get_customization_guide` | Theming and styling approaches |
| `get_setup_guide` | Installation and setup |
| `get_mui_guide` | Comprehensive docs and best practices |

---

## 4. UX/UI Tools MCP (React + MUI)

**Package**: `@marcusbarcelos/uiux-tools-react-mui`
**Source**: [GitHub](https://github.com/MarcusViniciusBarcelos/uiux-tools-react-mui)

### Installation

```bash
npx @marcusbarcelos/uiux-tools-react-mui
```

### 7 Tools for UX Best Practices

| Tool | Purpose |
|------|---------|
| `apply_responsiveness` | Mobile-first responsive design |
| `apply_material_ui_best_practices` | Theme spacing, alpha, sx prop |
| `apply_apple_design` | Scrollbars, animations, minimalism |
| `apply_nielsen_heuristic` | Apply Nielsen heuristic (1-10) |
| `apply_cognitive_bias` | Fitts, grouping, proximity, etc. |
| `apply_complete_ux` | All guidelines at once |
| `get_ux_checklist` | Validation checklist |

### Best Practices Enforced

**Nielsen's 10 Heuristics:**
1. System visibility
2. Real-world language matching
3. User control
4. Consistency
5. Error prevention
6. Recognition over recall
7. Flexibility
8. Aesthetic design
9. Error recognition
10. Help documentation

**Cognitive Biases:**
- Fitts's Law (44px+ touch targets)
- Grouping effects
- Proximity principles
- Zeigarnik effect (incomplete task indicators)
- Serial position effect
- Hick's Law (choice limitation)

---

## 5. Context7 MCP (General Documentation)

**Package**: `@upstash/context7-mcp`
**Source**: [GitHub - upstash/context7](https://github.com/upstash/context7)

### Installation for Claude Code

```bash
claude mcp add context7 -- npx -y @upstash/context7-mcp
```

### What It Provides

- Up-to-date, version-specific documentation for ANY library
- Supports: React, Vue, Angular, Next.js, TypeScript, and more
- Pulls documentation directly from source
- Prevents outdated training data issues

### Usage

Add "use context7" to prompts:
```
Create a React component using MUI DataGrid. Use context7
```

---

## 6. Figma MCP Server

**Source**: [Figma Official](https://www.figma.com/blog/introducing-figma-mcp-server/)

### What It Provides

- Design-to-code workflow with AI
- Structured React + Tailwind output
- Node tree, variant info, layout constraints, design tokens
- Component mappings via Code Connect

### Requirements

- Figma paid plan with Dev Mode
- Enable "Dev Mode MCP Server" in preferences

### Tool

- `get_design_context`: Structured React + Tailwind representation of Figma selection

### Effectiveness

- 50-70% reduction in initial development time
- Still requires manual adjustments for production

---

## 7. Storybook MCP Server

**Package**: `@storybook/addon-mcp` (official, experimental)
**Source**: [Storybook Addon MCP](https://storybook.js.org/addons/@storybook/addon-mcp)

### Installation

```bash
npm i @storybook/addon-mcp
claude mcp add storybook-mcp --transport http http://localhost:6006/mcp --scope project
```

### What It Provides

- Component metadata, usage snippets, types
- Optimized payload (fewest tokens)
- Autonomous correction loop (run tests, see failures, fix bugs)
- Screenshot capture and analysis

### Community Alternative

```json
{
  "mcpServers": {
    "storybook": {
      "command": "npx",
      "args": ["-y", "storybook-mcp@latest"],
      "env": {
        "STORYBOOK_URL": "<your_storybook_url>/index.json"
      }
    }
  }
}
```

---

## 8. Recommended MCP Stack for MUI/React Projects

### Essential (Install These)

| MCP | Purpose | Priority |
|-----|---------|----------|
| `@mui/mcp` | Official MUI documentation | **HIGH** |
| `@upstash/context7-mcp` | General library docs | **HIGH** |
| `@marcusbarcelos/uiux-tools-react-mui` | UX best practices | **MEDIUM** |

### Optional (Project-Specific)

| MCP | Purpose | When to Use |
|-----|---------|-------------|
| Figma MCP | Design-to-code | If using Figma designs |
| Storybook MCP | Component catalog | If using Storybook |
| mui-mcp-cloudflare | Alternative MUI server | If @mui/mcp has issues |

---

## 9. AI Coding Best Practices for MUI

### Prompt Engineering Tips

1. **Be Specific About Components**
   ```
   Create a MUI DataGrid with sorting, filtering, and pagination for a user list
   ```

2. **Reference Design System**
   ```
   Use theme.spacing() for margins, alpha() for transparency, sx prop for styling
   ```

3. **Request Accessibility**
   ```
   Include ARIA labels and keyboard navigation
   ```

4. **Specify Responsive Behavior**
   ```
   Mobile-first with breakpoints: xs, sm, md, lg, xl
   ```

### Component Patterns That Work Well

- Functional components with hooks
- TypeScript interfaces for props
- sx prop over styled-components for simple cases
- Theme-aware styling with `useTheme()`

### Common Pitfalls

1. Mixing styling approaches (sx, styled, makeStyles)
2. Not using theme spacing/colors
3. Missing accessibility attributes
4. Inconsistent responsive breakpoints
5. Over-customizing standard components

---

## 10. Installation Commands Summary

```bash
# Official MUI MCP (recommended)
claude mcp add mui-mcp -- npx -y @mui/mcp@latest

# Context7 for general docs
claude mcp add context7 -- npx -y @upstash/context7-mcp

# UX/UI Tools for best practices
claude mcp add uiux-tools -- npx -y @marcusbarcelos/uiux-tools-react-mui

# Verify installation
claude mcp list
```

---

## Sources

- [MUI MCP Official](https://mui.com/material-ui/getting-started/mcp/)
- [MUI X MCP](https://mui.com/x/introduction/mcp/)
- [MUI MCP Cloudflare](https://github.com/jgentes/mui-mcp-cloudflare)
- [UX/UI Tools MCP](https://github.com/MarcusViniciusBarcelos/uiux-tools-react-mui)
- [Context7 MCP](https://github.com/upstash/context7)
- [Figma MCP Blog](https://www.figma.com/blog/introducing-figma-mcp-server/)
- [Storybook MCP Addon](https://storybook.js.org/addons/@storybook/addon-mcp)
- [React + AI Stack 2025](https://www.builder.io/blog/react-ai-stack)

---

**Version**: 1.0
**Created**: 2025-12-12
**Location**: C:\Projects\claude-family\docs\MUI_MCP_RESEARCH_2025-12-12.md

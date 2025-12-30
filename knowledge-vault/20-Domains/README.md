---
title: Domain Knowledge Library
category: index
created: 2025-12-28
updated: 2025-12-28
tags:
  - index
  - library
  - reference
status: active
---

# Domain Knowledge Library

**Purpose**: Organized reference library for technical domains and systems

---

## How to Use This Library

**Structure:**
- **20-Domains**: Deep-dive reference docs on specific technical areas
- Each document is a comprehensive guide (not a quick note)
- Focus on "how it works" and "how to use it"
- Includes patterns, anti-patterns, and research findings

**When to Read:**
- Need to understand a system deeply
- Troubleshooting complex issues
- Designing new features
- Onboarding to unfamiliar tech

**When to Update:**
- Discover new patterns
- Solve challenging problems
- Research yields insights
- Configuration changes

---

## Domain Categories

### Claude Code System

#### [[Claude Code Hooks]]
**Purpose**: Hook system for automating workflows
**Topics**:
- Hook types (Prompt, Command)
- Configuration (File vs Database)
- Common patterns (validation, auto-apply, logging)
- Anti-patterns (chatty hooks, long timeouts)
- Research: UserPromptSubmit removal

**Use When**:
- Adding automation to workflow
- Troubleshooting hook behavior
- Designing new validation rules

---

#### [[MCP Server Management]]
**Purpose**: Managing Model Context Protocol servers
**Topics**:
- MCP architecture and lifecycle
- Global vs Project MCPs
- Windows-specific configuration (cmd /c wrapper)
- Database tracking (mcp_configs table)
- Common MCPs (postgres, tailwind, mui)
- Research: Playwright MCP vs Orchestrator agent

**Use When**:
- Setting up new project
- Adding tech stack-specific tools
- Troubleshooting MCP loading
- Optimizing context usage

---

### Database & Data Management

#### PostgreSQL Operations
**Status**: TODO
**Topics**:
- Schema design patterns
- Query optimization
- Index strategies
- Data gateway enforcement
- column_registry system

---

### Development Workflows

#### Git & Version Control
**Status**: TODO
**Topics**:
- Commit conventions
- Branch strategies
- Hooks integration
- Code review process

---

#### Testing Patterns
**Status**: TODO
**Topics**:
- Unit vs Integration tests
- Test organization
- Playwright usage
- Regression testing

---

### Technology Stacks

#### Tauri Desktop Development
**Status**: TODO
**Topics**:
- Architecture (Rust + Web frontend)
- Tauri commands
- IPC patterns
- Build & deployment

---

#### HTMX + Alpine.js
**Status**: TODO
**Topics**:
- Server-driven patterns
- Component architecture
- State management
- DaisyUI integration

---

#### React + Material-UI
**Status**: TODO
**Topics**:
- Component patterns
- MUI theming
- DataGrid usage
- State management (React Query, Zustand)

---

## Research Archive

### Recent Research (2025-12-28)

#### Hook System Optimization
**Problem**: Verbose "Operation stopped by hook" messages
**Investigation**: UserPromptSubmit prompt hook evaluating every message
**Solution**: Removed chatty hook, documented pattern
**Documentation**: [[Claude Code Hooks]]

---

#### MCP Configuration Standardization
**Problem**: Windows wrapper warnings, redundant Playwright MCP
**Investigation**:
- Windows requires `cmd /c` for npx commands
- Playwright available via orchestrator agent
**Solution**:
- Updated .mcp.json to use cmd wrapper
- Removed Playwright MCP, use agent instead
**Documentation**: [[MCP Server Management]]

---

## Document Standards

### Required Sections

Every domain document should include:

1. **Frontmatter**: YAML metadata
2. **Purpose**: What this domain is about
3. **Core Concepts**: Key ideas and architecture
4. **Patterns**: How to use it correctly
5. **Anti-Patterns**: What to avoid
6. **Research Notes**: Discoveries and investigations
7. **Best Practices**: Actionable guidelines
8. **Examples**: Real-world usage
9. **Troubleshooting**: Common issues
10. **Related Docs**: Links to other relevant knowledge

---

### Writing Guidelines

**Be Comprehensive**: These are reference docs, not quick notes
**Be Practical**: Include real examples and code snippets
**Be Clear**: Explain why, not just what
**Be Current**: Update when patterns change
**Be Linked**: Connect related concepts

---

## Contributing to the Library

### Adding a New Domain Document

1. **Identify Domain**: Is this a distinct technical area?
2. **Check Existing**: Don't duplicate - enhance existing docs
3. **Create File**: `20-Domains/{Domain Name}.md`
4. **Use Template**: Follow standard section structure
5. **Add to Index**: Update this README
6. **Link Related**: Reference from other relevant docs

---

### Updating Existing Documents

**When to Update:**
- New pattern discovered
- Anti-pattern identified
- Research yields insights
- Configuration changes
- Best practice evolves

**How to Update:**
1. Add to relevant section
2. Update version/date in frontmatter
3. Add changelog entry if major change
4. Update related documents if needed

---

## Future Domains

### Planned Documentation

- [ ] PostgreSQL Operations
- [ ] Git & Version Control
- [ ] Testing Patterns
- [ ] Tauri Desktop Development
- [ ] HTMX + Alpine.js Stack
- [ ] React + Material-UI Stack
- [ ] Claude API Integration
- [ ] Agentic Orchestration
- [ ] Knowledge Management (Obsidian + DB sync)
- [ ] Security & Secrets Management

---

## Quick Reference

| Need | See |
|------|-----|
| Set up project hooks | [[Claude Code Hooks]] |
| Add MCP to project | [[MCP Server Management]] |
| Troubleshoot hook issues | [[Claude Code Hooks#Troubleshooting]] |
| Fix Windows MCP warning | [[MCP Server Management#Windows-Specific Configuration]] |
| Remove chatty hook | [[Claude Code Hooks#Anti-Patterns]] |
| Choose MCP vs Agent | [[MCP Server Management#Research]] |

---

**Version**: 1.0
**Created**: 2025-12-28
**Updated**: 2025-12-28
**Location**: 20-Domains/README.md

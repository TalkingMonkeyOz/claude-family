---
projects:
- project-metis
- claude-family
tags:
- research
- tree-sitter
- code-analysis
---

# Code Analysis Tooling Evaluation

## Executive Summary

Tree-sitter MCP servers have matured significantly since early 2025, but Claude Code's built-in tools (Glob, Grep, Read) plus its emerging LSP support cover 70-80% of the same ground. The strongest case for adding tree-sitter is **structural code search** (find all functions matching a pattern, not just text) and **cross-project code health metrics** for METIS. However, **ast-grep** has emerged as a leaner, more practical alternative to raw tree-sitter for MCP integration.

## 1. Current Tree-Sitter MCP Servers

### wrale/mcp-server-tree-sitter (Python, 272 stars)

The canonical implementation. 22 tools across project management, AST analysis, search, symbol extraction, and complexity analysis.

**Working well**: AST traversal, symbol extraction (functions/classes/imports), text search, query templates, dependency analysis, complexity metrics. All 185 tests pass.

**Broken/weak**: `find_similar_code` executes but returns no results. UTF-16 encoding unsupported.

**Setup**: `pip install mcp-server-tree-sitter`, Python 3.10+. Languages via tree-sitter-language-pack (Python, JS, TS, Go, Rust, C/C++, Java, Kotlin, C#, Swift, 12+ total).

**Verdict**: Feature-rich but heavy. 22 tools is a large MCP surface area. Parse tree caching is in-memory only (lost on restart).

### nendotools/tree-sitter-mcp (Node.js, 29 stars)

Leaner alternative with 4 core tools: `search_code`, `find_usage`, `analyze_code`, `check_errors`. Also works as standalone CLI.

**Strengths**: Sub-100ms search, zero-config (auto-detects project structure), supports 15+ languages including C#. Dual CLI/MCP mode useful for CI pipelines.

**Verdict**: Better fit for our ecosystem (simpler surface, Node.js aligns with our tooling). But lower community adoption.

### ast-grep/ast-grep-mcp (Rust-based, experimental)

Uses ast-grep instead of raw tree-sitter. 4 tools: `dump_syntax_tree`, `test_match_code_rule`, `find_code`, `find_code_by_rule`.

**Key differentiator**: Pattern matching uses code-like syntax rather than S-expressions. Write `function $NAME($PARAMS) { $$$ }` instead of tree-sitter query DSL. YAML rule system for complex multi-condition searches.

**Verdict**: Most promising for practical use. Pattern syntax is intuitive, Rust performance is excellent, and YAML rules are composable. Experimental status is the main risk.

## 2. What Tree-Sitter Can Do For Us

| Capability | Tree-sitter Support | Current Claude Code Alternative |
|------------|--------------------|---------------------------------|
| Duplicate function detection | Weak (`find_similar_code` broken in wrale) | Grep + manual comparison |
| Function/class/module maps | Strong (`get_symbols`, `analyze_project`) | Grep for definitions (text-based, noisy) |
| Usage patterns (who calls what) | Moderate (`find_usage` works) | LSP find-references (if configured) |
| Code vs docs drift detection | Not built-in (requires custom queries) | Manual comparison |
| Coding standards enforcement | Strong (nesting depth, complexity metrics) | ESLint/Roslyn (language-specific) |
| Cross-language analysis | Strong (same tool, 15+ languages) | Separate tools per language |

**Honest assessment**: The "function map" and "complexity analysis" capabilities are genuinely useful and not well-covered by Claude Code's built-in tools. Usage tracking and duplicate detection are theoretically possible but not production-ready in any current MCP implementation.

## 3. Alternatives to Tree-Sitter

### LSP via MCP (cclsp, lsp-mcp-server)

Multiple LSP-to-MCP bridges exist. Claude Code itself has emerging LSP support (undocumented as of early 2026, 600x faster navigation when enabled).

**Advantages**: Type-aware analysis, go-to-definition, find-references, rename refactoring, diagnostics. Already understands the full type system.

**Disadvantages**: One LSP server per language. Requires language server installation and configuration. Session-scoped (no persistence).

**Our situation**: We work primarily with C#, Python, TypeScript. Each would need its own LSP server (OmniSharp, Pylsp, tsserver). Heavy setup cost but high accuracy.

### CodeScene MCP Server (32 stars, v0.3.1 March 2026)

Exposes CodeScene's Code Health analysis locally. Hotspot identification, technical debt scoring, delta reviews, maintainability metrics.

**Key insight**: Runs fully locally, no cloud dependency for analysis. But requires CodeScene subscription for advanced features. The "Code Health" metric (cognitive complexity for humans) is genuinely differentiated from raw AST metrics.

**Verdict**: Best-in-class for code health dashboards but subscription cost makes it impractical for our infrastructure project. Worth revisiting for METIS client-facing features.

### ast-grep (standalone, no MCP)

Rust-based structural search tool. Can be used directly via Bash tool in Claude Code without an MCP server. `ast-grep run --pattern 'function $NAME() { $$$ }' --lang typescript` works today.

**Verdict**: Lowest-friction option. Install via cargo/npm, use via Bash. No MCP overhead. Pattern syntax is the most developer-friendly of all options.

### Roslyn Analyzers (C# specific)

For our C#/WinForms/WPF projects, Roslyn analyzers provide deeper analysis than tree-sitter ever could: type resolution, data flow, control flow, custom diagnostics.

**Verdict**: Keep using for C# projects. Tree-sitter adds nothing here.

### ESLint/Prettier (JS/TS specific)

Already well-integrated into most JS/TS projects. Rules are more mature and community-tested than tree-sitter queries.

**Verdict**: Keep using for JS/TS. Tree-sitter adds cross-language consistency but not depth.

## 4. The METIS Angle

For a multi-tenant AI delivery platform, code analysis serves four functions:

### Project Onboarding
When METIS onboards a new client project, automated code analysis could:
- Generate a codebase map (modules, dependencies, entry points)
- Assess code health (complexity hotspots, test coverage gaps)
- Detect patterns and frameworks in use (auto-configure tooling)

**Best tool**: ast-grep for structure mapping + CodeScene for health scoring. Tree-sitter MCP is overkill here; a one-time analysis script is sufficient.

### Code Health Dashboards
Ongoing metrics for client projects:
- Complexity trends over time
- Hotspot identification (files changed frequently + high complexity)
- Technical debt quantification

**Best tool**: CodeScene (purpose-built for this) or custom ast-grep scripts feeding a dashboard DB. Tree-sitter MCP could work but would need significant custom tooling on top.

### Automated Refactoring Suggestions
AI-generated refactoring recommendations based on structural analysis:
- Extract method suggestions for long functions
- Identify dead code
- Suggest pattern consolidation

**Best tool**: LSP (type-aware refactoring) > ast-grep (structural patterns) > tree-sitter (raw AST). None of the current MCP servers do this well out of the box.

### Documentation Drift Detection
Compare code structure against architecture docs:
- Do documented modules still exist?
- Are documented APIs still present?
- Has the dependency graph changed?

**Best tool**: Custom tooling. No MCP server addresses this. A BPMN process comparing `get_symbols` output against vault docs would be a novel contribution.

## 5. Practical Evaluation: Should We Add Tree-Sitter MCP Today?

### Setup Cost

**wrale/mcp-server-tree-sitter**: Add to `.mcp.json`, install via pip. ~30 min setup. 22 tools added to MCP surface (increases tool selection overhead for Claude).

**nendotools/tree-sitter-mcp**: `npm install -g @nendo/tree-sitter-mcp`. 4 tools. ~15 min setup.

**ast-grep/ast-grep-mcp**: `npm install`. 4 tools. Experimental. ~15 min setup.

### Recommendation: Not Yet, But Watch ast-grep

**Don't add today** because:
1. Claude Code's Glob + Grep + Read covers 70-80% of code navigation needs
2. LSP integration (when it stabilizes) will cover type-aware analysis better
3. 22 extra MCP tools (wrale) creates tool selection noise
4. `find_similar_code` (the most valuable feature for dedup) is broken
5. Our codebase is primarily Python + C# — Roslyn handles C#, and Python's AST module handles Python

**Watch for**:
- ast-grep MCP moving from experimental to stable
- Claude Code's LSP support becoming official
- CodeScene MCP dropping the subscription requirement
- A tree-sitter MCP that actually delivers working duplicate detection

**Quick win available now**: Install ast-grep CLI (`cargo install ast-grep` or `npm i @ast-grep/cli -g`) and use it via Bash tool for ad-hoc structural searches. No MCP overhead, immediate value.

## 6. Decision Matrix

| Option | Setup Cost | Value Add | Maintenance | Recommendation |
|--------|-----------|-----------|-------------|----------------|
| wrale tree-sitter MCP | Medium | Medium | High (22 tools) | Skip |
| nendotools tree-sitter MCP | Low | Low-Medium | Low | Maybe later |
| ast-grep MCP | Low | Medium | Low | Watch (experimental) |
| ast-grep CLI (no MCP) | Very Low | Medium | None | **Do this now** |
| LSP MCP bridge | High | High | High | Wait for Claude Code native |
| CodeScene MCP | Medium | High | Medium | Evaluate for METIS clients |
| Status quo (Grep/Glob) | Zero | Baseline | Zero | Keep |

---
**Version**: 1.0
**Created**: 2026-03-19
**Updated**: 2026-03-19
**Location**: knowledge-vault/10-Projects/Project-Metis/research/code-analysis-tooling-evaluation.md

---
projects:
- claude-family
tags:
- research
- project-structure
- python
- monorepo
- documentation
---

# Research: Project Structure Best Practices (2025-2026)

Research date: 2026-03-19. Focus: actionable recommendations for a Python-heavy
infrastructure project with MCP servers, hook scripts, and a knowledge vault.

---

## 1. Python Project Folder Structure

Sources: [Python Packaging src vs flat](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) |
[Hitchhiker's Guide](https://docs.python-guide.org/writing/structure/) |
[Cleanest structure 2025](https://medium.com/the-pythonworld/the-cleanest-way-to-structure-a-python-project-in-2025-4f04ccb8602f)

### src/ vs flat layout

| Layout | Use when |
|--------|----------|
| **src/** | Package will be pip-installed or published. Prevents import-from-local-dir bugs. |
| **Flat** | Standalone scripts, tooling repos not meant to be installed. |

**Verdict for claude-family**: Flat layout is correct. Scripts and hooks are standalone — not a pip-installable package. Organise by *function*, not package hierarchy.

### Recommended flat layout

```
project-root/
├── pyproject.toml          # Central config for ruff, pytest
├── scripts/                # CLI helpers, maintenance, hooks
├── mcp-servers/            # Sub-projects, each with own pyproject.toml
│   ├── project-tools/
│   └── bpmn-engine/
├── tests/                  # Mirrors scripts/ structure
├── docs/                   # Long-form documentation
└── .claude/                # AI assistant configuration
```

Key rule: group by *purpose*, not file type. `scripts/` beats a flat root full of `.py` files.

---

## 2. Monorepo Structure

Sources: [Cracking the Python Monorepo](https://gafni.dev/blog/cracking-the-python-monorepo/) |
[Tweag deep-dive](https://www.tweag.io/blog/2023-04-04-python-monorepo-1/) |
[uv monorepo 2026](https://medium.com/@naorcho/building-a-python-monorepo-with-uv-the-modern-way-to-manage-multi-package-projects-4cbcc56df1b4)

### uv workspaces (2025 community standard for medium teams)

Each sub-project has its own `pyproject.toml`; all share a single `uv.lock` at root.

```toml
# Root pyproject.toml
[tool.uv.workspace]
members = ["mcp-servers/*"]
```

### Canonical two-folder split

Community consensus separates monorepos into:
- **apps/** (or named sub-dirs) — independently runnable services
- **lib/** or **shared/** — code reused across multiple apps

Applied to claude-family: `mcp-servers/` = apps, `scripts/` = shared utilities.

### Tool comparison

| Tool | Fit |
|------|-----|
| **uv workspaces** | Best for small-to-medium Python monorepos (2025 default) |
| **Pants** | Large teams needing fine-grained rebuild caching |
| **Bazel** | Enterprise, polyglot |

---

## 3. AI-Assisted Codebase Organisation

Sources: [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices) |
[Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) |
[7 real-project practices 2026](https://www.eesel.ai/blog/claude-code-best-practices)

### What makes a codebase discoverable by AI

1. **CLAUDE.md at root** — read every session. Keep under 200 lines. Use as index, not encyclopedia.
2. **Sub-directory CLAUDE.md files** — scope rules to specific sub-dirs (e.g., `mcp-servers/project-tools/CLAUDE.md`).
3. **Descriptive directory names** — AI tools traverse by name. `hooks/` is clearer than `misc/`.
4. **Progressive disclosure** — `CLAUDE.md` links to spec files; detail lives in specs.
5. **`.claude/commands/`** — slash commands checked into git are team-wide and session-persistent.

### Structure optimisations for AI assistants

- Flat > deeply nested (fewer traversal hops)
- One responsibility per directory
- README in each sub-directory explaining its purpose
- Avoid catch-all folders (`utils/`, `misc/`, `helpers/`) — split by domain instead

---

## 4. Documentation: Co-located vs Separate docs/

Sources: [Docs as Code — Write the Docs](https://www.writethedocs.org/guide/docs-as-code/) |
[Docs-as-Code explained](https://www.techtarget.com/searchapparchitecture/tip/Docs-as-Code-explained-Benefits-tools-and-best-practices) |
[5 critical docs-as-code practices](https://hyperlint.com/blog/5-critical-documentation-best-practices-for-docs-as-code/)

### Rules of thumb

| Doc type | Where it lives |
|----------|---------------|
| API reference / usage for a module | README.md alongside that module |
| Architecture decisions | `docs/adr/` |
| SOPs and procedures | `docs/sop/` or `knowledge-vault/40-Procedures/` |
| Research findings | `docs/research/` |
| Persistent domain knowledge | `knowledge-vault/20-Domains/` |

Core principle: proximity to code matters more than exact folder. Docs in a separate wiki get forgotten; docs in the same repo, same PR, stay current.

**Anti-pattern**: Giant `docs/` root with 150+ flat files. Topic sub-folders prevent rot.

---

## 5. Enforcing Project Structure

Sources: [pre-commit.com](https://pre-commit.com/) |
[Pre-Commit Hooks Guide 2025](https://gatlenculp.medium.com/effortless-code-quality-the-ultimate-pre-commit-hooks-guide-for-2025-57ca501d9835) |
[MegaLinter](https://megalinter.io/)

### Enforcement stack (lightest to heaviest)

1. **pre-commit hooks** (local, fast — target < 5 seconds)
   - `ruff` — replaces black + flake8 + isort in one tool
   - Custom hook: flag `.py` files placed in project root
   - Custom hook: validate CLAUDE.md line count

2. **CI checks** (slower, catches what pre-commit misses)
   - `ruff check` on push
   - `pytest` on merge to main
   - File-placement assertion: fail if `*.py` in project root

3. **Naming conventions** (zero-cost enforcement)
   - Date-prefix for temporal docs: `2026-03-19-audit.md`
   - kebab-case for evergreen docs

### What pre-commit should NOT do

Move these to CI — they are too slow for local hooks: full test suite, integration tests, complex import checks.

---

## Summary: Recommendations for claude-family

| Area | Action |
|------|--------|
| Python layout | Keep flat; add root `pyproject.toml` for ruff + pytest config |
| Monorepo | Add uv workspace config; each MCP server gets own `pyproject.toml` |
| AI discoverability | Add README.md to each sub-dir; keep CLAUDE.md under 200 lines |
| docs/ folder | Create `research/`, `sop/`, `designs/` sub-folders; stop adding flat files to root |
| Enforcement | Add `.pre-commit-config.yaml` with ruff + file-placement hook |

---

**Version**: 1.0
**Created**: 2026-03-19
**Updated**: 2026-03-19
**Location**: docs/research-project-structure-best-practices.md

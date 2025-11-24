# Documentation Management - Simple System

**Created**: 2025-10-23
**Purpose**: Keep documentation maintainable without over-engineering

---

## The System

**3 Components:**

1. **`.docs-manifest.json`** - Single source of truth
   - Lists all markdown files
   - Tracks status (active, deprecated, archive-candidate)
   - Records line counts and purposes

2. **`scripts/audit_docs.py`** - Monthly audit
   - Checks CLAUDE.md ≤250 lines
   - Lists files needing archival
   - Identifies docs >90 days deprecated

3. **Git pre-commit hook** - Automatic enforcement
   - Blocks commits if CLAUDE.md >250 lines
   - No manual checking needed

---

## Rules

1. **CLAUDE.md must be ≤250 lines** (enforced by git hook)
2. **Deprecated docs kept 90 days**, then archived
3. **Audit monthly** via `/session-start` reminder
4. **Archive to `docs/archive/YYYY-MM/`** when ready

---

## Commands

```bash
# Install git hook (one-time)
python scripts/install_git_hooks.py

# Run audit (monthly)
python scripts/audit_docs.py

# Archive old files
python scripts/archive_docs.py --month 2025-10

# Update manifest line counts
python scripts/update_manifest_lines.py
```

---

## Why This Works

**Simple**: 3 files, 4 commands, minimal maintenance
**Automated**: Git hook prevents bloat automatically
**Discoverable**: Audit shows what needs attention
**Flexible**: Can adapt as needs change

---

## Future Vision

When ClaudePM ideas system is ready:
- Migrate manifest to ClaudePM
- Centralized docs management
- Cross-project documentation search

For now: Keep it simple, keep it in claude-family repo.

---

**Replaced**: DOCUMENTATION_STANDARDS_v1.md (736 lines → 70 lines)

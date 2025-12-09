**QUICK SESSION RESUME - Context at a Glance**

Read TODO_NEXT_SESSION.md from current project and display last session context.

---

## Instructions

1. Look for `docs/TODO_NEXT_SESSION.md` in the current working directory
2. If it exists, read it and extract:
   - Last Updated date
   - "Completed This Session" summary
   - "Next Steps" items (top 3)
3. Run `git status --short | wc -l` for uncommitted file count
4. Check inbox with `mcp__orchestrator__check_inbox` for pending messages

---

## Display Format

```
╔══════════════════════════════════════════════════════════════╗
║  SESSION RESUME - {project name from CLAUDE.md}              ║
╠══════════════════════════════════════════════════════════════╣
║  Last Updated: {from TODO file header}                       ║
║  Summary: {from "Completed This Session" section}            ║
╠══════════════════════════════════════════════════════════════╣
║  NEXT STEPS:                                                 ║
║  1. {first priority item}                                    ║
║  2. {second priority item}                                   ║
║  3. {third priority item}                                    ║
╠══════════════════════════════════════════════════════════════╣
║  UNCOMMITTED: {count} files | MESSAGES: {pending count}      ║
╚══════════════════════════════════════════════════════════════╝
```

---

## If No TODO File Exists

Create one! Use this template:

```markdown
# Next Session TODO

**Last Updated**: {today's date}
**Last Session**: {brief description}

## Completed This Session
- Item 1
- Item 2

## Next Steps
1. First priority
2. Second priority
3. Third priority
```

Save to `docs/TODO_NEXT_SESSION.md` in the project root.

---

**Usage**: Run `/session-resume` at start of any session for instant context.

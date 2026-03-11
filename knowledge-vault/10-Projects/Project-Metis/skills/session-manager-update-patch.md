## Companion Skill Addition for project-session-manager

The following section should be inserted into `project-session-manager/SKILL.md` immediately after the "Why This Skill Exists" section (after line 23, before "## CRITICAL: Session Start and End Are Mandatory"):

```markdown
## Companion Skill

**This skill pairs with `gate-framework`.** Session-manager defines *session discipline* — how to start/end sessions, store decisions, checkpoint progress, and hand off between chats. Gate-framework defines the *design methodology* — what gates to pass through, what deliverables exist, how to assess readiness.

Use both together on any design project spanning multiple sessions:
- Session-manager tells you *how to persist progress* so nothing is lost between chats
- Gate-framework tells you *what gate you're at* and *what deliverables remain*

If you're using session-manager without gate-framework, you'll have continuity but no design structure. If you're using gate-framework without session-manager, you'll lose track of progress across sessions.
```

### How to install
Copy this section into the live skill file at its installed location, or reinstall the skill from this vault copy.

# Bug Report: history.jsonl.lock EBADF Error

**Reporter**: Claude Family Project
**Date**: 2026-01-04
**Product**: Claude Code CLI
**Platform**: Windows 11

---

## Error Message

```
Error: EBADF: bad file descriptor, realpath 'C:\Users\johnd\.claude\history.jsonl.lock'
```

## Environment

- OS: Windows 11
- Claude Code: Latest version (as of 2026-01-04)
- Shell: Git Bash / PowerShell

## Description

Random `EBADF: bad file descriptor` error occurs when Claude Code attempts to access the history.jsonl.lock file. The error appears intermittently during normal operation.

## Impact

- Intermittent errors during session
- May cause history logging issues
- Does not appear to crash the session

## Steps to Reproduce

1. Run Claude Code on Windows 11
2. Work normally with the CLI
3. Error appears randomly during file operations

## Notes

- This is a **Claude Code internal bug**, not related to user hooks or configuration
- The file locking mechanism on Windows may be the root cause
- Similar issues have been reported with lock files on Windows

---

## To Report to Anthropic

1. Go to: https://github.com/anthropics/claude-code/issues
2. Search for existing "EBADF" or "history.jsonl.lock" issues
3. If none found, create new issue with this information

---

**Version**: 1.0
**Created**: 2026-01-04
**Location**: docs/bugs/EBADF_HISTORY_LOCK_BUG.md

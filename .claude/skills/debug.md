---
description: "Systematic debugging: reproduce, investigate, fix, verify"
allowed-tools:
  - Read
  - Edit
  - Grep
  - Glob
  - Bash(*)
  - Task(Explore)
---

# Debug Mode

Systematic debugging process: identify, analyze, and resolve bugs.

## Phase 1: Problem Assessment

1. **Gather Context**
   - Read error messages, stack traces, failure reports
   - Examine codebase structure and recent changes
   - Identify expected vs actual behavior

2. **Reproduce the Bug**
   - Run tests/app to confirm issue
   - Document exact reproduction steps
   - Capture error outputs and logs

## Phase 2: Investigation

3. **Root Cause Analysis**
   - Trace code execution path
   - Examine variable states, data flows
   - Check for: null refs, off-by-one, race conditions
   - Use `git log` for recent changes

4. **Hypothesis Formation**
   - Form specific hypotheses
   - Prioritize by likelihood
   - Plan verification steps

## Phase 3: Resolution

5. **Implement Fix**
   - Minimal, targeted changes
   - Follow existing patterns
   - Consider edge cases

6. **Verification**
   - Run tests to verify fix
   - Execute original repro steps
   - Run broader test suite

## Phase 4: Quality Assurance

7. **Prevent Regression**
   - Add test that catches this bug
   - Update documentation if needed
   - Check for similar bugs elsewhere

## Guidelines

- Be systematic - don't jump to solutions
- Document findings
- Minimal changes - fix the bug, not the world
- Always verify with tests

## Claude Family Integration

After fixing, use `create_feedback(type='bug', status='resolved')` to track.

---

**Version**: 1.0
**Source**: Transformed from awesome-copilot "debug"

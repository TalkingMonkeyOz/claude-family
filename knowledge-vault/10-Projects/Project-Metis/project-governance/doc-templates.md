---
projects:
  - Project-Metis
  - claude-family
tags:
  - templates
  - documentation
  - feature-docs
---

# Feature Documentation Templates

Templates for mandatory docs linked to features. Used by `create_feature_doc()` MCP tool. Each template < 100 lines when filled. Claude drafts from context; human reviews.

Reference: [[doc-lifecycle-bpmn]] for when each is required.

---

## Problem Statement {#problem}

Required for: **Features** before `planned → in_progress`

```markdown
# Problem: {Feature Name}

## What
{1-3 sentences: what is the problem?}

## Who Is Affected
{End users, system components, operators?}

## Why Now
{Why solve this in this phase? What dependency or priority drives it?}

## Impact If Not Solved
{What happens if we skip or defer?}

## Constraints
{Known constraints: tech decisions, dependencies, scope boundaries}

## Related Decisions
{Links to remember() decisions or ADRs that inform this}
```

---

## Proposed Solution {#solution}

Required for: **Features** before `planned → in_progress`

```markdown
# Solution: {Feature Name}

## Approach
{2-5 sentences: what are we building and how?}

## Alternatives Considered
| Option | Pros | Cons | Why Not |
|--------|------|------|---------|

## Key Decisions
{Bullets: decisions made for this feature, with rationale}

## Components Affected
{System parts this touches — cross-reference with C4 diagrams}

## Acceptance Criteria
1. {Testable criterion}
2. {Testable criterion}

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
```

---

## Implementation Notes {#implementation}

Required for: **Features** before `in_progress → completed`

```markdown
# Implementation: {Feature Name}

## What Was Built
{Summary: actual implementation vs planned}

## Deviations from Plan
{What changed and why — links to plan_updated events}

## Lessons Learned
{Patterns, gotchas, things to do differently}

## Key Files
{Primary files/modules created or modified}

## Verification
{How acceptance criteria were verified — test results, manual checks}
```

---

## Vision & Scope {#vision}

Required for: **Streams** before `draft → planned`

```markdown
# Vision: {Stream Name}

## Purpose
{What this stream delivers and why it exists}

## Boundaries
{What's IN scope vs OUT of scope}

## Success Criteria
{How we know this stream has achieved its goals}

## Dependencies
{Other streams/features this depends on or enables}

## Key Decisions
{Architectural decisions that shape this stream}
```

---

## Architecture Overview {#architecture}

Required for: **Streams** before `draft → planned`

```markdown
# Architecture: {Stream Name}

## Components
{Key components/services and their responsibilities}

## Data Flow
{How data moves through this stream's components}

## Integration Points
{Where this stream connects to other streams/external systems}

## Technology Choices
{Key tech decisions with rationale — reference ADRs}

## Constraints & Assumptions
{Technical constraints, capacity assumptions, scaling approach}
```

---

## Combined (Lite) {#combined}

For: **Small one-task features** — replaces separate problem + solution.

```markdown
# {Feature Name}

## Problem
{2-3 sentences: what and why}

## Solution
{2-3 sentences: approach}

## Acceptance Criteria
1. {Criterion}

## Key Decisions
{Any decisions, or "N/A — straightforward implementation"}
```

---
**Version**: 1.0
**Created**: 2026-03-16
**Updated**: 2026-03-16
**Location**: knowledge-vault/10-Projects/Project-Metis/project-governance/doc-templates.md

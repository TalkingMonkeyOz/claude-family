---
name: doc-lifecycle
description: Feature documentation lifecycle — create, review, approve docs
---

# Doc Lifecycle Skill

## When to Use

When creating or managing documentation for features in stream-tracked projects.

## Doc Types

| Type | When | Template Sections |
|------|------|-------------------|
| **problem** | Before planning | Problem Statement, Impact, Success Criteria |
| **solution** | During planning | Approach, Alternatives Considered, Risks |
| **implementation** | During build | Architecture, Key Decisions, API Changes |
| **combined-lite** | Small features | Problem + Solution + Implementation (combined) |

## Creating a Feature Doc

1. Create vault file at conventional path:
   ```
   knowledge-vault/10-Projects/{project}/features/{feature_code}/{doc_type}.md
   ```

2. Use YAML frontmatter:
   ```yaml
   ---
   feature: F42
   doc_type: problem
   doc_status: draft
   projects: [project-name]
   tags: [feature-doc]
   ---
   ```

3. Update feature plan_data.docs:
   ```json
   {"docs": {"problem": {"path": "vault/path.md", "status": "draft"}}}
   ```

## Doc Status Flow

`draft` → `reviewed` → `approved` → `superseded`

- **draft**: Initial creation by Claude
- **reviewed**: Human has read and provided feedback
- **approved**: Human signs off
- **superseded**: Replaced by newer version

## Rules

- Stream draft→planned: vision + architecture docs recommended
- Feature planned→in_progress: problem + solution docs recommended  
- Feature in_progress→completed: implementation doc recommended
- Single-task features: combined-lite is sufficient
- These are RECOMMENDATIONS, not blocks (use override_reason if needed)

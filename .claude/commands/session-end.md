**MANDATORY END-OF-SESSION CHECKLIST**

Before ending this session, complete ALL of the following:

---

## 🚨 COMPREHENSIVE SESSION LOGGING 🚨

### ✅ Update Session History (postgres MCP)

**CRITICAL**: Capture both what was DONE and where we LEFT OFF so next Claude can resume instantly.

```sql
-- Update your current session with complete context
UPDATE claude_family.session_history
SET
    session_end = NOW(),

    -- What we accomplished
    session_summary = 'High-level summary of what was done (1-2 sentences)',

    tasks_completed = ARRAY[
        'Specific task 1 completed',
        'Specific task 2 completed',
        'Specific task 3 completed'
    ],

    learnings_gained = ARRAY[
        'Key insight or pattern discovered',
        'Technical learning or gotcha',
        'Decision made and why'
    ],

    challenges_encountered = ARRAY[
        'Problem encountered and how it was solved',
        'Blocker that still exists',
        'Unexpected behavior discovered'
    ],

    -- WHERE WE LEFT OFF (Critical for next session!)
    session_metadata = jsonb_build_object(
        -- Next Steps
        'next_steps', ARRAY[
            'First thing to do next session',
            'Second thing to do',
            'Third priority'
        ],

        -- Pending Work
        'pending_tasks', ARRAY[
            'Task started but not finished',
            'Feature partially implemented',
            'Bug investigation in progress'
        ],

        -- Files Context
        'files_in_progress', ARRAY[
            'path/to/file.cs: Function X needs completion',
            'path/to/other.cs: Refactoring halfway done'
        ],

        -- Decisions Needed
        'decisions_pending', ARRAY[
            'User needs to decide between approach A vs B',
            'Clarification needed on requirement X'
        ],

        -- Current State
        'current_state', jsonb_build_object(
            'build_status', 'passing/failing/not tested',
            'test_status', 'all passing/X failing/not run',
            'branch', 'current-branch-name',
            'last_commit', 'commit-sha',
            'deployment_status', 'deployed/ready/not ready'
        ),

        -- Context for Resumption
        'resumption_context', jsonb_build_object(
            'working_directory', 'C:\Projects\project-name',
            'relevant_docs', ARRAY['docs/file1.md', 'docs/file2.md'],
            'database_state', 'Any DB changes made this session',
            'environment_changes', 'Any env vars or config changes'
        ),

        -- Additional Metadata (optional)
        'version_changes', jsonb_build_object(
            'from', '1.0.0',
            'to', '1.1.0'
        ),
        'external_dependencies', ARRAY[
            'Waiting on API access',
            'Needs user to provide credentials'
        ]
    )

WHERE session_id = (
    SELECT session_id
    FROM claude_family.session_history
    WHERE identity_id = (SELECT identity_id FROM claude_family.identities WHERE identity_name = 'your-identity-name')
    ORDER BY session_start DESC
    LIMIT 1
);
```

---

### ✅ Store Reusable Knowledge (postgres MCP)

**If you discovered a reusable pattern or solution:**

```sql
INSERT INTO claude_family.shared_knowledge
(learned_by_identity_id, knowledge_type, knowledge_category, title, description, applies_to_projects, confidence_level, code_example, gotchas)
VALUES (
    (SELECT identity_id FROM claude_family.identities WHERE identity_name = 'your-identity-name'),
    'pattern', -- or 'technique', 'bug-fix', 'configuration'
    'Category name',
    'Clear pattern title',
    'Detailed description of what this solves and when to use it',
    ARRAY['all'], -- or specific projects
    10, -- confidence 1-10
    'Code example if applicable',
    'Things to watch out for when using this'
);
```

---

### ✅ Store in Memory Graph (memory MCP)

```
mcp__memory__create_entities(entities=[{
    "name": "Session-YYYY-MM-DD-ProjectName",
    "entityType": "Session",
    "observations": [
        "Summary: What was accomplished",
        "Next Steps: What should happen next",
        "Files Modified: List of files",
        "Key Decision: Important choice made",
        "Pending: Incomplete work",
        "Context: Working directory or state info"
    ]
}])
```

**If you solved a problem or discovered a pattern:**

```
mcp__memory__create_entities(entities=[{
    "name": "Pattern-DescriptiveName",
    "entityType": "Pattern",
    "observations": [
        "Problem: What this solves",
        "Solution: How to implement",
        "Example: Code or usage",
        "Gotchas: Things to watch for"
    ]
}])

mcp__memory__create_relations(relations=[{
    "from": "Session-YYYY-MM-DD-ProjectName",
    "relationType": "discovered",
    "to": "Pattern-DescriptiveName"
}])
```

---

## 📋 Pre-Flight Checklist

Before ending, verify ALL of these:

- [ ] **Session logged** with comprehensive summary in postgres
- [ ] **Tasks completed** array filled with specific accomplishments
- [ ] **Learnings gained** array captures key insights
- [ ] **Challenges encountered** documents problems and solutions
- [ ] **Next steps** clearly defined in session_metadata
- [ ] **Pending tasks** documented (what's incomplete)
- [ ] **Files in progress** listed with context
- [ ] **Current state** captured (build, tests, branch, deployment)
- [ ] **Resumption context** provided (working dir, docs, db state)
- [ ] **Decisions pending** documented if any
- [ ] **Reusable knowledge** stored in shared_knowledge if applicable
- [ ] **Memory graph** updated with session entity and observations
- [ ] **Relations created** between problems, patterns, and solutions

**IF ANY ANSWER IS NO → DO IT NOW BEFORE ENDING SESSION**

---

## 💡 Why This Matters

**Without comprehensive logging:**
- ❌ Next Claude spends 30+ minutes getting oriented
- ❌ "Where were we?" becomes a 10-minute interrogation
- ❌ Incomplete work gets forgotten and redone
- ❌ Decisions get re-debated
- ❌ Context gets lost

**With comprehensive logging:**
- ✅ Next Claude resumes in 2 minutes
- ✅ Knows exactly what to do next
- ✅ Has full context on pending work
- ✅ Understands current state
- ✅ Can pick up exactly where you left off

---

## 📝 Example Session End

```sql
UPDATE claude_family.session_history
SET
    session_end = NOW(),
    session_summary = 'Implemented user authentication with OAuth2. Added login/logout flows, token refresh, and session management. All tests passing.',

    tasks_completed = ARRAY[
        'Created AuthService with OAuth2 integration',
        'Implemented token refresh mechanism',
        'Added login/logout UI components',
        'Wrote 12 unit tests for auth flows',
        'Updated documentation in AUTHENTICATION.md'
    ],

    learnings_gained = ARRAY[
        'OAuth2 token refresh must happen 5 minutes before expiry for smooth UX',
        'Cannot use httpOnly cookies with current CORS setup - switched to localStorage',
        'User sessions must be validated on every protected route',
        'Refresh token rotation prevents token replay attacks'
    ],

    challenges_encountered = ARRAY[
        'CORS issues with cookie-based auth - solved by switching to token-based',
        'Token refresh race condition when multiple tabs open - solved with mutex lock',
        'Session persistence across browser restarts - implemented with localStorage'
    ],

    session_metadata = jsonb_build_object(
        'next_steps', ARRAY[
            'Implement password reset flow',
            'Add email verification on signup',
            'Add rate limiting to prevent brute force',
            'Deploy to staging and test with real OAuth provider'
        ],

        'pending_tasks', ARRAY[
            'Email verification partially coded but not tested',
            'Rate limiting service created but not integrated',
            'Password reset UI mockup done, backend pending'
        ],

        'files_in_progress', ARRAY[
            'src/services/EmailService.cs: Verification logic needs completion',
            'src/middleware/RateLimitMiddleware.cs: Integration pending',
            'src/components/PasswordReset.tsx: Backend API not connected yet'
        ],

        'decisions_pending', ARRAY[
            'User wants SMS verification option - need to discuss pricing',
            'Multi-factor auth priority - is this MVP or post-MVP?'
        ],

        'current_state', jsonb_build_object(
            'build_status', 'passing',
            'test_status', '47 tests passing, 0 failing',
            'branch', 'feature/oauth-authentication',
            'last_commit', 'a7f3c9d',
            'deployment_status', 'ready for staging'
        ),

        'resumption_context', jsonb_build_object(
            'working_directory', 'C:\Projects\app-name',
            'relevant_docs', ARRAY['docs/AUTHENTICATION.md', 'docs/API.md'],
            'database_state', 'Added users.refresh_token column, migration applied',
            'environment_changes', 'Added OAUTH_CLIENT_ID and OAUTH_CLIENT_SECRET to .env'
        )
    )
WHERE session_id = 'current-session-uuid';
```

---

**Remember**: The 5 minutes spent logging comprehensively saves the next Claude 30+ minutes of context gathering.

---
description: 'React component architecture standards — centralized constants, max size, hook extraction, TanStack Query'
applyTo: '**/*.tsx,**/*.ts'
source: 'Claude Family (DB: coding_standards)'
---

# React Component Architecture Standards

## Rules

### 1. Centralized Constants
All color maps, label maps, icon maps, status maps go in `src/constants/`.
Never define status colors or type labels inline in a component.

### 2. Single Source Components
If a shared component exists in `src/components/`, import it. Never redefine locally.
Key shared: TabPanel, LoadingState, ErrorAlert, EntityList, EntityEditor, CodeEditor.

### 3. Max Component Size: 300 Lines
Beyond 300 lines, decompose into sub-components in a feature subfolder.

### 4. Hook Extraction
Business logic (API calls, state management, transformations) goes in custom hooks.
Components should be primarily JSX rendering.

### 5. Standard Data Hooks
Use `useQuery`/`useMutation` from @tanstack/react-query for data fetching.
No raw `useState` + `useEffect` + `try/catch` for API calls.

### 6. Centralized Date Utilities
Date formatting in `src/utils/dateUtils.ts`. Available: `formatRelativeTime()`, `formatTimeAgo()`.

### 7. Logical Grouping
- `src/utils/` — shared utilities
- `src/hooks/` — shared hooks
- `src/constants/` — shared constants
- `src/features/<feature>/` — feature code
- `src/components/` — shared components
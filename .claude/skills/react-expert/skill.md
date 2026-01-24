---
name: react-expert
description: React 19.2 frontend engineering - hooks, Server Components, Actions, TypeScript
model: sonnet
agent: coder-sonnet
allowed-tools:
  - Read
  - Edit
  - Write
  - Glob
  - Grep
  - Bash(npm *, npx *)
  - Task(Explore)
---

# React 19.2 Expert Skill

**Status**: Active
**Last Updated**: 2026-01-24

---

## Overview

Expert React 19.2 frontend engineering with modern hooks, Server Components, Actions API, and TypeScript.

---

## React 19.2 Features

| Feature | Use Case |
|---------|----------|
| `<Activity>` | UI visibility, state preservation |
| `useEffectEvent()` | Extract non-reactive logic from effects |
| `cacheSignal` | Cache management |
| `use()` hook | Promise handling, async data |
| `useFormStatus` | Form loading states |
| `useOptimistic` | Optimistic UI updates |
| `useActionState` | Action state management |
| Actions API | Form handling with progressive enhancement |

---

## Core Principles

- **Functional components only** - Class components are legacy
- **TypeScript throughout** - React 19's improved type inference
- **Server Components when beneficial** - RSC for data fetching, reduced bundle
- **Concurrent by default** - `startTransition`, `useDeferredValue`
- **Accessibility by default** - WCAG 2.1 AA, semantic HTML, ARIA
- **React Compiler aware** - Avoid manual memoization when possible

---

## Patterns

### Form with Actions

```tsx
'use client';
import { useFormStatus, useActionState } from 'react';

function SubmitButton() {
  const { pending } = useFormStatus();
  return <button disabled={pending}>{pending ? 'Saving...' : 'Save'}</button>;
}

async function saveAction(prevState: State, formData: FormData) {
  // Server action
}

function MyForm() {
  const [state, formAction] = useActionState(saveAction, initialState);
  return (
    <form action={formAction}>
      <SubmitButton />
    </form>
  );
}
```

### Optimistic Updates

```tsx
const [optimisticItems, addOptimistic] = useOptimistic(
  items,
  (state, newItem) => [...state, { ...newItem, pending: true }]
);
```

### Server Component Data Fetching

```tsx
// app/users/page.tsx (Server Component)
async function UsersPage() {
  const users = await fetchUsers(); // No useEffect needed
  return <UserList users={users} />;
}
```

---

## Technology Stack

| Category | Recommended |
|----------|-------------|
| Build | Vite, Turbopack |
| Testing | Vitest, React Testing Library, Playwright |
| State | React Context, Zustand, Redux Toolkit |
| Styling | Tailwind, CSS Modules, Styled Components |
| UI Library | Shadcn/ui, MUI, Fluent UI |

---

## Testing Pattern

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('form submits correctly', async () => {
  const user = userEvent.setup();
  render(<MyForm />);

  await user.type(screen.getByRole('textbox'), 'value');
  await user.click(screen.getByRole('button', { name: /save/i }));

  expect(screen.getByText('Saved')).toBeInTheDocument();
});
```

---

## Related Skills

- `testing` - Testing patterns
- `a11y` - Accessibility guidelines
- `code-review` - Review React code

---

**Version**: 1.0
**Source**: Transformed from awesome-copilot "Expert React Frontend Engineer"

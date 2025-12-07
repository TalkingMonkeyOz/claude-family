# Development Standards

**Document Type**: Standard
**Version**: 1.0
**Created**: 2025-12-07
**Status**: Active
**Enforcement**: MANDATORY - All development work MUST follow these standards

---

## Purpose

Define consistent development patterns for all projects built by Claude. These standards ensure:
- Predictable code structure across projects
- Maintainable, readable code
- Consistent naming and organization
- Quality through standardized testing

---

## 1. Project Structure

### 1.1 Required Files (ALL Projects)

Every project MUST have these files at the root:

```
project-root/
├── CLAUDE.md              # AI instructions (MANDATORY)
├── ARCHITECTURE.md        # System design (MANDATORY)
├── PROBLEM_STATEMENT.md   # Goals and context (MANDATORY)
├── README.md              # Human overview (MANDATORY)
├── .gitignore             # Git exclusions
├── .env.example           # Environment template (if applicable)
└── .claude/
    ├── hooks.json         # Claude Code hooks
    ├── settings.local.json # Local settings
    └── commands/          # Slash commands
```

### 1.2 Web Application Structure (Next.js/React)

```
project-root/
├── src/
│   ├── app/               # Next.js app router pages
│   │   ├── api/           # API routes
│   │   └── (routes)/      # Page routes
│   ├── components/
│   │   ├── ui/            # Reusable UI components
│   │   ├── forms/         # Form components
│   │   └── [feature]/     # Feature-specific components
│   ├── lib/
│   │   ├── db.ts          # Database client
│   │   ├── api.ts         # API client
│   │   └── utils.ts       # Utility functions
│   ├── hooks/             # Custom React hooks
│   ├── types/             # TypeScript types
│   └── styles/            # Global styles
├── public/                # Static assets
├── tests/                 # Test files
└── docs/                  # Project documentation
```

### 1.3 Python Project Structure

```
project-root/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── main.py
│       └── [modules]/
├── tests/
├── scripts/               # Utility scripts
├── docs/
├── requirements.txt       # Dependencies
├── pyproject.toml         # Project config
└── setup.py               # Package setup
```

---

## 2. Naming Conventions

### 2.1 Files and Directories

| Item | Convention | Example |
|------|------------|---------|
| Directories | lowercase-kebab | `user-management/` |
| TypeScript files | kebab-case | `user-profile.tsx` |
| Python files | snake_case | `user_profile.py` |
| Test files | *.test.ts, *_test.py | `user.test.ts` |
| Constants files | UPPERCASE | `CONSTANTS.ts` |
| Config files | lowercase | `config.ts` |

### 2.2 Code Naming

**TypeScript/JavaScript:**

```typescript
// Variables and functions: camelCase
const userName = "John";
function getUserById(id: string) { }

// Classes and types: PascalCase
class UserService { }
interface UserProfile { }
type UserRole = "admin" | "user";

// Constants: UPPER_SNAKE_CASE
const MAX_RETRY_COUNT = 3;
const API_BASE_URL = "/api";

// Boolean variables: is/has/can prefix
const isLoading = true;
const hasPermission = false;
const canEdit = true;
```

**Python:**

```python
# Variables and functions: snake_case
user_name = "John"
def get_user_by_id(user_id: str): pass

# Classes: PascalCase
class UserService: pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
API_BASE_URL = "/api"

# Private: leading underscore
_internal_cache = {}
def _validate_input(): pass
```

### 2.3 Database Naming

```sql
-- Tables: plural snake_case
CREATE TABLE users (...);
CREATE TABLE build_tasks (...);

-- Columns: snake_case
user_id, created_at, is_active

-- Primary keys: id or table_singular_id
id, user_id, project_id

-- Foreign keys: referenced_table_singular_id
project_id, created_by_user_id

-- Indexes: idx_table_column
idx_users_email

-- Constraints: chk/fk/uq_table_column
chk_users_status
fk_tasks_project_id
uq_users_email
```

---

## 3. Code Organization

### 3.1 File Length

| File Type | Max Lines | Action if Exceeded |
|-----------|-----------|-------------------|
| Component | 200 | Extract subcomponents |
| Service/Module | 300 | Split by responsibility |
| Test file | 500 | Split by feature |
| Config file | 100 | Split by environment |

### 3.2 Function Length

- **Ideal:** 10-20 lines
- **Maximum:** 50 lines
- **If longer:** Extract helper functions

### 3.3 Import Order

```typescript
// 1. External libraries
import React from 'react';
import { useQuery } from '@tanstack/react-query';

// 2. Internal absolute imports
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';

// 3. Relative imports
import { UserCard } from './user-card';
import { useUserData } from './hooks';

// 4. Types (if separate)
import type { User } from '@/types';

// 5. Styles
import styles from './user.module.css';
```

---

## 4. Error Handling

### 4.1 API Errors

```typescript
// Standard error response format
interface ApiError {
  error: {
    code: string;        // "VALIDATION_ERROR", "NOT_FOUND", etc.
    message: string;     // Human-readable message
    details?: Record<string, string>;  // Field-level errors
  };
}

// Standard error codes
const ERROR_CODES = {
  VALIDATION_ERROR: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  INTERNAL_ERROR: 500,
};
```

### 4.2 Try-Catch Pattern

```typescript
// DO: Specific error handling
try {
  await saveUser(data);
} catch (error) {
  if (error instanceof ValidationError) {
    setFieldErrors(error.fields);
  } else if (error instanceof NetworkError) {
    toast.error("Network error. Please try again.");
  } else {
    console.error("Unexpected error:", error);
    toast.error("An unexpected error occurred.");
  }
}

// DON'T: Swallowing errors
try {
  await saveUser(data);
} catch (error) {
  // Silent fail - BAD!
}
```

### 4.3 Logging

```typescript
// Use structured logging
logger.info("User created", { userId, email });
logger.error("Failed to save", { error: error.message, userId });

// Log levels
// - error: Something failed that shouldn't
// - warn: Something unexpected but handled
// - info: Significant events (user actions, API calls)
// - debug: Detailed debugging info (dev only)
```

---

## 5. TypeScript Standards

### 5.1 Type Safety

```typescript
// DO: Explicit types for function parameters and returns
function getUser(id: string): Promise<User | null> { }

// DO: Use const assertions for literals
const STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
} as const;

// DON'T: Use 'any'
function process(data: any) { }  // BAD

// DO: Use 'unknown' and narrow
function process(data: unknown) {
  if (isUser(data)) {
    // data is now typed as User
  }
}
```

### 5.2 Null Handling

```typescript
// DO: Use optional chaining
const name = user?.profile?.name;

// DO: Use nullish coalescing
const displayName = user.name ?? "Anonymous";

// DO: Handle null explicitly in functions
function getDisplayName(user: User | null): string {
  if (!user) return "Unknown";
  return user.name;
}
```

---

## 6. React/Component Standards

### 6.1 Component Structure

```tsx
// Standard component file structure
import { useState, useEffect } from 'react';
import type { ComponentProps } from './types';

// Types first
interface Props {
  userId: string;
  onSave: (user: User) => void;
}

// Component
export function UserEditor({ userId, onSave }: Props) {
  // 1. Hooks (state, effects, queries)
  const [name, setName] = useState('');
  const { data: user, isLoading } = useUser(userId);

  // 2. Derived values
  const isValid = name.length > 0;

  // 3. Effects
  useEffect(() => {
    if (user) setName(user.name);
  }, [user]);

  // 4. Event handlers
  const handleSubmit = () => {
    onSave({ ...user, name });
  };

  // 5. Early returns (loading, error)
  if (isLoading) return <Skeleton />;

  // 6. Main render
  return (
    <form onSubmit={handleSubmit}>
      {/* ... */}
    </form>
  );
}
```

### 6.2 Props Pattern

```typescript
// DO: Destructure props
function Button({ label, onClick, disabled = false }: ButtonProps) { }

// DO: Spread remaining props for wrapper components
function Card({ children, className, ...props }: CardProps) {
  return <div className={cn("card", className)} {...props}>{children}</div>;
}

// DON'T: Pass entire objects when you only need one property
function UserName({ user }: { user: User }) { }  // If only using user.name
function UserName({ name }: { name: string }) { }  // Better
```

---

## 7. Testing Standards

### 7.1 Test Structure

```typescript
describe('UserService', () => {
  describe('getUser', () => {
    it('returns user when found', async () => {
      // Arrange
      const userId = 'test-id';
      mockDb.users.findOne.mockResolvedValue(mockUser);

      // Act
      const result = await userService.getUser(userId);

      // Assert
      expect(result).toEqual(mockUser);
    });

    it('throws NotFoundError when user not found', async () => {
      // Arrange
      mockDb.users.findOne.mockResolvedValue(null);

      // Act & Assert
      await expect(userService.getUser('invalid'))
        .rejects.toThrow(NotFoundError);
    });
  });
});
```

### 7.2 What to Test

| Layer | What to Test | What NOT to Test |
|-------|-------------|------------------|
| Components | User interactions, rendering states | Internal implementation |
| Services | Business logic, edge cases | Framework code |
| API | Request/response format, errors | Database internals |
| Utils | Pure functions, transformations | Trivial getters/setters |

### 7.3 Test Naming

```typescript
// Pattern: "should [expected behavior] when [condition]"
it('should return empty array when no users exist')
it('should throw ValidationError when email is invalid')
it('should update cache after successful save')
```

---

## 8. Git Standards

### 8.1 Commit Messages

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting (no code change)
- `refactor`: Code change (no feature/fix)
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples:**
```
feat: Add user profile page

- Display user avatar and name
- Show recent activity
- Add edit profile button

Closes #123
```

### 8.2 Branch Naming

```
<type>/<ticket>-<description>

feature/PROJ-123-user-profile
bugfix/PROJ-456-login-error
hotfix/critical-security-patch
```

---

## 9. Documentation Standards

### 9.1 Code Comments

```typescript
// DO: Explain WHY, not WHAT
// Cache user data to reduce database calls during bulk operations
const userCache = new Map<string, User>();

// DON'T: Explain obvious code
// Loop through users
for (const user of users) { }

// DO: Document complex logic
/**
 * Calculates compound interest with monthly compounding.
 * Formula: A = P(1 + r/n)^(nt)
 * @param principal Initial amount
 * @param rate Annual interest rate (decimal)
 * @param years Number of years
 */
function calculateInterest(principal: number, rate: number, years: number) { }
```

### 9.2 JSDoc for Public APIs

```typescript
/**
 * Creates a new user account.
 *
 * @param data - User registration data
 * @returns The created user with generated ID
 * @throws {ValidationError} If email is invalid or already exists
 * @throws {DatabaseError} If database operation fails
 *
 * @example
 * const user = await createUser({
 *   email: "john@example.com",
 *   name: "John Doe"
 * });
 */
export async function createUser(data: CreateUserInput): Promise<User> { }
```

---

## 10. Performance Standards

### 10.1 Database Queries

- **Always paginate** lists (never SELECT * without LIMIT)
- **Index** columns used in WHERE, ORDER BY, JOIN
- **Avoid N+1** queries (use joins or batch loading)
- **Use explain** to verify query plans

### 10.2 Frontend Performance

- **Lazy load** routes and heavy components
- **Memoize** expensive calculations (useMemo)
- **Debounce** frequent events (search, resize)
- **Virtualize** long lists (>100 items)

---

## Quick Reference Checklist

Before merging code:

- [ ] Follows naming conventions
- [ ] Has appropriate error handling
- [ ] Includes tests for new functionality
- [ ] No TypeScript errors or warnings
- [ ] No console.log statements (use logger)
- [ ] Commit message follows standard
- [ ] Documentation updated if API changed

---

## Related Documents

- UI_COMPONENT_STANDARDS.md - UI patterns
- API_STANDARDS.md - API conventions
- SOP-006: Testing Process - Test levels

---

**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-07 | Initial version |

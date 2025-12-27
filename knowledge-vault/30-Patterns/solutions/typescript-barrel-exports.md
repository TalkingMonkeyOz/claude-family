---
category: typescript
confidence: 90
created: 2025-12-19
projects:
- mission-control-web
synced: true
synced_at: '2025-12-20T13:15:19.790448'
tags:
- typescript
- exports
- barrel
- services
title: TypeScript Service Export Pattern
type: pattern
---

# TypeScript Service Export Pattern

## Summary
When creating services with barrel exports (index.ts), create service files first with all exports, then update index.ts to match actual exports.

## Details
When using AI agents to generate code, the barrel export file (index.ts) may get out of sync with the actual service implementations. The generated code may use different function names than expected.

### Problem
```typescript
// index.ts (barrel export) assumes:
export { getUserById, createUser } from './userService';

// But actual userService.ts has:
export function fetchUser(id: string) { ... }
export function addNewUser(data: UserData) { ... }
```

### Solution
Always read actual file exports before updating barrel exports:

```typescript
// Step 1: Check what's actually exported
// Read userService.ts to see actual function names

// Step 2: Update barrel to match reality
export { fetchUser, addNewUser } from './userService';
```

## Code Example
```typescript
// services/index.ts - Correct barrel export pattern
// Re-export only what actually exists in each service file

// Read user.service.ts first to confirm exports
export { 
  fetchUser,        // Not getUserById
  addNewUser,       // Not createUser
  updateUser,
  deleteUser 
} from './user.service';

// Read auth.service.ts to confirm exports
export {
  signIn,           // Not login
  signOut,          // Not logout
  refreshToken
} from './auth.service';
```

## Gotcha
Agent-generated code may use different naming conventions than your project. Always verify actual exports before updating barrel files.

## Related
- [[typescript-generic-constraint]]
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: 30-Patterns/solutions/typescript-barrel-exports.md
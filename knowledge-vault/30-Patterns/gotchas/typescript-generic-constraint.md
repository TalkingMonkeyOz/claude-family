---
category: typescript
confidence: 95
created: 2025-12-19
projects:
- mission-control-web
synced: true
synced_at: '2025-12-20T13:15:19.786088'
tags:
- typescript
- generics
- react
- hooks
title: TypeScript Generic Constraint for Table Data
type: gotcha
---

# TypeScript Generic Constraint for Table Data

## Summary
When creating React hooks that accept typed data arrays, use `T extends object` instead of `T extends Record<string, unknown>`.

## Details
TypeScript interfaces don't have index signatures, so they fail the `Record<string, unknown>` constraint. The broader `object` constraint works for interfaces.

### WRONG
```typescript
// TypeScript interfaces fail this constraint
function useTableSort<T extends Record<string, unknown>>(data: T[]): T[] {
    return data.sort(/* ... */);
}

interface User {
    id: number;
    name: string;
}

// ERROR: Type 'User' does not satisfy the constraint 'Record<string, unknown>'
const sorted = useTableSort<User>(users);
```

### CORRECT
```typescript
// Use broader 'object' constraint
function useTableSort<T extends object>(data: T[]): T[] {
    return data.sort(/* ... */);
}

interface User {
    id: number;
    name: string;
}

// Works fine
const sorted = useTableSort<User>(users);
```

## Code Example
```typescript
// Generic table hook with correct constraint
function useTableData<T extends object>(initialData: T[]) {
    const [data, setData] = useState<T[]>(initialData);
    const [sortKey, setSortKey] = useState<keyof T | null>(null);
    
    const sortedData = useMemo(() => {
        if (!sortKey) return data;
        return [...data].sort((a, b) => {
            const aVal = a[sortKey];
            const bVal = b[sortKey];
            if (aVal < bVal) return -1;
            if (aVal > bVal) return 1;
            return 0;
        });
    }, [data, sortKey]);
    
    return { data: sortedData, setSortKey };
}
```

## Why This Happens
TypeScript interfaces are "open" types without index signatures. `Record<string, unknown>` requires an index signature `[key: string]: unknown`. The `object` type is less restrictive and accepts any non-primitive type.

## Related
- [[typescript-utility-types]]
- [[react-generic-hooks]]
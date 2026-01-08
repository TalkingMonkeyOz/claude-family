---
category: architecture
confidence: 95
created: 2026-01-07
projects:
- nimbus-mui
synced: false
tags:
- comparison
- architecture
- pattern
- reusable
- cross-database
title: Cross-Database Comparison Module Pattern
type: pattern
---

# Cross-Database Comparison Module Pattern

## Summary

Reusable architecture for comparing configuration data between two database instances. Used for Contract Rules, Security Roles, Award Rules.

## Architecture Overview

```
src/modules/comparison/
├── index.ts                          # Module exports
├── ComparisonConnectionPanel.tsx     # Dual connection UI (reusable)
├── utils/
│   └── diffEngine.ts                 # Generic deep comparison (reusable)
├── contractRules/                    # Specific comparison type
│   ├── types.ts                      # Entity types + comparison types
│   ├── contractRuleService.ts        # API fetch functions
│   ├── contractRuleComparer.ts       # Comparison logic
│   └── ContractRulesComparisonModule.tsx  # Main UI
├── securityRoles/                    # (Future - same pattern)
│   └── ...
└── awardRules/                       # (Future - same pattern)
    └── ...
```

## Core Components

### 1. Comparison Store (Zustand)

```typescript
interface ComparisonState {
  // Dual connections
  source: ConnectionState;
  target: ConnectionState;

  // Entity data
  sourceRules: EntityType[];
  targetRules: EntityType[];

  // Results
  comparisonResults: ComparisonResult[];
  summary: ComparisonSummary | null;
  isComparing: boolean;
}

type ConnectionState = {
  profile: Profile | null;
  credentials: NimbusCredentials | null;
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  errorMessage: string | null;
};
```

### 2. Comparison Categories

```typescript
type ComparisonCategory =
  | 'exact'       // Identical in both
  | 'similar'     // Same key, different config
  | 'typeMatch'   // Same type, different identifier
  | 'sourceOnly'  // Only in source
  | 'targetOnly'; // Only in target
```

### 3. Comparison Result

```typescript
interface ComparisonResult {
  category: ComparisonCategory;
  sourceEntity: EntityType | null;
  targetEntity: EntityType | null;
  differences: FieldDifference[];
}

interface FieldDifference {
  path: string;           // e.g., "config.timeout"
  sourceValue: unknown;
  targetValue: unknown;
  type: 'added' | 'removed' | 'changed';
}
```

### 4. Diff Engine (Generic)

```typescript
// Deep compare any two objects
function deepCompare(
  source: unknown,
  target: unknown,
  path?: string
): FieldDifference[];

// Skip metadata fields
function shouldSkipField(field: string): boolean;

// Check equality
function deepEqual(source: unknown, target: unknown): boolean;
```

## Adding New Comparison Type

To add Security Roles comparison:

### Step 1: Create folder structure
```
src/modules/comparison/securityRoles/
├── types.ts
├── securityRoleService.ts
├── securityRoleComparer.ts
└── SecurityRolesComparisonModule.tsx
```

### Step 2: Define types
```typescript
// types.ts
export interface SecurityRoleObject {
  SecurityRoleID: number;
  Name: string;
  Permissions: string[];
  // ...
}

export interface SecurityRoleComparisonResult extends ComparisonResult {
  sourceRole: SecurityRoleObject | null;
  targetRole: SecurityRoleObject | null;
}
```

### Step 3: Create service
```typescript
// securityRoleService.ts
export async function fetchSecurityRoles(
  credentials: NimbusCredentials
): Promise<SecurityRoleObject[]> {
  const url = `${credentials.baseUrl}/RESTApi/SecurityRole`;
  // ... fetch logic
}
```

### Step 4: Create comparer
```typescript
// securityRoleComparer.ts
export function compareSecurityRoles(
  sourceRoles: SecurityRoleObject[],
  targetRoles: SecurityRoleObject[]
): { results: ComparisonResult[]; summary: ComparisonSummary } {
  // Match by Name
  // Use diffEngine.deepCompare for field differences
}
```

### Step 5: Create UI
```typescript
// SecurityRolesComparisonModule.tsx
export function SecurityRolesComparisonModule() {
  // Reuse ComparisonConnectionPanel
  // Display results using same pattern
}
```

## Comparison Strategy

### Match Key Selection

| Entity Type | Primary Key | Secondary Key |
|-------------|-------------|---------------|
| Contract Rules | ContractRuleName | Note (description) |
| Security Roles | Name | - |
| Award Rules | RuleName | Category |

### Algorithm

```typescript
function compareEntities(source: Entity[], target: Entity[]) {
  const results: ComparisonResult[] = [];
  const matchedTargetIds = new Set<string>();

  // 1. Match source to target
  for (const sourceEntity of source) {
    const match = findBestMatch(sourceEntity, target, matchedTargetIds);
    if (match) {
      matchedTargetIds.add(match.id);
      const diffs = deepCompare(sourceEntity, match);
      results.push({
        category: diffs.length === 0 ? 'exact' : 'similar',
        sourceEntity,
        targetEntity: match,
        differences: diffs
      });
    } else {
      results.push({
        category: 'sourceOnly',
        sourceEntity,
        targetEntity: null,
        differences: []
      });
    }
  }

  // 2. Find target-only
  for (const targetEntity of target) {
    if (!matchedTargetIds.has(targetEntity.id)) {
      results.push({
        category: 'targetOnly',
        sourceEntity: null,
        targetEntity,
        differences: []
      });
    }
  }

  return results;
}
```

## UI Pattern

```
┌─────────────────────────────────────────────────────┐
│ [Source Profile ▼] [Connect]  │  [Target ▼] [Connect]│
├─────────────────────────────────────────────────────┤
│ Summary Cards (counts by category)                   │
├─────────────────────────────────────────────────────┤
│ Grouped Results List                                 │
│ ├── Source Only (expandable)                         │
│ ├── Similar (expandable with diff details)           │
│ ├── Exact Matches (collapsed by default)             │
│ └── Target Only (expandable)                         │
└─────────────────────────────────────────────────────┘
```

## Related

- [[nimbus-authentication]]
- [[nimbus-rest-crud-pattern]]

---

**Version**: 1.0
**Created**: 2026-01-07
**Updated**: 2026-01-07
**Location**: 30-Patterns/comparison-module-pattern.md

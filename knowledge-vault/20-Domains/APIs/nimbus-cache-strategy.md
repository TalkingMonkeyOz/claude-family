---
category: nimbus-api
confidence: 95
created: 2026-01-07
projects:
- nimbus-mui
- nimbus-import
synced: false
tags:
- nimbus
- cache
- indexeddb
- zustand
- performance
title: Nimbus Two-Tier Caching Strategy
type: pattern
---

# Nimbus Two-Tier Caching Strategy

## Summary

Use IndexedDB for persistence + Zustand Maps for O(1) lookups. Survives app restarts while maintaining fast access.

## Architecture

```
┌─────────────────────────────────────────┐
│         Zustand Store (Memory)          │
│  Map<ID, Entity> for O(1) lookups       │
│  Invalidated on app close               │
├─────────────────────────────────────────┤
│         IndexedDB (Persistent)          │
│  Full entity arrays per type            │
│  Survives app restart                   │
│  Timestamped for freshness              │
└─────────────────────────────────────────┘
           ↑ Hydrate on startup
           ↓ Persist on load
```

## Cache Flow

### Initial Load
1. Check IndexedDB for cached data
2. If fresh (< expiry), hydrate Zustand
3. If stale/missing, fetch from API
4. Store in IndexedDB + hydrate Zustand

### Lookup
1. Check Zustand Map first (O(1))
2. If miss, check IndexedDB
3. If miss, fetch from API

## IndexedDB Schema

```typescript
interface CacheEntry<T> {
  key: string;           // e.g., "locations", "departments"
  data: T[];             // Full entity array
  timestamp: number;     // Date.now() when cached
  expiresAt: number;     // timestamp + TTL
}
```

## Zustand Store Pattern

```typescript
interface CacheStore {
  // Maps for O(1) lookup
  locationsById: Map<number, Location>;
  departmentsById: Map<number, Department>;

  // Loading states
  isLoading: boolean;
  loadedEntities: Set<string>;

  // Actions
  loadFromDb: () => Promise<void>;
  setLocations: (locations: Location[]) => void;
  getLocationById: (id: number) => Location | undefined;
}
```

## Code Example

```typescript
// Cache loader
async function loadLocations(): Promise<Location[]> {
  // 1. Check memory
  const cached = useCacheStore.getState().locations;
  if (cached.length > 0) return cached;

  // 2. Check IndexedDB
  const dbCached = await cacheDb.get('locations');
  if (dbCached && Date.now() < dbCached.expiresAt) {
    useCacheStore.getState().setLocations(dbCached.data);
    return dbCached.data;
  }

  // 3. Fetch from API
  const locations = await fetchLocationsFromApi();

  // 4. Persist + hydrate
  await cacheDb.set('locations', {
    key: 'locations',
    data: locations,
    timestamp: Date.now(),
    expiresAt: Date.now() + (60 * 60 * 1000) // 1 hour
  });
  useCacheStore.getState().setLocations(locations);

  return locations;
}
```

## TTL Guidelines

| Entity Type | TTL | Reason |
|-------------|-----|--------|
| Locations | 1 hour | Rarely changes |
| Departments | 1 hour | Rarely changes |
| Users | 15 min | Changes more frequently |
| Activity Types | 1 hour | Rarely changes |
| Shifts | 5 min | Frequently updated |

## Invalidation Triggers

- User clicks "Refresh" button
- After successful import
- On profile/environment switch
- Manual cache clear in settings

## Related

- [[nimbus-entity-creation-order]]
- [[nimbus-odata-field-naming]]

---

**Version**: 1.0
**Created**: 2026-01-07
**Updated**: 2026-01-07
**Location**: 20-Domains/APIs/nimbus-cache-strategy.md

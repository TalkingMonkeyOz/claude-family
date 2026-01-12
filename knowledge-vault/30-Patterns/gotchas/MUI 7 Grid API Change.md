---
projects:
  - claude-manager-mui
  - nimbus-mui
tags:
  - mui
  - react
  - gotcha
  - breaking-change
synced: false
---

# MUI 7 Grid API Change

**Discovered**: 2026-01-11
**Context**: Subagent experiment - coder-sonnet used deprecated Grid API

---

## The Problem

MUI 7 changed the Grid component API. Agents with older knowledge use the deprecated pattern.

### Deprecated (MUI 5/6)

```tsx
<Grid container spacing={3}>
  <Grid item xs={12} md={6}>
    <TextField />
  </Grid>
</Grid>
```

### Current (MUI 7)

```tsx
<Grid container spacing={3}>
  <Grid size={{ xs: 12, md: 6 }}>
    <TextField />
  </Grid>
</Grid>
```

Or use Box with CSS grid (recommended - more reliable):

```tsx
<Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 3 }}>
  <TextField />
  <TextField />
</Box>
```

---

## TypeScript Error

```
error TS2769: No overload matches this call.
Property 'item' does not exist on type 'IntrinsicAttributes & GridBaseProps...'
```

---

## Prevention

1. Use `mui-coder-sonnet` for MUI work (has MUI MCP with docs)
2. Prefer `Box` with CSS grid over `Grid` component
3. Check MUI version in package.json before suggesting Grid patterns

---

## Files Affected (2026-01-11)

- McpConfigurator.tsx
- ProjectConfigurator.tsx
- ProjectTypeConfigurator.tsx

---

**Version**: 1.0
**Created**: 2026-01-11
**Updated**: 2026-01-11
**Location**: knowledge-vault/30-Patterns/gotchas/MUI 7 Grid API Change.md

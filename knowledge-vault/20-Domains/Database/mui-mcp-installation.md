---
category: tooling
confidence: 90
created: 2025-12-19
projects:
- mission-control-web
synced: true
synced_at: '2025-12-20T13:15:19.807382'
tags:
- mui
- mcp
- react
- material-ui
title: MUI MCP Installation and Best Practices
type: best-practice
---

# MUI MCP Installation and Best Practices

## Summary
Official MUI MCP provides up-to-date Material-UI documentation for AI coding assistants.

## Installation

```bash
claude mcp add mui-mcp -- npx -y @mui/mcp@latest
```

## Best Practices

### 1. Use sx Prop with Theme Values
```tsx
// GOOD - Uses theme spacing
<Box sx={{ p: 2, mt: 1 }}>

// BAD - Hardcoded pixels
<Box sx={{ padding: '16px', marginTop: '8px' }}>
```

### 2. Individual Imports for Tree-Shaking
```tsx
// GOOD - Tree-shakeable
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';

// BAD - Imports entire library
import { Button, TextField } from '@mui/material';
```

### 3. Use Theme Spacing, Not Pixels
```tsx
// GOOD - Theme-aware
<Box sx={{ gap: 2 }}>  // 16px (2 * 8px default spacing)

// BAD - Fixed pixels
<Box sx={{ gap: '16px' }}>
```

### 4. Responsive Breakpoint Syntax
```tsx
// Responsive values using breakpoint object
<Box sx={{ 
  width: { xs: '100%', sm: '50%', md: '33%' },
  display: { xs: 'block', md: 'flex' }
}}>
```

## Code Example
```tsx
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';

function MyComponent() {
  return (
    <Box sx={{ 
      p: { xs: 2, md: 3 },
      display: 'flex',
      flexDirection: 'column',
      gap: 2
    }}>
      <Typography variant="h4">
        Title
      </Typography>
      <Button variant="contained" color="primary">
        Click Me
      </Button>
    </Box>
  );
}
```

## Related
- [[react-component-patterns]]
- [[typescript-generic-constraint]]
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: 20-Domains/Database/mui-mcp-installation.md
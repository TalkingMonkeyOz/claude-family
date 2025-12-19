# UI Component Standards

**Document Type**: Standard
**Version**: 1.0
**Created**: 2025-12-07
**Status**: Active
**Enforcement**: MANDATORY - All UI work MUST follow these standards

---

## Purpose

Define consistent UI patterns for all web applications built by Claude. These standards ensure:
- Consistent user experience across projects
- Predictable behavior for users
- Maintainable, reusable components
- Accessibility compliance

---

## 1. Data Tables

### 1.1 Pagination (REQUIRED)

**ALL tables displaying data MUST have pagination.**

```typescript
// Standard pagination configuration
interface PaginationConfig {
  defaultPageSize: 20;           // Default rows per page
  pageSizeOptions: [10, 20, 50, 100];  // User-selectable options
  showPageSizeSelector: true;    // Allow user to change
  showTotalCount: true;          // "Showing 1-20 of 156"
  showPageNumbers: true;         // 1, 2, 3... navigation
}
```

**Implementation Requirements:**
- Display current range: "Showing 1-20 of 156 items"
- Previous/Next navigation buttons
- Direct page number links (max 5 visible, with ellipsis)
- Page size selector dropdown
- Keyboard navigation support (Tab, Enter)

**API Format:**
```typescript
// Request
GET /api/items?page=1&pageSize=20

// Response
{
  "data": [...],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "totalItems": 156,
    "totalPages": 8
  }
}
```

### 1.2 Sorting (REQUIRED)

**ALL tables MUST support column sorting.**

- Click header to sort ascending
- Click again to sort descending
- Click again to clear sort
- Visual indicator (arrow) on sorted column
- Support multi-column sort (Shift+click)

```typescript
// API Format
GET /api/items?sort=created_at&order=desc
GET /api/items?sort=name,created_at&order=asc,desc  // Multi-sort
```

### 1.3 Filtering (REQUIRED)

**ALL tables MUST have at least ONE filter option.**

**Standard Filter Types:**

| Data Type | Filter Component | Behavior |
|-----------|------------------|----------|
| Text | Search input | Debounced (300ms), searches multiple fields |
| Status/Enum | Dropdown | "All" option + specific values |
| Date | Date range picker | From/To with presets (Today, This Week, etc.) |
| Boolean | Toggle or dropdown | Yes/No/All |
| Numeric | Range input | Min/Max fields |

**Filter UI Placement:**
- Filters appear ABOVE the table
- Search input on the left
- Additional filters to the right
- "Clear all filters" button when any filter active
- Show active filter count badge

### 1.4 Row Actions (REQUIRED)

**Standard actions per row:**

| Action | Icon | Keyboard | Confirmation |
|--------|------|----------|--------------|
| View | Eye | Enter | No |
| Edit | Pencil | E | No |
| Delete | Trash | Delete | YES - Modal |
| Duplicate | Copy | D | No |

**Action Menu:**
- If > 3 actions, use dropdown menu (...)
- Destructive actions (delete) at bottom, in red
- Disable unavailable actions (don't hide)

### 1.5 Bulk Actions

**For tables with checkboxes:**
- Select All checkbox in header
- Show selected count: "3 items selected"
- Bulk action bar appears when items selected
- Standard bulk actions: Delete, Export, Archive

---

## 2. Forms

### 2.1 Field Layout

```
┌─────────────────────────────────────────┐
│ Label *                                  │
│ ┌─────────────────────────────────────┐ │
│ │ Input field                          │ │
│ └─────────────────────────────────────┘ │
│ Helper text or error message            │
└─────────────────────────────────────────┘
```

**Requirements:**
- Labels ABOVE inputs (not inline)
- Required fields marked with asterisk (*)
- Helper text below field (gray, smaller)
- Error text replaces helper text (red)
- Errors show on blur or submit

### 2.2 Validation

**Client-side validation (immediate):**
- Required fields
- Format validation (email, phone, URL)
- Min/max length
- Pattern matching

**Server-side validation (on submit):**
- Uniqueness checks
- Business logic validation
- Cross-field validation

**Error Display:**
- Field-level errors below each field
- Form-level errors in alert at top
- Scroll to first error
- Focus first error field

### 2.3 Submit Behavior

```typescript
// Standard form submit pattern
const onSubmit = async (data) => {
  setIsSubmitting(true);
  try {
    await api.save(data);
    toast.success("Saved successfully");
    router.push("/list");
  } catch (error) {
    if (error.fieldErrors) {
      setFieldErrors(error.fieldErrors);
    } else {
      toast.error(error.message);
    }
  } finally {
    setIsSubmitting(false);
  }
};
```

**Button States:**
- Default: "Save" or "Create"
- Submitting: "Saving..." with spinner, disabled
- Success: Brief "Saved!" then redirect
- Error: Re-enable button, show errors

---

## 3. Component States

### 3.1 Loading States (REQUIRED)

**Every async component MUST show loading state.**

| Component | Loading Pattern |
|-----------|-----------------|
| Page | Full page skeleton |
| Table | Skeleton rows (5) |
| Card | Skeleton with shimmer |
| Button | Spinner inside, disabled |
| Form | Overlay with spinner |

**Implementation:**
```tsx
if (isLoading) {
  return <TableSkeleton rows={5} columns={4} />;
}
```

### 3.2 Empty States (REQUIRED)

**Every list MUST have an empty state.**

```
┌─────────────────────────────────────────┐
│                                         │
│            [Illustration]               │
│                                         │
│         No items found                  │
│                                         │
│   There are no items matching your      │
│   filters. Try adjusting your search.   │
│                                         │
│         [Clear Filters]                 │
│              or                         │
│         [Create First Item]             │
│                                         │
└─────────────────────────────────────────┘
```

**Requirements:**
- Relevant illustration or icon
- Clear heading
- Helpful description
- Action button (create new or clear filters)

### 3.3 Error States (REQUIRED)

**Every component MUST handle errors gracefully.**

```tsx
if (error) {
  return (
    <ErrorState
      title="Failed to load data"
      message={error.message}
      onRetry={() => refetch()}
    />
  );
}
```

**Requirements:**
- Don't show technical errors to users
- Provide retry action
- Log error details for debugging
- Fallback to cached data if available

---

## 4. Dialogs and Modals

### 4.1 Confirmation Dialogs

**REQUIRED for destructive actions:**

```
┌─────────────────────────────────────────┐
│ Delete Item?                        [X] │
├─────────────────────────────────────────┤
│                                         │
│ Are you sure you want to delete         │
│ "Item Name"? This action cannot         │
│ be undone.                              │
│                                         │
├─────────────────────────────────────────┤
│              [Cancel]  [Delete]         │
└─────────────────────────────────────────┘
```

**Requirements:**
- Clear title stating the action
- Consequence explanation
- Cancel button (left, secondary)
- Confirm button (right, danger for delete)
- Close on Escape key
- Focus trap inside modal

### 4.2 Form Dialogs

**For quick create/edit without leaving page:**
- Max width 600px
- Close on backdrop click (if no changes)
- Warn before closing with unsaved changes
- Success toast on save

---

## 5. Navigation

### 5.1 Breadcrumbs

**Required for nested pages (depth > 1):**

```
Home > Projects > Claude Family > Settings
```

- All items except last are links
- Last item is current page (not a link)
- Max 4 levels visible (collapse middle with ...)

### 5.2 Sidebar Navigation

**Standard structure:**
```
├── Dashboard
├── Projects
│   └── (submenu on hover/click)
├── Sessions
├── Feedback
├── Settings
└── Help
```

- Active item highlighted
- Collapsible on mobile
- Icons + text labels
- Keyboard navigable

---

## 6. Responsive Design

### 6.1 Breakpoints

```css
/* Standard breakpoints */
--breakpoint-sm: 640px;   /* Mobile landscape */
--breakpoint-md: 768px;   /* Tablet */
--breakpoint-lg: 1024px;  /* Desktop */
--breakpoint-xl: 1280px;  /* Large desktop */
```

### 6.2 Mobile Adaptations

| Desktop Pattern | Mobile Adaptation |
|-----------------|-------------------|
| Multi-column table | Card list or horizontal scroll |
| Sidebar navigation | Bottom nav or hamburger menu |
| Form columns | Single column stack |
| Modal | Full-screen sheet |

---

## 7. Accessibility

### 7.1 Keyboard Navigation (REQUIRED)

- All interactive elements focusable (Tab)
- Logical focus order (top-left to bottom-right)
- Visible focus indicator
- Escape closes modals/dropdowns
- Enter activates buttons/links

### 7.2 ARIA Labels (REQUIRED)

```tsx
// Icon buttons MUST have labels
<Button aria-label="Delete item">
  <TrashIcon />
</Button>

// Form inputs MUST have labels
<label htmlFor="email">Email</label>
<input id="email" type="email" />
```

### 7.3 Color Contrast

- Text: minimum 4.5:1 contrast ratio
- Large text (18px+): minimum 3:1
- Interactive elements: visible in all states
- Don't rely on color alone (add icons/text)

---

## 8. Notifications

### 8.1 Toast Messages

| Type | Duration | Use Case |
|------|----------|----------|
| Success | 3 seconds | Save, create, delete complete |
| Error | Until dismissed | Operation failed |
| Warning | 5 seconds | Non-blocking issue |
| Info | 4 seconds | Helpful information |

**Position:** Top-right, stacked
**Max visible:** 3 at a time

### 8.2 Inline Alerts

For persistent messages within the page:
- Info (blue): Helpful context
- Warning (yellow): Attention needed
- Error (red): Problem to fix
- Success (green): Positive confirmation

---

## Quick Reference Checklist

Before shipping any UI:

- [ ] Tables have pagination (default 20)
- [ ] Tables have sorting on relevant columns
- [ ] Tables have at least one filter
- [ ] All async operations show loading state
- [ ] Empty states have helpful message + action
- [ ] Error states have retry option
- [ ] Destructive actions have confirmation
- [ ] Forms validate on blur and submit
- [ ] All buttons have loading/disabled states
- [ ] Keyboard navigation works
- [ ] ARIA labels on icon buttons
- [ ] Mobile responsive

---

## 9. Material UI (MUI) Standards

### 9.1 MCP Server (REQUIRED for MUI Projects)

Install the official MUI MCP for accurate, up-to-date documentation:
```bash
claude mcp add mui-mcp -- npx -y @mui/mcp@latest
```

### 9.2 Styling Approach

**Use sx prop for most cases:**
```tsx
// Preferred: sx prop with theme values
<Box sx={{
  p: 2,                    // theme.spacing(2)
  mt: 3,                   // margin-top
  bgcolor: 'primary.main', // theme color
  borderRadius: 1          // theme shape
}}>

// For transparency
<Box sx={{ bgcolor: alpha(theme.palette.primary.main, 0.1) }}>
```

**When to use alternatives:**
- `sx prop`: Single-use styling, quick customization (most common)
- `styled()`: Reusable styled components, complex conditional styles
- `useTheme()`: When you need theme values in logic

**Avoid:**
- Inline `style={}` props (no theme access)
- Mixing approaches in same component

### 9.3 Component Best Practices

**Imports:**
```tsx
// Prefer individual imports (better tree-shaking)
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';

// NOT
import { Box, Button } from '@mui/material';
```

**Theme Spacing:**
```tsx
// Always use theme.spacing() or shorthand
sx={{ m: 2 }}      // margin: theme.spacing(2) = 16px
sx={{ p: 3 }}      // padding: theme.spacing(3) = 24px
sx={{ gap: 2 }}    // gap between flex items

// Never hardcode pixels for spacing
sx={{ margin: '16px' }}  // Bad - not theme-aware
```

**Responsive Values:**
```tsx
<Box sx={{
  width: { xs: '100%', sm: '50%', md: '33%' },
  p: { xs: 1, md: 2 }
}}>
```

### 9.4 Common Pitfalls to Avoid

| Pitfall | Solution |
|---------|----------|
| Mixing sx, styled, and makeStyles | Pick one approach per component |
| Hardcoded colors | Use theme palette: `color: 'text.secondary'` |
| Hardcoded spacing | Use theme spacing: `p: 2` not `padding: '16px'` |
| Missing ARIA labels | Add `aria-label` to icon buttons |
| Over-customizing standard components | Use theme overrides instead |
| Ignoring MUI's responsive system | Use breakpoint object syntax |

### 9.5 Prompt Engineering for MUI

When working with AI on MUI code:

1. **Be specific about components:**
   ```
   Create a MUI DataGrid with sorting, filtering, and pagination for a user list
   ```

2. **Reference design system:**
   ```
   Use theme.spacing() for margins, alpha() for transparency, sx prop for styling
   ```

3. **Request accessibility:**
   ```
   Include ARIA labels and keyboard navigation
   ```

4. **Specify responsive behavior:**
   ```
   Mobile-first with breakpoints: xs, sm, md, lg, xl
   ```

---

## Related Documents

- DEVELOPMENT_STANDARDS.md - Coding conventions
- API_STANDARDS.md - Backend patterns
- ARCHITECTURE.md (per project) - System design
- MUI_MCP_RESEARCH_2025-12-12.md - Full MCP research

---

**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-07 | Initial version |
| 1.1 | 2025-12-12 | Added Section 9: Material UI (MUI) Standards |

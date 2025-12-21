---
description: 'Playwright E2E testing guidelines'
applyTo: '**/*.spec.ts,**/tests/**/*.ts,**/e2e/**/*.ts'
source: 'github.com/github/awesome-copilot (adapted)'
---

# Playwright Test Guidelines

## Locator Strategy (Priority Order)

1. `getByRole()` - Best for accessibility (buttons, links, headings)
2. `getByLabel()` - Form inputs with labels
3. `getByText()` - Visible text content
4. `getByTestId()` - Last resort, data-testid attributes

**Avoid:**
- CSS selectors like `.class` or `#id`
- XPath expressions
- Fragile selectors that break on UI changes

## Assertions

- Use auto-retrying assertions with `await`
- Don't assert visibility unless testing visibility changes
- Prefer specific assertions over generic ones:

```typescript
// Good
await expect(page.getByRole('button', { name: 'Submit' })).toBeEnabled();

// Avoid
await expect(page.locator('.btn-submit')).toBeVisible();
```

## Auto-Waiting

- Rely on Playwright's built-in waiting
- Never use `page.waitForTimeout()` for synchronization
- Use `waitForLoadState()` only when necessary

## Test Structure

- Store tests in `tests/` directory
- Name files: `<feature>.spec.ts`
- Group related tests with `test.describe()`
- Use `beforeEach` for common setup (navigation, auth)

```typescript
test.describe('User Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should login with valid credentials', async ({ page }) => {
    // test implementation
  });
});
```

## Page Object Pattern

- Create page objects for complex pages
- Keep selectors in page objects, not tests
- Methods should represent user actions

## Snapshot Testing

- Use `toMatchAriaSnapshot` for accessibility tree verification
- Update snapshots intentionally, review changes
- Store snapshots in version control

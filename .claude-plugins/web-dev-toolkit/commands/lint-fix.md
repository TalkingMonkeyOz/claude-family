---
description: Run ESLint with automatic fixes
---

# Lint and Fix Code

Runs ESLint across the project and automatically fixes fixable issues.

## Steps

1. Check which package manager is installed:
   - Look for `pnpm-lock.yaml` → use `pnpm`
   - Look for `yarn.lock` → use `yarn`
   - Look for `package-lock.json` → use `npm`
   - Default to `npm` if none found

2. Run ESLint with fix flag:
   ```bash
   # pnpm
   pnpm lint --fix
   
   # yarn
   yarn lint --fix
   
   # npm
   npm run lint -- --fix
   ```

3. Check if ESLint is not configured as a script:
   - Fallback: `npx eslint . --fix`

4. Report results:
   - Number of files checked
   - Number of issues fixed
   - Remaining unfixable issues (with file locations)
   - Rules that were applied

## Notes

- Some issues cannot be auto-fixed and require manual review
- Common unfixable issues: unused variables, naming conventions, TODO comments
- Look for `.eslintrc` or `eslint.config.js` for configuration
- TypeScript ESLint is commonly used: `@typescript-eslint/eslint-plugin`
- Changes are applied directly to files

## Success Indicators

- Exit code 0 = all checks passed
- Exit code 1 = issues found/fixed or configuration issues

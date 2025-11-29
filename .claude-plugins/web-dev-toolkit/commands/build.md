---
description: Build the Next.js application
---

# Build Project

Detects the package manager and builds the project, then categorizes any errors that occur.

## Steps

1. Check which package manager is installed:
   - Look for `pnpm-lock.yaml` → use `pnpm`
   - Look for `yarn.lock` → use `yarn`
   - Look for `package-lock.json` → use `npm`
   - Default to `npm` if none found

2. Run the build command:
   ```bash
   # pnpm
   pnpm build
   
   # yarn
   yarn build
   
   # npm
   npm run build
   ```

3. Analyze the output and categorize errors:
   - **TypeScript errors** (TS prefix)
   - **ESLint warnings/errors** (eslint)
   - **Build warnings** (warning)
   - **Runtime errors** (error, cannot find module, etc.)

4. Report results to user with:
   - Build status (success/failure)
   - Error count by category
   - Recommended fixes

## Notes

- Build typically takes 30-60 seconds for medium-sized projects
- Check that `package.json` has a `build` script defined
- Exit code 0 = success, non-zero = failure

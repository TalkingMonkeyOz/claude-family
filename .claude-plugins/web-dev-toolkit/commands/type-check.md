---
description: Run TypeScript type checking without emitting files
---

# Type Check

Runs TypeScript compiler to check for type errors without generating output files.

## Steps

1. Check which package manager is installed:
   - Look for `pnpm-lock.yaml` → use `pnpm`
   - Look for `yarn.lock` → use `yarn`
   - Look for `package-lock.json` → use `npm`
   - Default to `npm` if none found

2. Run TypeScript type checker:
   ```bash
   # Direct command (preferred)
   npx tsc --noEmit
   
   # Or via package manager if tsc is installed
   pnpm tsc --noEmit
   yarn tsc --noEmit
   npm exec tsc -- --noEmit
   ```

3. Parse the output for errors:
   - Extract file paths and error messages
   - Organize by error type:
     - Type mismatches
     - Missing properties
     - Incorrect assignments
     - Module resolution errors

4. Report results:
   - Total error count
   - Errors grouped by file
   - Error descriptions with line numbers
   - Summary of most common error types

## Notes

- `--noEmit` flag prevents creating `.js` files
- Type checking is fast (usually < 10 seconds)
- Check `tsconfig.json` for TypeScript configuration
- Common configurations: strict mode, lib versions, module resolution
- Exit code 0 = no type errors, non-zero = errors found

## Success Indicators

- No output = success (or message: "No type errors!")
- All errors listed with locations and descriptions
- Type checking completes without hanging

---
description: Run the project test suite
---

# Run Tests

Executes the test suite for the project using Jest, Vitest, or other configured test runner.

## Steps

1. Check which package manager is installed:
   - Look for `pnpm-lock.yaml` → use `pnpm`
   - Look for `yarn.lock` → use `yarn`
   - Look for `package-lock.json` → use `npm`
   - Default to `npm` if none found

2. Detect test runner:
   - Check `package.json` for test script
   - Look for `jest.config.js` → Jest
   - Look for `vitest.config.ts` → Vitest
   - Check for `playwright.config.ts` → Playwright (E2E)
   - Default to `npm test`

3. Run the test command:
   ```bash
   # npm
   npm test
   
   # pnpm
   pnpm test
   
   # yarn
   yarn test
   ```

4. Wait for tests to complete (may take 30-120 seconds)

5. Parse and report results:
   - Total tests run
   - Passed/Failed/Skipped counts
   - Failed test names and reasons
   - Code coverage if available
   - Execution time

## Notes

- Tests may run in watch mode by default (press 'q' to quit)
- Some test runners support running specific test files
- Coverage reports typically appear in `coverage/` directory
- Failed tests should show assertion errors
- Check `package.json` for test-related scripts (test, test:watch, test:coverage)

## Success Indicators

- All tests pass (exit code 0)
- Clear pass/fail summary
- No hanging or timeout issues
- Error messages are clear and actionable

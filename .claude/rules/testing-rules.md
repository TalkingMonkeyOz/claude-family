# Testing Rules

## When to Test

- After modifying 3+ code files
- Before committing feature work
- After fixing bugs (regression test)

## Test Patterns

### Python
```bash
pytest path/to/tests -v
```

### JavaScript/TypeScript
```bash
npm test
# or
npx jest
```

### C#
```bash
dotnet test
```

## Coverage Expectations

- New features: Add tests for happy path + edge cases
- Bug fixes: Add test that would have caught the bug
- Refactoring: Ensure existing tests still pass

## Stop Hook Reminder

The stop hook will remind you to test after modifying 3+ code files.

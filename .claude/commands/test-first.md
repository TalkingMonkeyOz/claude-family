# Test-First Development Mode

You are now in TDD (Test-Driven Development) mode for: $ARGUMENTS

## MANDATORY STEPS

### Step 1: Write Tests FIRST
Before writing ANY implementation code:
- Create test file in appropriate location
- Write tests for:
  - [ ] Happy path (valid inputs)
  - [ ] Edge cases (nulls, empty, boundaries)
  - [ ] Error cases (invalid inputs, failures)
  - [ ] Integration points (if applicable)

### Step 2: Run Tests - Confirm Failure
- Execute the test suite
- VERIFY tests fail (they should - no implementation yet)
- If tests pass, they're not testing the new functionality

### Step 3: Write Minimal Implementation
- Write ONLY enough code to make tests pass
- No extra features
- No premature optimization
- No "nice to haves"

### Step 4: Run Tests - Confirm Pass
- Execute the test suite again
- ALL tests must pass
- If any fail, fix implementation (not tests)

### Step 5: Refactor (Optional)
- Clean up code while keeping tests green
- Extract common patterns
- Improve readability
- Run tests after each change

## Test Patterns by Type

### Unit Test (Function/Class)
```typescript
describe('functionName', () => {
  it('should handle valid input', () => {});
  it('should throw on null input', () => {});
  it('should return default for empty', () => {});
});
```

### API Test (Endpoint)
```typescript
describe('POST /api/endpoint', () => {
  it('should return 200 with valid body', () => {});
  it('should return 400 with missing fields', () => {});
  it('should return 401 without auth', () => {});
});
```

### Component Test (React)
```typescript
describe('ComponentName', () => {
  it('should render correctly', () => {});
  it('should handle click events', () => {});
  it('should show loading state', () => {});
  it('should show error state', () => {});
});
```

## Remember
- Tests are documentation
- Tests prevent regression
- Tests enable refactoring
- Write tests YOU would want to maintain

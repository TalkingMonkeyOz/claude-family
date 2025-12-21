---
description: 'Guidelines for building C# applications'
applyTo: '**/*.cs'
source: 'github.com/github/awesome-copilot (adapted)'
---

# C# Development Guidelines

## C# Instructions
- Use modern C# features (C# 12+, .NET 8+)
- Write clear and concise comments for complex logic only
- Prefer expression-bodied members for simple methods

## Naming Conventions

- PascalCase for: classes, methods, properties, public members
- camelCase for: private fields, local variables, parameters
- Prefix interfaces with "I" (e.g., IUserService)
- Prefix private fields with underscore: `_privateField`

## Formatting

- Apply code-formatting style defined in `.editorconfig` if present
- Prefer file-scoped namespace declarations
- Use pattern matching and switch expressions where appropriate
- Use `nameof` instead of string literals for member names
- Ensure XML doc comments for public APIs

## Nullable Reference Types

- Declare variables non-nullable by default
- Use `is null` or `is not null` instead of `== null`
- Trust C# null annotations - don't add redundant null checks

## Error Handling

- Use specific exception types, not generic Exception
- Include meaningful error messages
- Never swallow exceptions silently
- Use try-catch at boundary points, not everywhere

## Async Patterns

- Suffix async methods with `Async`
- Use `ConfigureAwait(false)` in library code
- Prefer `ValueTask` for hot paths that often complete synchronously
- Always await or return tasks - never fire-and-forget without reason

## Testing

- Do not emit "Arrange", "Act", or "Assert" comments
- Copy existing style in nearby files for test method names
- Use meaningful test names that describe the scenario
- Mock external dependencies, not internal implementation

## Performance

- Use `StringBuilder` for string concatenation in loops
- Prefer `Span<T>` and `Memory<T>` for buffer operations
- Use `IAsyncEnumerable` for streaming large datasets
- Avoid allocations in hot paths

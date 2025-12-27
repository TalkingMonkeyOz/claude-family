---
synced: true
synced_at: '2025-12-21T14:40:40.014080'
tags:
- domain-knowledge
- csharp
projects: []
---

# C# Expert Rules

**Category**: csharp
**Tags**: #csharp #dotnet #solid #best-practices

---

## Core Principles

- Write **clean, secure, readable, maintainable** code
- Follow **.NET conventions** and **SOLID principles**
- Apply **least-exposure principle**: `private` > `internal` > `protected` > `public`
- Comments explain **reasoning**, not implementation details
- **Don't edit auto-generated code**

---

## Design Patterns to Apply

| Pattern | When to Use |
|---------|-------------|
| Async/Await | All I/O operations |
| Dependency Injection | External dependencies, testability |
| Unit of Work | Database transactions |
| CQRS | Complex domain logic |

---

## Error Handling

```csharp
// Null validation
ArgumentNullException.ThrowIfNull(customer);
ArgumentException.ThrowIfNullOrEmpty(name);

// Use precise exception types
throw new InvalidOperationException("Cannot process empty order");

// Never silently swallow
catch (Exception ex)
{
    _logger.LogError(ex, "Failed to process order {OrderId}", orderId);
    throw; // Rethrow to preserve stack
}
```

---

## Async Programming

```csharp
// All async methods end with Async
public async Task<Customer> GetCustomerAsync(int id, CancellationToken ct)
{
    // Pass CancellationToken through
    return await _repository.FindAsync(id, ct);
}

// Library code
await SomeOperationAsync().ConfigureAwait(false);

// AVOID fire-and-forget
// BAD: DoSomethingAsync(); // No await!
```

---

## Modern C# Features

### Prefer

```csharp
// File-scoped namespaces
namespace MyApp.Services;

// Raw strings for multi-line
var json = """
    {
        "name": "value"
    }
    """;

// Switch expressions
var result = status switch
{
    Status.Active => "Running",
    Status.Paused => "Waiting",
    _ => "Unknown"
};

// Records for DTOs
public record CustomerDto(string Name, string Email);

// Target-typed new
Button button = new();

// Pattern matching
if (sender is Button { Name: "btnSave" } btn)
{
    // Use btn
}
```

### Performance-Critical Paths

```csharp
// Use Span<T> for slicing without allocation
ReadOnlySpan<char> slice = text.AsSpan(0, 10);

// Use Memory<T> for async scenarios
Memory<byte> buffer = new byte[1024];
```

---

## Property Patterns

```csharp
// WRONG - creates new instance per access (memory leak)
public List<Item> Items => new List<Item>();

// CORRECT - cached instance
public List<Item> Items { get; } = new();

// Computed value
public string FullName => $"{FirstName} {LastName}";

// Lazy with fallback
public string DisplayName => _displayName ?? Name;
```

---

## Interface Usage

Use interfaces **only** for:
- External dependencies (repositories, services)
- Testing/mocking requirements
- Genuine polymorphism needs

**Avoid** unnecessary abstractions - not every class needs an interface.

---

## Testing (Arrange-Act-Assert)

```csharp
[Fact]
public async Task GetCustomer_WithValidId_ReturnsCustomer()
{
    // Arrange
    var repository = new Mock<ICustomerRepository>();
    repository.Setup(r => r.FindAsync(1, default))
        .ReturnsAsync(new Customer { Id = 1, Name = "John" });

    var service = new CustomerService(repository.Object);

    // Act
    var result = await service.GetCustomerAsync(1);

    // Assert
    Assert.NotNull(result);
    Assert.Equal("John", result.Name);
}
```

### Testing Guidelines

- One behavior per test
- Test public APIs only
- Don't change visibility for testing
- Mirror class names: `CustomerService` → `CustomerServiceTests`

---

**Version**: 1.0
**Source**: GitHub awesome-copilot CSharpExpert.agent.md
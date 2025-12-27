---
tags: []
projects: []
---
# C# Data Access: Entity Framework Core vs Dapper
## Decision Guide for Personal Finance App

**Date:** 26 December 2025  
**Purpose:** Help choose between EF Core and Dapper for PostgreSQL access

---

## Quick Summary

| Factor | Entity Framework Core | Dapper |
|--------|----------------------|--------|
| **Learning Curve** | Steeper | Easier |
| **Code Volume** | Less (auto-generated) | More (manual SQL) |
| **Performance** | Good (slightly slower) | Excellent (minimal overhead) |
| **Control** | Less (ORM abstracts SQL) | Full (you write SQL) |
| **Best For** | Rapid development, CRUD-heavy | Performance-critical, complex queries |
| **Recommendation** | âœ… **Start here** | Switch later if needed |

---

## What They Are

### Entity Framework Core (EF Core)
**An Object-Relational Mapper (ORM)** - translates C# objects to/from database tables automatically.

**Example:**
```csharp
// You write this (no SQL):
var accounts = await context.Accounts
    .Where(a => a.IsActive)
    .Include(a => a.Transactions)
    .ToListAsync();

// EF Core generates this SQL:
// SELECT * FROM accounts WHERE is_active = true
// SELECT * FROM transactions WHERE account_id IN (...)
```

**Pros:**
- âœ… Write less code (no manual SQL)
- âœ… Type-safe (catches errors at compile time)
- âœ… Handles relationships automatically (joins, foreign keys)
- âœ… Migrations built-in (schema versioning)
- âœ… Change tracking (knows what changed, updates only that)

**Cons:**
- âŒ Can generate inefficient SQL if not careful
- âŒ More "magic" (harder to debug sometimes)
- âŒ Slightly slower than raw SQL
- âŒ Bigger learning curve

### Dapper
**A "micro-ORM"** - you write SQL, it maps results to C# objects.

**Example:**
```csharp
// You write this (manual SQL):
var accounts = await connection.QueryAsync<Account>(
    @"SELECT * FROM accounts 
      WHERE is_active = @IsActive",
    new { IsActive = true }
);

// Dapper executes your exact SQL
```

**Pros:**
- âœ… Full control over SQL (optimize every query)
- âœ… Minimal overhead (very fast)
- âœ… Easy to learn (if you know SQL)
- âœ… Works great with complex queries

**Cons:**
- âŒ More code (write every SQL statement)
- âŒ No automatic migrations (manage schema separately)
- âŒ No change tracking (you handle updates manually)
- âŒ SQL strings can have typos (not type-checked)

---

## Detailed Comparison

### 1. Code Examples (Same Task)

**Task:** Get all transactions for an account in December 2025

#### Entity Framework Core
```csharp
public async Task<List<Transaction>> GetDecemberTransactions(int accountId)
{
    return await _context.Transactions
        .Where(t => t.AccountId == accountId)
        .Where(t => t.TransactionDate >= new DateTime(2025, 12, 1))
        .Where(t => t.TransactionDate < new DateTime(2026, 1, 1))
        .Include(t => t.Category)
        .OrderByDescending(t => t.TransactionDate)
        .ToListAsync();
}

// EF Core generates SQL automatically
// Handles joins, parameters, mapping
```

#### Dapper
```csharp
public async Task<List<Transaction>> GetDecemberTransactions(int accountId)
{
    var sql = @"
        SELECT t.*, c.name as CategoryName
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.account_id = @AccountId
          AND t.transaction_date >= @StartDate
          AND t.transaction_date < @EndDate
        ORDER BY t.transaction_date DESC";
    
    return (await _connection.QueryAsync<Transaction>(sql, new {
        AccountId = accountId,
        StartDate = new DateTime(2025, 12, 1),
        EndDate = new DateTime(2026, 1, 1)
    })).ToList();
}

// You write SQL explicitly
// Full control over query performance
```

### 2. Setup Complexity

#### Entity Framework Core Setup
```csharp
// 1. Install package
// dotnet add package Npgsql.EntityFrameworkCore.PostgreSQL

// 2. Define models (classes match tables)
public class Account
{
    public int Id { get; set; }
    public string Name { get; set; }
    public decimal Balance { get; set; }
    public List<Transaction> Transactions { get; set; } // EF tracks relationships
}

// 3. Create DbContext (main interface)
public class AppDbContext : DbContext
{
    public DbSet<Account> Accounts { get; set; }
    public DbSet<Transaction> Transactions { get; set; }
    
    protected override void OnConfiguring(DbContextOptionsBuilder options)
    {
        options.UseNpgsql("Host=localhost;Database=personal_finance;");
    }
}

// 4. Use it
using var context = new AppDbContext();
var accounts = await context.Accounts.ToListAsync();
```

#### Dapper Setup
```csharp
// 1. Install package
// dotnet add package Dapper
// dotnet add package Npgsql

// 2. Define models (simple POCOs)
public class Account
{
    public int Id { get; set; }
    public string Name { get; set; }
    public decimal Balance { get; set; }
    // No navigation properties
}

// 3. Create connection
using var connection = new NpgsqlConnection("Host=localhost;Database=personal_finance;");
await connection.OpenAsync();

// 4. Use it
var accounts = await connection.QueryAsync<Account>("SELECT * FROM accounts");
```

**Winner for Setup:** Dapper (simpler, less boilerplate)

### 3. Migrations (Schema Changes)

#### Entity Framework Core
```csharp
// EF Core tracks schema changes automatically

// 1. Change your model
public class Account
{
    public int Id { get; set; }
    public string Name { get; set; }
    public string AccountNumber { get; set; } // NEW FIELD
}

// 2. Generate migration
// dotnet ef migrations add AddAccountNumber

// 3. Apply to database
// dotnet ef database update

// EF Core creates this SQL:
// ALTER TABLE accounts ADD COLUMN account_number VARCHAR(50);
```

#### Dapper
```csharp
// Dapper doesn't handle migrations - you do it manually

// 1. Write SQL migration file
// migrations/002_add_account_number.sql:
ALTER TABLE accounts ADD COLUMN account_number VARCHAR(50);

// 2. Run migration (using tool like Flyway, or manually)
psql -d personal_finance -f migrations/002_add_account_number.sql

// 3. Update your model
public class Account
{
    public int Id { get; set; }
    public string Name { get; set; }
    public string AccountNumber { get; set; }
}
```

**Winner for Migrations:** EF Core (automatic schema versioning)

### 4. Performance

**Simple Query (100 records):**
- EF Core: ~5ms
- Dapper: ~3ms
- **Difference:** Negligible

**Complex Query (1000s of records, joins):**
- EF Core: ~50ms (if optimized)
- Dapper: ~30ms
- **Difference:** Noticeable

**Recommendation:** EF Core is fast enough for 99% of personal finance queries. Only switch to Dapper if you have proven performance issues.

### 5. Relationship Handling

#### Entity Framework Core
```csharp
// EF handles relationships automatically
var account = await context.Accounts
    .Include(a => a.Transactions)        // Join
    .ThenInclude(t => t.Category)        // Nested join
    .FirstOrDefaultAsync(a => a.Id == 1);

// Access related data easily
foreach (var transaction in account.Transactions)
{
    Console.WriteLine($"{transaction.Category.Name}: ${transaction.Amount}");
}

// EF tracks changes
account.Balance += 100;
await context.SaveChangesAsync(); // Updates DB automatically
```

#### Dapper
```csharp
// Dapper requires manual mapping for relationships
var accountDict = new Dictionary<int, Account>();

var sql = @"
    SELECT a.*, t.*, c.*
    FROM accounts a
    LEFT JOIN transactions t ON a.id = t.account_id
    LEFT JOIN categories c ON t.category_id = c.id
    WHERE a.id = @Id";

await connection.QueryAsync<Account, Transaction, Category, Account>(
    sql,
    (account, transaction, category) => {
        if (!accountDict.ContainsKey(account.Id))
            accountDict.Add(account.Id, account);
        
        var currentAccount = accountDict[account.Id];
        if (transaction != null)
        {
            transaction.Category = category;
            currentAccount.Transactions.Add(transaction);
        }
        return currentAccount;
    },
    new { Id = 1 }
);

var account = accountDict.Values.FirstOrDefault();

// Manual updates
await connection.ExecuteAsync(
    "UPDATE accounts SET balance = @Balance WHERE id = @Id",
    new { Balance = account.Balance + 100, Id = account.Id }
);
```

**Winner for Relationships:** EF Core (much simpler)

---

## Recommendation for Personal Finance App

### Use **Entity Framework Core** because:

1. **Faster Development** - You'll spend less time writing CRUD operations
2. **Built-in Migrations** - Schema changes are tracked and versioned
3. **Relationship Management** - Accounts → Transactions → Categories handled automatically
4. **Type Safety** - Compiler catches errors before runtime
5. **Good Enough Performance** - Personal finance app isn't processing millions of transactions

### When to Consider Switching to Dapper:

- Performance issues with specific queries (rare)
- Need highly optimized reporting queries
- Want more control over complex SQL

### Hybrid Approach (Best of Both):

Many apps use **both**:
- **EF Core** for standard CRUD (accounts, transactions, categories)
- **Dapper** for complex reporting queries (net worth calculations, spending analytics)

```csharp
// Example: Use both in same app
public class FinanceService
{
    private readonly AppDbContext _context; // EF Core
    private readonly NpgsqlConnection _connection; // Dapper
    
    // Simple CRUD - use EF Core
    public async Task<Account> CreateAccount(Account account)
    {
        _context.Accounts.Add(account);
        await _context.SaveChangesAsync();
        return account;
    }
    
    // Complex reporting - use Dapper
    public async Task<MonthlySpendingReport> GetSpendingReport(int month)
    {
        var sql = @"
            WITH category_totals AS (
                SELECT category_id, SUM(amount) as total
                FROM transactions
                WHERE EXTRACT(MONTH FROM transaction_date) = @Month
                GROUP BY category_id
            )
            SELECT c.name, ct.total, 
                   RANK() OVER (ORDER BY ct.total DESC) as rank
            FROM category_totals ct
            JOIN categories c ON ct.category_id = c.id";
        
        return await _connection.QueryFirstAsync<MonthlySpendingReport>(
            sql, new { Month = month }
        );
    }
}
```

---

## Learning Resources

### Entity Framework Core
- **Official Docs:** https://learn.microsoft.com/ef/core/
- **Tutorial:** "Getting Started with EF Core" (Microsoft Learn)
- **Time to Learn:** 2-3 days for basics, 1-2 weeks to be productive

### Dapper
- **Official Docs:** https://github.com/DapperLib/Dapper
- **Tutorial:** "Dapper Tutorial" (dapper-tutorial.net)
- **Time to Learn:** 1 day if you know SQL well

---

## Final Recommendation

**Start with Entity Framework Core:**
1. Install: `dotnet add package Npgsql.EntityFrameworkCore.PostgreSQL`
2. Create models (Account, Transaction, Category)
3. Create DbContext
4. Use migrations for schema management
5. Build app quickly

**Add Dapper later** if you need it for specific performance-critical queries.

**Don't overthink it** - EF Core is the right choice for 95% of scenarios, especially when starting out.

---

**Decision:** âœ… **Entity Framework Core**  
**Reasoning:** Faster development, easier maintenance, good enough performance  
**Fallback:** Can always add Dapper for specific queries later

---

*End of ORM Comparison Document*
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: John's Notes/Personal Finance Orig/ORM_COMPARISON.md

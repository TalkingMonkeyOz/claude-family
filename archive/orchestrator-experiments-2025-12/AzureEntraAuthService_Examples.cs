using System;
using System.Collections.Generic;
using System.Data;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.SqlClient;
using NimbusUserLoader.Services;

namespace NimbusUserLoader.Examples
{
    /// <summary>
    /// Practical examples of using AzureEntraAuthService for authentication and SQL access.
    /// </summary>

    // ============================================================================
    // EXAMPLE 1: Simple Console Authentication
    // ============================================================================

    public class SimpleConsoleExample
    {
        public static async Task RunAsync()
        {
            var authService = new AzureEntraAuthService();
            var progress = new ConsoleAuthenticationProgress();

            try
            {
                // Authenticate
                var accessToken = await authService.AuthenticateAsync(progress);

                // Use token
                var connectionString = "Server=myserver.database.windows.net;Database=mydb;";
                using var connection = AzureEntraAuthService.CreateSqlConnection(
                    connectionString, accessToken);

                await connection.OpenAsync();
                Console.WriteLine($"✓ Connected to SQL Server as: {connection.Database}");

                // Query example
                using var command = connection.CreateCommand();
                command.CommandText = "SELECT COUNT(*) FROM Users";
                var count = (int)await command.ExecuteScalarAsync();
                Console.WriteLine($"✓ User count: {count}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"✗ Error: {ex.Message}");
            }
        }
    }

    // ============================================================================
    // EXAMPLE 2: WPF Integration with Custom Progress Reporting
    // ============================================================================

    public class WpfAuthenticationProgress : AzureEntraAuthService.IAuthenticationProgress
    {
        private readonly Action<string> _updateStatus;
        private readonly Action<string> _setUserCode;
        private readonly Action<string> _setVerificationUri;
        private readonly Action<bool> _setProgressIndeterminate;

        public WpfAuthenticationProgress(
            Action<string> updateStatus,
            Action<string> setUserCode,
            Action<string> setVerificationUri,
            Action<bool> setProgressIndeterminate)
        {
            _updateStatus = updateStatus;
            _setUserCode = setUserCode;
            _setVerificationUri = setVerificationUri;
            _setProgressIndeterminate = setProgressIndeterminate;
        }

        public void ReportDeviceCode(string userCode, string verificationUri)
        {
            _setUserCode($"Code: {userCode}");
            _setVerificationUri($"URL: {verificationUri}");
            _updateStatus("Opening browser for sign-in...");
            _setProgressIndeterminate(true);

            // Open browser (or let user click link)
            try
            {
                System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                {
                    FileName = verificationUri,
                    UseShellExecute = true
                });
            }
            catch
            {
                _updateStatus($"Please visit: {verificationUri}");
            }
        }

        public void ReportPollingStarted()
        {
            _updateStatus("Waiting for sign-in to complete...");
        }

        public void ReportPollingProgress(int secondsElapsed)
        {
            if (secondsElapsed % 5 == 0)
            {
                _updateStatus($"Waiting for sign-in... ({secondsElapsed}s)");
            }
        }

        public void ReportAuthenticationComplete()
        {
            _updateStatus("✓ Authentication successful!");
            _setProgressIndeterminate(false);
        }

        public void ReportError(string errorMessage)
        {
            _updateStatus($"✗ Error: {errorMessage}");
            _setProgressIndeterminate(false);
        }
    }

    public class WpfExample
    {
        // This would be in your WPF ViewModel
        public async Task AuthenticateAndConnectAsync()
        {
            var authService = new AzureEntraAuthService();

            var progress = new WpfAuthenticationProgress(
                updateStatus: status => Console.WriteLine(status),
                setUserCode: code => Console.WriteLine(code),
                setVerificationUri: uri => Console.WriteLine(uri),
                setProgressIndeterminate: flag => Console.WriteLine($"Indeterminate: {flag}")
            );

            try
            {
                var accessToken = await authService.AuthenticateAsync(progress);
                // Token is now available for SQL operations
            }
            catch (TimeoutException)
            {
                Console.WriteLine("Authentication timed out");
            }
            catch (OperationCanceledException)
            {
                Console.WriteLine("Authentication was cancelled");
            }
        }
    }

    // ============================================================================
    // EXAMPLE 3: Cached Token Management
    // ============================================================================

    public class CachedTokenManager
    {
        private readonly AzureEntraAuthService _authService;
        private string _cachedAccessToken;
        private DateTime _tokenExpiryTime;
        private readonly TimeSpan _refreshThreshold = TimeSpan.FromMinutes(5);

        public CachedTokenManager(string tenantId = "common")
        {
            _authService = new AzureEntraAuthService(tenantId);
            _tokenExpiryTime = DateTime.MinValue;
        }

        public async Task<string> GetValidAccessTokenAsync(
            AzureEntraAuthService.IAuthenticationProgress progress = null,
            CancellationToken cancellationToken = default)
        {
            // Check if cached token is still valid
            if (_cachedAccessToken != null &&
                DateTime.UtcNow.AddSeconds(-30) < _tokenExpiryTime - _refreshThreshold)
            {
                return _cachedAccessToken;
            }

            // Need new token
            _cachedAccessToken = await _authService.AuthenticateAsync(progress, cancellationToken);

            // Azure tokens typically last 1 hour
            _tokenExpiryTime = DateTime.UtcNow.AddHours(1);

            return _cachedAccessToken;
        }

        public void InvalidateToken()
        {
            _cachedAccessToken = null;
            _tokenExpiryTime = DateTime.MinValue;
        }
    }

    public class CachedTokenExample
    {
        public static async Task RunAsync()
        {
            var tokenManager = new CachedTokenManager();
            var connectionString = "Server=myserver.database.windows.net;Database=mydb;";

            // First call - authenticates
            Console.WriteLine("First call - authenticating...");
            var token1 = await tokenManager.GetValidAccessTokenAsync();

            // Second call - uses cached token
            Console.WriteLine("Second call - using cached token...");
            var token2 = await tokenManager.GetValidAccessTokenAsync();

            Console.WriteLine($"Same token: {token1 == token2}");

            // Use token for SQL
            using var connection = AzureEntraAuthService.CreateSqlConnection(
                connectionString, token1);
            await connection.OpenAsync();
        }
    }

    // ============================================================================
    // EXAMPLE 4: Retry Logic with Transient Error Handling
    // ============================================================================

    public class SqlOperationWithRetry
    {
        private readonly CachedTokenManager _tokenManager;
        private readonly string _connectionString;
        private const int MaxRetries = 3;

        public SqlOperationWithRetry(string connectionString, string tenantId = "common")
        {
            _tokenManager = new CachedTokenManager(tenantId);
            _connectionString = connectionString;
        }

        /// <summary>
        /// Executes a SQL operation with retry logic for transient errors.
        /// </summary>
        public async Task<T> ExecuteWithRetryAsync<T>(
            Func<SqlConnection, Task<T>> operation,
            CancellationToken cancellationToken = default)
        {
            for (int attempt = 1; attempt <= MaxRetries; attempt++)
            {
                try
                {
                    var accessToken = await _tokenManager.GetValidAccessTokenAsync(
                        cancellationToken: cancellationToken);

                    using var connection = AzureEntraAuthService.CreateSqlConnection(
                        _connectionString, accessToken);

                    await connection.OpenAsync(cancellationToken);
                    return await operation(connection);
                }
                catch (SqlException ex) when (attempt < MaxRetries && IsTransientError(ex))
                {
                    Console.WriteLine($"Transient error on attempt {attempt}: {ex.Number}. Retrying...");

                    // Exponential backoff: 1s, 2s, 4s
                    var delayMs = (int)Math.Pow(2, attempt - 1) * 1000;
                    await Task.Delay(delayMs, cancellationToken);

                    continue;
                }
                catch (SqlException ex) when (IsAuthenticationError(ex))
                {
                    Console.WriteLine("Authentication error. Refreshing token...");
                    _tokenManager.InvalidateToken();

                    if (attempt < MaxRetries)
                    {
                        await Task.Delay(1000, cancellationToken);
                        continue;
                    }

                    throw;
                }
            }

            throw new InvalidOperationException(
                $"Operation failed after {MaxRetries} attempts");
        }

        public async Task ExecuteWithRetryAsync(
            Func<SqlConnection, Task> operation,
            CancellationToken cancellationToken = default)
        {
            await ExecuteWithRetryAsync(async conn =>
            {
                await operation(conn);
                return true;
            }, cancellationToken);
        }

        private static bool IsTransientError(SqlException ex)
        {
            // Transient SQL errors that should be retried
            return ex.Number switch
            {
                40613 => true,  // Database unavailable
                40501 => true,  // Service busy
                40197 => true,  // Error processing request
                64 => true,     // Connection initialization error
                233 => true,    // Connection timeout
                -2 => true,     // Timeout expired
                _ => false
            };
        }

        private static bool IsAuthenticationError(SqlException ex)
        {
            // Authentication-related errors
            return ex.Number switch
            {
                18456 => true,  // Login failed
                18488 => true,  // Login failed - MFA
                _ => false
            };
        }
    }

    public class RetryExample
    {
        public static async Task RunAsync()
        {
            var connectionString = "Server=myserver.database.windows.net;Database=mydb;";
            var sqlOps = new SqlOperationWithRetry(connectionString);

            // Execute a query with automatic retry
            var userCount = await sqlOps.ExecuteWithRetryAsync(async conn =>
            {
                using var cmd = conn.CreateCommand();
                cmd.CommandText = "SELECT COUNT(*) FROM Users";
                return (int)await cmd.ExecuteScalarAsync();
            });

            Console.WriteLine($"User count: {userCount}");

            // Execute a non-query operation with retry
            await sqlOps.ExecuteWithRetryAsync(async conn =>
            {
                using var cmd = conn.CreateCommand();
                cmd.CommandText = "UPDATE Users SET LastLogin = @now WHERE Id = @id";
                cmd.Parameters.AddWithValue("@now", DateTime.UtcNow);
                cmd.Parameters.AddWithValue("@id", 123);
                await cmd.ExecuteNonQueryAsync();
            });

            Console.WriteLine("✓ User updated");
        }
    }

    // ============================================================================
    // EXAMPLE 5: Bulk Operations with Connection Pooling
    // ============================================================================

    public class BulkDataLoader
    {
        private readonly CachedTokenManager _tokenManager;
        private readonly string _connectionString;

        public BulkDataLoader(string connectionString, string tenantId = "common")
        {
            _tokenManager = new CachedTokenManager(tenantId);
            _connectionString = connectionString;
        }

        public async Task<int> BulkInsertAsync<T>(
            string tableName,
            IEnumerable<T> data,
            Action<SqlBulkCopy, T> configureRow,
            CancellationToken cancellationToken = default)
        {
            var accessToken = await _tokenManager.GetValidAccessTokenAsync(
                cancellationToken: cancellationToken);

            using var connection = AzureEntraAuthService.CreateSqlConnection(
                _connectionString, accessToken);

            await connection.OpenAsync(cancellationToken);

            using var bulkCopy = new SqlBulkCopy(connection)
            {
                DestinationTableName = tableName,
                BulkCopyTimeout = 300
            };

            // Configuration would be done by caller
            // This is a simplified example

            return bulkCopy.RowsCopied;
        }
    }

    // ============================================================================
    // EXAMPLE 6: Async Enumeration of Query Results
    // ============================================================================

    public class DataReader
    {
        private readonly CachedTokenManager _tokenManager;
        private readonly string _connectionString;

        public DataReader(string connectionString, string tenantId = "common")
        {
            _tokenManager = new CachedTokenManager(tenantId);
            _connectionString = connectionString;
        }

        public async IAsyncEnumerable<T> QueryAsync<T>(
            string sql,
            Func<SqlDataReader, T> rowMapper,
            CancellationToken cancellationToken = default)
        {
            var accessToken = await _tokenManager.GetValidAccessTokenAsync(
                cancellationToken: cancellationToken);

            using var connection = AzureEntraAuthService.CreateSqlConnection(
                _connectionString, accessToken);

            await connection.OpenAsync(cancellationToken);

            using var command = connection.CreateCommand();
            command.CommandText = sql;

            using var reader = await command.ExecuteReaderAsync(
                CommandBehavior.SequentialAccess, cancellationToken);

            while (await reader.ReadAsync(cancellationToken))
            {
                yield return rowMapper(reader);
            }
        }
    }

    public class DataReaderExample
    {
        public class User
        {
            public int Id { get; set; }
            public string Name { get; set; }
            public string Email { get; set; }
        }

        public static async Task RunAsync()
        {
            var connectionString = "Server=myserver.database.windows.net;Database=mydb;";
            var reader = new DataReader(connectionString);

            var sql = "SELECT Id, Name, Email FROM Users WHERE Active = 1 ORDER BY Name";

            await foreach (var user in reader.QueryAsync(
                sql,
                r => new User
                {
                    Id = (int)r["Id"],
                    Name = (string)r["Name"],
                    Email = (string)r["Email"]
                }))
            {
                Console.WriteLine($"{user.Name} ({user.Email})");
            }
        }
    }

    // ============================================================================
    // EXAMPLE 7: Timeout and Cancellation Handling
    // ============================================================================

    public class TimeoutExample
    {
        public static async Task RunAsync()
        {
            var authService = new AzureEntraAuthService();
            var progress = new ConsoleAuthenticationProgress();

            // Create a timeout for authentication (5 minutes)
            using var cts = new CancellationTokenSource(TimeSpan.FromMinutes(5));

            try
            {
                var accessToken = await authService.AuthenticateAsync(
                    progress,
                    cts.Token);

                Console.WriteLine("✓ Authentication completed within timeout");
            }
            catch (OperationCanceledException)
            {
                Console.WriteLine("✗ Authentication cancelled due to timeout");
            }

            // Or cancel manually from elsewhere
            var cts2 = new CancellationTokenSource();

            _ = Task.Run(async () =>
            {
                await Task.Delay(TimeSpan.FromSeconds(30));
                cts2.Cancel(); // Cancel after 30 seconds
            });

            try
            {
                var accessToken = await authService.AuthenticateAsync(
                    progress,
                    cts2.Token);
            }
            catch (OperationCanceledException)
            {
                Console.WriteLine("✗ Authentication was cancelled by user");
            }
        }
    }

    // ============================================================================
    // EXAMPLE 8: Multi-Tenant Scenario
    // ============================================================================

    public class MultiTenantExample
    {
        private readonly Dictionary<string, CachedTokenManager> _tenantTokens;

        public MultiTenantExample()
        {
            _tenantTokens = new Dictionary<string, CachedTokenManager>();
        }

        public async Task<string> GetTokenForTenantAsync(string tenantId)
        {
            if (!_tenantTokens.ContainsKey(tenantId))
            {
                _tenantTokens[tenantId] = new CachedTokenManager(tenantId);
            }

            return await _tenantTokens[tenantId].GetValidAccessTokenAsync();
        }

        public async Task ExecuteAcrossTenantsAsync(
            Dictionary<string, string> tenantConnectionStrings,
            Func<SqlConnection, Task> operation)
        {
            var tasks = new List<Task>();

            foreach (var (tenantId, connString) in tenantConnectionStrings)
            {
                tasks.Add(Task.Run(async () =>
                {
                    var token = await GetTokenForTenantAsync(tenantId);
                    using var connection = AzureEntraAuthService.CreateSqlConnection(
                        connString, token);
                    await connection.OpenAsync();
                    await operation(connection);
                }));
            }

            await Task.WhenAll(tasks);
        }
    }

    public class Program
    {
        public static async Task Main(string[] args)
        {
            Console.WriteLine("Azure Entra Auth Service Examples");
            Console.WriteLine("===================================\n");

            Console.WriteLine("Choose an example to run:");
            Console.WriteLine("1. Simple Console Authentication");
            Console.WriteLine("2. WPF Integration");
            Console.WriteLine("3. Cached Token Management");
            Console.WriteLine("4. SQL Retry Logic");
            Console.WriteLine("5. Bulk Data Loading");
            Console.WriteLine("6. Async Data Reader");
            Console.WriteLine("7. Timeout Handling");
            Console.WriteLine("8. Multi-Tenant");

            // Example: Run simple console example
            // await SimpleConsoleExample.RunAsync();

            Console.WriteLine("\nExamples are ready to use!");
        }
    }
}

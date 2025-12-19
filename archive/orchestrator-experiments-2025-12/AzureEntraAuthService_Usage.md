# Azure Entra Device Code Flow Authentication Service

## Overview

`AzureEntraAuthService` provides a complete implementation of OAuth2 Device Code Flow authentication for Azure AD MFA-enabled accounts. This enables passwordless, MFA-compatible authentication to Azure SQL Database.

## Key Features

- ✅ Device Code Flow for MFA-enabled Azure AD accounts
- ✅ Async/await pattern with CancellationToken support
- ✅ Progress reporting interface for UI integration
- ✅ Automatic browser opening for device code verification
- ✅ Configurable polling with exponential backoff
- ✅ Comprehensive error handling
- ✅ 15-minute timeout with user-friendly messaging

## Constants

The service uses these fixed Azure constants:

```csharp
AZURE_SQL_SCOPE = "https://database.windows.net/.default"
AZURE_CLI_CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  // Well-known Azure CLI client
AZURE_COMMON_TENANT = "common"
```

## Basic Usage

### Simple Console Example

```csharp
using NimbusUserLoader.Services;

// Create service (uses default "common" tenant)
var authService = new AzureEntraAuthService();

// Authenticate with progress reporting
var progress = new ConsoleAuthenticationProgress();
var accessToken = await authService.AuthenticateAsync(progress);

// Use token to create SQL connection
var connectionString = "Server=myserver.database.windows.net;Database=mydb;";
using var connection = AzureEntraAuthService.CreateSqlConnection(connectionString, accessToken);
await connection.OpenAsync();
```

### With Specific Tenant

```csharp
// Use specific Azure AD tenant
var authService = new AzureEntraAuthService("your-tenant-id");
var accessToken = await authService.AuthenticateAsync();
```

### With Cancellation Token

```csharp
using var cts = new CancellationTokenSource(TimeSpan.FromMinutes(5));

var accessToken = await authService.AuthenticateAsync(
    progress: new ConsoleAuthenticationProgress(),
    cancellationToken: cts.Token);
```

## Custom Progress Reporting

Implement `IAuthenticationProgress` for custom UI:

```csharp
public class WpfAuthenticationProgress : AzureEntraAuthService.IAuthenticationProgress
{
    private readonly MainWindow _window;

    public WpfAuthenticationProgress(MainWindow window)
    {
        _window = window;
    }

    public void ReportDeviceCode(string userCode, string verificationUri)
    {
        _window.Dispatcher.Invoke(() =>
        {
            _window.UserCodeTextBlock.Text = userCode;
            _window.VerificationLinkTextBlock.Text = verificationUri;
            // Open browser
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = verificationUri,
                UseShellExecute = true
            });
        });
    }

    public void ReportPollingStarted()
    {
        _window.Dispatcher.Invoke(() =>
        {
            _window.StatusTextBlock.Text = "Waiting for sign-in...";
            _window.ProgressBar.IsIndeterminate = true;
        });
    }

    public void ReportPollingProgress(int secondsElapsed)
    {
        _window.Dispatcher.Invoke(() =>
        {
            _window.ElapsedTimeTextBlock.Text = $"{secondsElapsed}s elapsed";
        });
    }

    public void ReportAuthenticationComplete()
    {
        _window.Dispatcher.Invoke(() =>
        {
            _window.StatusTextBlock.Text = "✓ Authentication successful!";
            _window.ProgressBar.IsIndeterminate = false;
        });
    }

    public void ReportError(string errorMessage)
    {
        _window.Dispatcher.Invoke(() =>
        {
            MessageBox.Show($"Authentication failed: {errorMessage}", "Error");
        });
    }
}

// Usage:
var progress = new WpfAuthenticationProgress(this);
var accessToken = await authService.AuthenticateAsync(progress);
```

## SQL Connection Integration

### Basic Connection

```csharp
var connectionString = "Server=myserver.database.windows.net;Database=mydb;";
using var connection = AzureEntraAuthService.CreateSqlConnection(connectionString, accessToken);
await connection.OpenAsync();

using var command = connection.CreateCommand();
command.CommandText = "SELECT COUNT(*) FROM Users";
var count = (int)await command.ExecuteScalarAsync();
```

### Connection Pool Management

```csharp
// Tokens have lifetime - refresh when expired
private async Task<string> GetValidAccessTokenAsync()
{
    if (_cachedToken == null || _tokenExpiry < DateTime.UtcNow)
    {
        _cachedToken = await _authService.AuthenticateAsync();
        _tokenExpiry = DateTime.UtcNow.AddHours(1); // Typical token lifetime
    }
    return _cachedToken;
}
```

### With Connection Retry Logic

```csharp
public async Task<T> ExecuteWithRetryAsync<T>(
    string connectionString,
    Func<SqlConnection, Task<T>> operation,
    int maxRetries = 3)
{
    for (int attempt = 0; attempt < maxRetries; attempt++)
    {
        try
        {
            var accessToken = await GetValidAccessTokenAsync();
            using var connection = AzureEntraAuthService.CreateSqlConnection(
                connectionString, accessToken);
            await connection.OpenAsync();
            return await operation(connection);
        }
        catch (SqlException ex) when (attempt < maxRetries - 1 && IsTransientError(ex))
        {
            await Task.Delay(TimeSpan.FromSeconds(Math.Pow(2, attempt)));
            continue;
        }
    }
    throw new InvalidOperationException("Operation failed after retries");
}

private static bool IsTransientError(SqlException ex)
{
    // Check for transient SQL errors (40613, 40501, etc.)
    return ex.Number is 40613 or 40501 or 40197 or 64;
}
```

## Error Handling

The service throws specific exceptions:

- `InvalidOperationException`: Auth flow errors, invalid responses
- `TimeoutException`: 15-minute timeout exceeded
- `HttpRequestException`: Network issues
- `OperationCanceledException`: Token cancellation

```csharp
try
{
    var accessToken = await authService.AuthenticateAsync();
}
catch (TimeoutException)
{
    MessageBox.Show("Authentication timed out. Please try again.");
}
catch (OperationCanceledException)
{
    MessageBox.Show("Authentication was cancelled.");
}
catch (Exception ex)
{
    MessageBox.Show($"Authentication failed: {ex.Message}");
}
```

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. GetDeviceCodeAsync()                                     │
│    POST to /devicecode endpoint                            │
│    ↓ Returns: user_code, verification_uri, device_code     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Report to User                                           │
│    Display user_code and verification_uri                  │
│    Open browser to verification_uri                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. PollForTokenAsync()                                      │
│    Loop: Poll /token endpoint                              │
│    - If "authorization_pending" → wait and retry           │
│    - If error → throw exception                            │
│    - If success → return access_token                      │
│    Timeout after 15 minutes                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. CreateSqlConnection()                                    │
│    Create SqlConnection with access_token                  │
│    Ready for SQL operations                                │
└─────────────────────────────────────────────────────────────┘
```

## Testing

### Unit Test Example

```csharp
[TestClass]
public class AzureEntraAuthServiceTests
{
    private AzureEntraAuthService _service;
    private Mock<HttpMessageHandler> _httpHandler;

    [TestInitialize]
    public void Setup()
    {
        _httpHandler = new Mock<HttpMessageHandler>();
        _service = new AzureEntraAuthService();
    }

    [TestMethod]
    public async Task AuthenticateAsync_WithValidDeviceCode_ReturnsAccessToken()
    {
        // Arrange
        var mockProgress = new Mock<AzureEntraAuthService.IAuthenticationProgress>();
        
        // Act
        var token = await _service.AuthenticateAsync(mockProgress.Object);

        // Assert
        Assert.IsNotNull(token);
        Assert.IsTrue(token.Length > 0);
        mockProgress.Verify(p => p.ReportDeviceCode(It.IsAny<string>(), It.IsAny<string>()));
        mockProgress.Verify(p => p.ReportAuthenticationComplete());
    }

    [TestMethod]
    [ExpectedException(typeof(TimeoutException))]
    public async Task AuthenticateAsync_AfterTimeout_ThrowsTimeoutException()
    {
        // This would need mocked delays to test practically
    }
}
```

## Integration with Existing Services

The service integrates seamlessly with `ODataCacheService` and `AuthenticationService`:

```csharp
public class IntegratedAuthService
{
    private readonly AzureEntraAuthService _entraAuth;
    private readonly ODataCacheService _cache;

    public IntegratedAuthService(ODataCacheService cache)
    {
        _entraAuth = new AzureEntraAuthService();
        _cache = cache;
    }

    public async Task<string> GetCachedDataAsync(string connectionString)
    {
        // Try cache first
        var cached = _cache.Get("sql_data");
        if (cached != null) return cached;

        // Authenticate
        var accessToken = await _entraAuth.AuthenticateAsync();

        // Query SQL
        using var connection = AzureEntraAuthService.CreateSqlConnection(
            connectionString, accessToken);
        await connection.OpenAsync();

        var result = await QueryDatabaseAsync(connection);

        // Cache result
        _cache.Set("sql_data", result, TimeSpan.FromHours(1));

        return result;
    }
}
```

## Dependencies

Required NuGet packages:
- `Microsoft.Data.SqlClient` (for SQL connections)
- `Newtonsoft.Json` (for JSON deserialization)

```xml
<ItemGroup>
    <PackageReference Include="Microsoft.Data.SqlClient" Version="5.1.0" />
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
</ItemGroup>
```

## Troubleshooting

### "authorization_pending" - Takes too long
- Normal behavior - user hasn't completed sign-in yet
- Service will continue polling for 15 minutes
- User can check the code at https://microsoft.com/devicelogin

### "invalid_grant" - Code already used
- User may have already signed in on another device
- Request a new device code and try again

### "invalid_client" - Azure CLI client ID issues
- Ensure AZURE_CLI_CLIENT_ID is correct (04b07795-8ddb-461a-bbee-02f9e1bf7b46)
- This is a Microsoft-provided well-known client

### Network timeouts
- Ensure target machine can reach login.microsoftonline.com
- Check firewall and proxy settings
- Verify DNS resolution

## Security Considerations

1. **Token Handling**: Tokens are in-memory only, not persisted to disk
2. **HTTPS Only**: All Azure endpoints use HTTPS
3. **Tenant Isolation**: Specify tenant ID for additional security
4. **Scope Limiting**: Uses specific SQL scope, not general access
5. **Timeout**: 15-minute maximum device code lifetime prevents stale flows

## Performance Notes

- Initial device code request: ~200-500ms
- User sign-in: Variable (depends on user)
- Token polling: ~1s interval (configurable)
- Overall flow: Typically 30-60 seconds for interactive sign-in

## References

- [Azure Device Code Flow](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-device-code)
- [Microsoft.Data.SqlClient](https://github.com/dotnet/SqlClient)
- [Azure SQL Authentication](https://learn.microsoft.com/en-us/azure/azure-sql/database/authentication-aad-overview)

# Integration Guide: AzureEntraAuthService with Nimbus Project

## Quick Start Integration

### Step 1: Copy Files
```
Copy AzureEntraAuthService.cs to:
src/nimbus-user-gui/Services/AzureEntraAuthService.cs
```

### Step 2: Update Namespace (if needed)
```csharp
// If your project namespace differs, update:
namespace NimbusUserLoader.Services  // Adjust as needed
```

### Step 3: Ensure NuGet Dependencies
```xml
<ItemGroup>
    <PackageReference Include="Microsoft.Data.SqlClient" Version="5.1.0" />
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
</ItemGroup>
```

### Step 4: Create Progress Reporter for Your UI
See examples below for your specific UI framework.

## Integration with Existing Services

### Pattern 1: Alongside ODataCacheService

The `AzureEntraAuthService` complements `ODataCacheService` by providing SQL authentication:

```csharp
public class DataService
{
    private readonly AzureEntraAuthService _authService;
    private readonly ODataCacheService _cacheService;
    private readonly string _sqlConnectionString;

    public DataService(ODataCacheService cacheService, string sqlConnectionString)
    {
        _authService = new AzureEntraAuthService();
        _cacheService = cacheService;
        _sqlConnectionString = sqlConnectionString;
    }

    /// <summary>
    /// Get data from cache first, then SQL if needed.
    /// </summary>
    public async Task<T> GetDataAsync<T>(string cacheKey, Func<SqlConnection, Task<T>> queryFunc)
    {
        // Try cache
        if (_cacheService.TryGet(cacheKey, out T cached))
        {
            return cached;
        }

        // Authenticate and query SQL
        var token = await _authService.AuthenticateAsync();
        using var connection = AzureEntraAuthService.CreateSqlConnection(
            _sqlConnectionString, token);
        await connection.OpenAsync();

        var result = await queryFunc(connection);

        // Cache for future use
        _cacheService.Set(cacheKey, result, TimeSpan.FromHours(1));

        return result;
    }
}
```

### Pattern 2: Extend AuthenticationService

If your existing `AuthenticationService` handles general auth, extend it to include SQL auth:

```csharp
public class ExtendedAuthenticationService : AuthenticationService
{
    private readonly AzureEntraAuthService _sqlAuthService;
    private string _cachedSqlToken;

    public ExtendedAuthenticationService() : base()
    {
        _sqlAuthService = new AzureEntraAuthService();
    }

    /// <summary>
    /// Get SQL access token (extends base authentication).
    /// </summary>
    public async Task<string> GetSqlAccessTokenAsync(
        IAuthenticationProgress progress = null)
    {
        if (!string.IsNullOrEmpty(_cachedSqlToken))
        {
            return _cachedSqlToken;
        }

        _cachedSqlToken = await _sqlAuthService.AuthenticateAsync(progress);
        return _cachedSqlToken;
    }

    public void InvalidateSqlToken()
    {
        _cachedSqlToken = null;
    }
}
```

### Pattern 3: Dependency Injection (Recommended)

Setup in your DI container:

```csharp
// Startup.cs or Program.cs
public void ConfigureServices(IServiceCollection services)
{
    // Register Azure Auth Service
    services.AddScoped<AzureEntraAuthService>(provider =>
    {
        var tenantId = Configuration["Azure:TenantId"] ?? "common";
        return new AzureEntraAuthService(tenantId);
    });

    // Register token manager for caching
    services.AddSingleton<CachedTokenManager>(provider =>
    {
        var tenantId = Configuration["Azure:TenantId"] ?? "common";
        return new CachedTokenManager(tenantId);
    });

    // Register SQL operations helper
    services.AddScoped<SqlOperationWithRetry>(provider =>
    {
        var connString = Configuration.GetConnectionString("DefaultConnection");
        return new SqlOperationWithRetry(connString);
    });

    services.AddOther();
}
```

Usage in controllers/services:

```csharp
[ApiController]
[Route("api/[controller]")]
public class DataController : ControllerBase
{
    private readonly SqlOperationWithRetry _sqlOps;
    private readonly AzureEntraAuthService _authService;

    public DataController(
        SqlOperationWithRetry sqlOps,
        AzureEntraAuthService authService)
    {
        _sqlOps = sqlOps;
        _authService = authService;
    }

    [HttpGet("users")]
    public async Task<IActionResult> GetUsers()
    {
        var count = await _sqlOps.ExecuteWithRetryAsync(async conn =>
        {
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "SELECT COUNT(*) FROM Users";
            return (int)await cmd.ExecuteScalarAsync();
        });

        return Ok(new { userCount = count });
    }
}
```

## UI Framework Integration

### WPF Integration

```csharp
public partial class AuthWindow : Window
{
    private readonly AzureEntraAuthService _authService;
    private string _cachedToken;

    public AuthWindow()
    {
        InitializeComponent();
        _authService = new AzureEntraAuthService();
    }

    private async void AuthenticateButton_Click(object sender, RoutedEventArgs e)
    {
        AuthenticateButton.IsEnabled = false;
        StatusTextBlock.Text = "Starting authentication...";

        try
        {
            var progress = new WpfAuthenticationProgress(
                updateStatus: status => Dispatcher.Invoke(() =>
                    StatusTextBlock.Text = status),
                setUserCode: code => Dispatcher.Invoke(() =>
                    UserCodeTextBlock.Text = code),
                setVerificationUri: uri => Dispatcher.Invoke(() =>
                    VerificationLinkTextBlock.Text = uri),
                setProgressIndeterminate: flag => Dispatcher.Invoke(() =>
                    ProgressBar.IsIndeterminate = flag)
            );

            _cachedToken = await _authService.AuthenticateAsync(progress);

            StatusTextBlock.Text = "✓ Authenticated successfully!";
            DialogResult = true;
            Close();
        }
        catch (OperationCanceledException)
        {
            StatusTextBlock.Text = "Authentication was cancelled";
        }
        catch (TimeoutException)
        {
            StatusTextBlock.Text = "Authentication timed out";
        }
        catch (Exception ex)
        {
            StatusTextBlock.Text = $"Error: {ex.Message}";
        }
        finally
        {
            AuthenticateButton.IsEnabled = true;
        }
    }

    public string GetCachedToken() => _cachedToken;
}
```

### WinForms Integration

```csharp
public partial class AuthForm : Form
{
    private readonly AzureEntraAuthService _authService;
    private string _cachedToken;

    public AuthForm()
    {
        InitializeComponent();
        _authService = new AzureEntraAuthService();
    }

    private async void AuthenticateButton_Click(object sender, EventArgs e)
    {
        AuthenticateButton.Enabled = false;
        StatusLabel.Text = "Starting authentication...";

        try
        {
            var progress = new WinFormsAuthenticationProgress(this);
            _cachedToken = await _authService.AuthenticateAsync(progress);

            StatusLabel.Text = "✓ Authenticated successfully!";
            DialogResult = DialogResult.OK;
            Close();
        }
        catch (Exception ex)
        {
            StatusLabel.Text = $"Error: {ex.Message}";
            MessageBox.Show(ex.Message, "Authentication Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            AuthenticateButton.Enabled = true;
        }
    }

    public string GetCachedToken() => _cachedToken;
}

public class WinFormsAuthenticationProgress : AzureEntraAuthService.IAuthenticationProgress
{
    private readonly AuthForm _form;

    public WinFormsAuthenticationProgress(AuthForm form)
    {
        _form = form;
    }

    public void ReportDeviceCode(string userCode, string verificationUri)
    {
        _form.Invoke(() =>
        {
            _form.UserCodeLabel.Text = userCode;
            _form.VerificationLinkLabel.Text = verificationUri;
            System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
            {
                FileName = verificationUri,
                UseShellExecute = true
            });
        });
    }

    public void ReportPollingStarted()
    {
        _form.Invoke(() =>
        {
            _form.ProgressBar.Style = ProgressBarStyle.Marquee;
            _form.StatusLabel.Text = "Waiting for sign-in...";
        });
    }

    public void ReportPollingProgress(int secondsElapsed)
    {
        if (secondsElapsed % 5 == 0)
        {
            _form.Invoke(() =>
                _form.StatusLabel.Text = $"Waiting... ({secondsElapsed}s)");
        }
    }

    public void ReportAuthenticationComplete()
    {
        _form.Invoke(() =>
        {
            _form.ProgressBar.Style = ProgressBarStyle.Continuous;
            _form.StatusLabel.Text = "✓ Success!";
        });
    }

    public void ReportError(string errorMessage)
    {
        _form.Invoke(() =>
        {
            _form.ProgressBar.Style = ProgressBarStyle.Continuous;
            _form.StatusLabel.Text = $"✗ Error: {errorMessage}";
        });
    }
}
```

### ASP.NET Core / Blazor Integration

```csharp
// Service
public class BlazorAuthService
{
    private readonly AzureEntraAuthService _authService;
    private string _cachedToken;
    public event Action OnAuthenticationCompleted;

    public BlazorAuthService()
    {
        _authService = new AzureEntraAuthService();
    }

    public async Task AuthenticateAsync(IAuthenticationProgress progress)
    {
        _cachedToken = await _authService.AuthenticateAsync(progress);
        OnAuthenticationCompleted?.Invoke();
    }

    public string GetToken() => _cachedToken;
    public bool IsAuthenticated => !string.IsNullOrEmpty(_cachedToken);
}

// Razor Component
@page "/authenticate"
@inject BlazorAuthService AuthService
@implements IDisposable

<div class="auth-container">
    @if (!IsAuthenticated)
    {
        <button class="btn btn-primary" @onclick="StartAuthentication">
            Sign in with Azure AD
        </button>
        
        @if (!string.IsNullOrEmpty(DeviceCode))
        {
            <div class="alert alert-info">
                <p>Your device code: <code>@DeviceCode</code></p>
                <p><a href="@VerificationUri" target="_blank">Click here to sign in</a></p>
                <p>@StatusMessage</p>
            </div>
        }
    }
    else
    {
        <p class="alert alert-success">✓ You are signed in!</p>
    }
</div>

@code {
    private string DeviceCode;
    private string VerificationUri;
    private string StatusMessage;
    private bool IsAuthenticated = false;

    protected override void OnInitialized()
    {
        AuthService.OnAuthenticationCompleted += OnAuthComplete;
    }

    private async Task StartAuthentication()
    {
        var progress = new BlazorAuthenticationProgress(this);
        await AuthService.AuthenticateAsync(progress);
    }

    private void OnAuthComplete()
    {
        IsAuthenticated = AuthService.IsAuthenticated;
        StateHasChanged();
    }

    void IDisposable.Dispose()
    {
        AuthService.OnAuthenticationCompleted -= OnAuthComplete;
    }

    public class BlazorAuthenticationProgress : AzureEntraAuthService.IAuthenticationProgress
    {
        private readonly Component _component;

        public BlazorAuthenticationProgress(Component component)
        {
            _component = component;
        }

        public void ReportDeviceCode(string userCode, string verificationUri)
        {
            // Update component state
            _component.GetType()
                .GetProperty("DeviceCode")
                ?.SetValue(_component, userCode);
            _component.GetType()
                .GetProperty("VerificationUri")
                ?.SetValue(_component, verificationUri);
        }

        public void ReportPollingStarted()
        {
            ReportPollingProgress(0);
        }

        public void ReportPollingProgress(int secondsElapsed)
        {
            var status = $"Waiting for sign-in... ({secondsElapsed}s)";
            _component.GetType()
                .GetProperty("StatusMessage")
                ?.SetValue(_component, status);
        }

        public void ReportAuthenticationComplete()
        {
            _component.GetType()
                .GetProperty("StatusMessage")
                ?.SetValue(_component, "✓ Signed in successfully!");
        }

        public void ReportError(string errorMessage)
        {
            _component.GetType()
                .GetProperty("StatusMessage")
                ?.SetValue(_component, $"✗ Error: {errorMessage}");
        }
    }
}
```

## Configuration

Add to your appsettings.json:

```json
{
  "Azure": {
    "TenantId": "common",
    "SqlScope": "https://database.windows.net/.default",
    "CliClientId": "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
  },
  "ConnectionStrings": {
    "DefaultConnection": "Server=myserver.database.windows.net;Database=mydb;",
    "SqlConnection": "Server=myserver.database.windows.net;Database=mydb;"
  }
}
```

Usage in configuration:

```csharp
var tenantId = Configuration["Azure:TenantId"];
var connString = Configuration.GetConnectionString("SqlConnection");
var authService = new AzureEntraAuthService(tenantId);
```

## Testing Integration

### Unit Test Example

```csharp
[TestClass]
public class AuthServiceIntegrationTests
{
    private Mock<AzureEntraAuthService> _mockAuthService;
    private DataService _dataService;

    [TestInitialize]
    public void Setup()
    {
        _mockAuthService = new Mock<AzureEntraAuthService>();
        _dataService = new DataService("test_connection_string");
    }

    [TestMethod]
    public async Task GetDataAsync_WithValidToken_ReturnsData()
    {
        // Arrange
        var expectedToken = "test_token";
        _mockAuthService
            .Setup(x => x.AuthenticateAsync(It.IsAny<AzureEntraAuthService.IAuthenticationProgress>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(expectedToken);

        // Act
        var result = await _dataService.GetDataAsync(
            "test_key",
            conn => Task.FromResult("test_data"));

        // Assert
        Assert.AreEqual("test_data", result);
    }

    [TestMethod]
    [ExpectedException(typeof(TimeoutException))]
    public async Task GetDataAsync_WithTimeout_ThrowsException()
    {
        // Arrange
        _mockAuthService
            .Setup(x => x.AuthenticateAsync(It.IsAny<AzureEntraAuthService.IAuthenticationProgress>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new TimeoutException());

        // Act
        await _dataService.GetDataAsync("test_key", conn => Task.FromResult("data"));
    }
}
```

## Migration from Other Auth Methods

### From Connection String Credentials
```csharp
// OLD (no longer recommended)
var connString = "Server=myserver.database.windows.net;Database=mydb;User ID=user@example.com;Password=...";
using var connection = new SqlConnection(connString);

// NEW (with Device Code Flow)
var authService = new AzureEntraAuthService();
var token = await authService.AuthenticateAsync();
var connString = "Server=myserver.database.windows.net;Database=mydb;";
using var connection = AzureEntraAuthService.CreateSqlConnection(connString, token);
```

### From Managed Identity
```csharp
// OLD (Azure VM/App Service only)
var credential = new DefaultAzureCredential();
var token = await credential.GetTokenAsync(new TokenRequestContext(new[] { "https://database.windows.net/.default" }));

// NEW (Any environment, with MFA)
var authService = new AzureEntraAuthService();
var token = await authService.AuthenticateAsync();
// Works from laptop, docker container, etc.
```

## Troubleshooting Integration Issues

### Issue: "Cannot find AzureEntraAuthService"
**Solution**: Ensure file is copied to correct Services folder and namespace matches.

### Issue: "Missing NuGet dependencies"
**Solution**: Install required packages:
```bash
dotnet add package Microsoft.Data.SqlClient
dotnet add package Newtonsoft.Json
```

### Issue: "Browser won't open"
**Solution**: Catch exception and show URI to user:
```csharp
try
{
    System.Diagnostics.Process.Start(verificationUri);
}
catch
{
    Console.WriteLine($"Visit: {verificationUri}");
}
```

### Issue: "Token expires during operation"
**Solution**: Use `CachedTokenManager` which handles refresh:
```csharp
var tokenMgr = new CachedTokenManager();
var token = await tokenMgr.GetValidAccessTokenAsync();
// Automatically refreshes if expired
```

## Performance Tuning

### Token Caching
Use `CachedTokenManager` to avoid repeated authentication:
- First call: ~2-5 seconds (requires user interaction)
- Cached calls: <1ms

### Connection Pooling
Azure SDK handles connection pooling automatically. Reuse connections when possible:

```csharp
// Good - connection reuse
var sqlOps = new SqlOperationWithRetry(connString);
var result1 = await sqlOps.ExecuteWithRetryAsync(query1);
var result2 = await sqlOps.ExecuteWithRetryAsync(query2);

// Less ideal - new service each time
var service1 = new AzureEntraAuthService();
var token1 = await service1.AuthenticateAsync();
// ... token2, token3, etc.
```

### Polling Optimization
Default polling interval (1 second) is reasonable for most scenarios. Adjust if needed:

In `AzureEntraAuthService`:
```csharp
// Change DEFAULT_POLL_INTERVAL_MS to tune polling
private const int DEFAULT_POLL_INTERVAL_MS = 2000; // 2 seconds instead of 1
```

## Next Steps

1. Copy `AzureEntraAuthService.cs` to your services folder
2. Choose integration pattern that matches your architecture
3. Implement custom `IAuthenticationProgress` for your UI
4. Add to dependency injection container
5. Start using in your services/controllers
6. Run tests to verify integration

## Support

Refer to these files for additional help:
- `AzureEntraAuthService_Usage.md` - Detailed usage guide
- `AzureEntraAuthService_Examples.cs` - Code examples
- `AzureEntraAuthService.cs` - Full implementation with XML docs

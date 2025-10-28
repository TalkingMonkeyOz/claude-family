# C# Desktop Development with Claude Code - MCP Enhancement Guide

**Purpose**: Maximize Claude Code's effectiveness for C# desktop applications (WPF, WinForms, WinUI)
**Target Projects**: Claude PM, Nimbus User Loader, any .NET desktop projects
**Created**: 2025-10-26

---

## Quick Start

**Already Installed:**
- ✅ Context7 MCP - Up-to-date C#/.NET documentation
- ✅ Roslyn MCP - Code analysis and refactoring

**Install Next:**
- ⏳ NuGet MCP - Package management (requires .NET 10, available later)

---

## 1. Context7 MCP - Documentation Access

### What It Does
Fetches current, version-specific documentation from official sources:
- C# language features
- .NET framework APIs (latest .NET 8/9 patterns)
- WPF/WinForms/WinUI documentation
- NuGet package documentation
- MVVM frameworks (CommunityToolkit.Mvvm, Prism, etc.)

### Installation
```bash
# Already installed globally
claude mcp list  # Verify context7 is listed
```

### Usage Patterns

**Trigger Context7 by adding "use context7" to your prompt:**

```bash
# WPF Examples
"Create a ViewModel for user management using CommunityToolkit.Mvvm. use context7"
"How do I bind a DataGrid to an ObservableCollection in WPF? use context7"
"Implement ICommand with RelayCommand. use context7"

# WinForms Examples
"Create a custom UserControl with designer support. use context7"
"How do I implement async loading in WinForms? use context7"

# .NET API Examples
"Use HttpClient with retry policy using Polly. use context7"
"Implement async/await with ConfigureAwait in desktop apps. use context7"

# MVVM Patterns
"Structure a ViewModel with validation using DataAnnotations. use context7"
"Implement property change notification with [ObservableProperty]. use context7"
```

**Without "use context7":**
- Claude uses training data (January 2025 cutoff)
- May suggest deprecated patterns
- Missing recent C# 12 features

**With "use context7":**
- Gets current documentation
- Latest API patterns
- Modern C# syntax

### Security Note (ATO Projects)
✅ **Safe for:**
- Public frameworks (C#, .NET, WPF, WinForms)
- Public NuGet packages
- Open-source libraries

❌ **Don't use for:**
- Internal ATO APIs
- Proprietary tax calculation logic
- Client-specific implementations
- Sensitive business logic

**Reason**: Queries go to external API server. Only use for public knowledge.

---

## 2. Roslyn Analyzer MCP - Code Analysis

### What It Does
Provides deep C# code analysis using Microsoft's Roslyn compiler:
- Symbol search across entire solution
- Reference tracking (find all usages)
- Cyclomatic complexity calculation
- Code structure analysis
- MSBuild project integration

### Installation

**Requirements:**
- .NET 8.0 SDK or later
- Git

**Steps:**
```bash
# 1. Clone repository
cd C:\Projects
git clone https://github.com/egorpavlikhin/roslyn-mcp.git

# 2. Build project
cd roslyn-mcp
dotnet build RoslynMCP.sln

# 3. Add to Claude Code
claude mcp add roslyn -s user -- dotnet run --no-build --project "C:\Projects\roslyn-mcp\RoslynMCP\RoslynMCP.csproj"

# 4. Verify installation
claude mcp list
# Should show: roslyn: ... - ✓ Connected
```

**Note**: Builds with 19 nullable warnings (non-critical), 0 errors.

### Usage Patterns

**Code Analysis:**
```bash
"Analyze the complexity of UserService.cs"
"Find all references to IConnectionManager interface"
"Search for all classes implementing IPluginModule"
```

**Refactoring:**
```bash
"Analyze DatabaseService for high-complexity methods and suggest refactoring"
"Find all usages of deprecated GetVal() method"
```

**Architecture Exploration:**
```bash
"Map all dependencies of the authentication module"
"Find circular dependencies in the project"
```

### Troubleshooting

**Problem:** Roslyn MCP not connecting
**Solution:**
```bash
# Ensure .NET 8 SDK is installed
dotnet --list-sdks

# Rebuild with verbose logging
cd C:\Projects\roslyn-mcp
dotnet clean
dotnet build RoslynMCP.sln -v detailed

# Test manual run
dotnet run --project RoslynMCP\RoslynMCP.csproj

# If still failing, check .NET 9 requirement
# This version requires .NET 9 runtime
dotnet --version  # Should be 9.x
```

---

## 3. NuGet MCP - Package Management (Future)

### What It Will Do
- Real-time NuGet package search
- Version discovery and compatibility checking
- Dependency resolution (Microsoft Research NuGetSolver)
- Security vulnerability detection

### Installation (When Available)

**Requirements:**
- .NET 10 Preview 6 or later (released Q2 2025)

**Steps:**
```bash
# Install .NET 10 Preview
# Download from: https://dotnet.microsoft.com/download/dotnet/10.0

# Add NuGet MCP
claude mcp add nuget -s user -- dnx NuGet.Mcp.Server --prerelease --yes

# Verify
claude mcp list
```

### Usage Patterns (When Available)
```bash
"Find the latest Excel export package for .NET 8"
"Add EPPlus with dependencies to ClaudePM.csproj"
"Check for security vulnerabilities in current packages"
"Suggest alternative to Newtonsoft.Json for System.Text.Json migration"
```

**Status**: ⏳ Waiting for .NET 10 RTM (expected Q3 2025)

---

## 4. WPF-Specific Best Practices

### MVVM Pattern with CommunityToolkit.Mvvm

**DO:**
```csharp
// Use ObservableProperty attribute (no manual INotifyPropertyChanged)
public partial class UserViewModel : ObservableObject
{
    [ObservableProperty]
    private string userName;  // Generates UserName property automatically

    [RelayCommand]
    private async Task SaveUserAsync()
    {
        // Command implementation
    }
}
```

**DON'T:**
```csharp
// Manual INotifyPropertyChanged boilerplate (outdated pattern)
private string _userName;
public string UserName
{
    get => _userName;
    set
    {
        _userName = value;
        OnPropertyChanged(nameof(UserName));
    }
}
```

### Data Binding Patterns

**OneWay vs TwoWay:**
```xml
<!-- Default is OneWay for most properties -->
<TextBlock Text="{Binding UserName}" />

<!-- TwoWay for input controls -->
<TextBox Text="{Binding UserName, Mode=TwoWay, UpdateSourceTrigger=PropertyChanged}" />

<!-- OneTime for static data -->
<TextBlock Text="{Binding AppVersion, Mode=OneTime}" />
```

### Async Commands
```csharp
[RelayCommand(CanExecute = nameof(CanSave))]
private async Task SaveAsync()
{
    IsLoading = true;
    try
    {
        await _databaseService.SaveAsync();
    }
    finally
    {
        IsLoading = false;
    }
}

private bool CanSave() => !IsLoading && IsValid;
```

### UI Thread Marshalling
```csharp
// WPF automatic marshalling
Application.Current.Dispatcher.Invoke(() =>
{
    StatusText = "Operation complete";
});

// Or use async version
await Application.Current.Dispatcher.InvokeAsync(() =>
{
    ProgressBar.Value = 100;
});
```

---

## 5. WinForms-Specific Best Practices

### Async Event Handlers
```csharp
private async void LoadButton_Click(object sender, EventArgs e)
{
    LoadButton.Enabled = false;
    try
    {
        var data = await _dataService.LoadDataAsync();
        DataGridView.DataSource = data;
    }
    finally
    {
        LoadButton.Enabled = true;
    }
}
```

### Thread-Safe UI Updates
```csharp
// Use Invoke for cross-thread UI updates
if (StatusLabel.InvokeRequired)
{
    StatusLabel.Invoke(new Action(() => StatusLabel.Text = "Complete"));
}
else
{
    StatusLabel.Text = "Complete";
}

// Or use extension helper
public static void SafeInvoke(this Control control, Action action)
{
    if (control.InvokeRequired)
        control.Invoke(action);
    else
        action();
}

// Usage
StatusLabel.SafeInvoke(() => StatusLabel.Text = "Complete");
```

### Designer Best Practices
```csharp
// Separate Designer code from business logic
public partial class MainForm : Form  // MainForm.cs
{
    private readonly IDataService _dataService;

    public MainForm(IDataService dataService)
    {
        InitializeComponent();  // Designer-generated
        _dataService = dataService;
        SetupEventHandlers();   // Manual event wiring
    }
}

// Keep designer file clean (MainForm.Designer.cs - auto-generated)
```

---

## 6. Common C# Desktop Patterns

### Dependency Injection Setup
```csharp
// Program.cs (WPF or WinForms)
var services = new ServiceCollection();

// Register services
services.AddSingleton<IDatabaseService, DatabaseService>();
services.AddTransient<IUserService, UserService>();

// Register ViewModels (WPF)
services.AddTransient<MainViewModel>();

// Build provider
var provider = services.BuildServiceProvider();

// Launch app
var mainWindow = provider.GetRequiredService<MainWindow>();
mainWindow.Show();
```

### Configuration Management
```csharp
// appsettings.json with User Secrets
var config = new ConfigurationBuilder()
    .SetBasePath(Directory.GetCurrentDirectory())
    .AddJsonFile("appsettings.json", optional: false)
    .AddUserSecrets<Program>()  // For sensitive data
    .Build();

// Access values
var connectionString = config["Database:ConnectionString"];
```

### Error Handling Pattern
```csharp
public async Task<Result<User>> LoadUserAsync(int userId)
{
    try
    {
        var user = await _repository.GetUserAsync(userId);
        return Result<User>.Success(user);
    }
    catch (NotFoundException ex)
    {
        _logger.LogWarning(ex, "User {UserId} not found", userId);
        return Result<User>.Failure("User not found");
    }
    catch (Exception ex)
    {
        _logger.LogError(ex, "Error loading user {UserId}", userId);
        return Result<User>.Failure("An error occurred");
    }
}
```

---

## 7. Prompting Strategies for Better Code

### Be Specific About Framework
```bash
# BAD
"Create a user management screen"

# GOOD
"Create a WPF UserControl for user management using MVVM pattern with CommunityToolkit.Mvvm"

# BEST (with Context7)
"Create a WPF UserControl for user management using MVVM pattern with CommunityToolkit.Mvvm.
Include DataGrid with CRUD operations, validation, and async save. use context7"
```

### Incremental Refinement
```bash
# Step 1
"Generate IUserService interface with CRUD methods"

# Step 2
"Implement IUserService using async/await with Npgsql for PostgreSQL"

# Step 3
"Add unit tests for UserService using xUnit and Moq"

# Step 4
"Refactor for dependency injection"
```

### Request Architecture Validation
```bash
"Review the UserViewModel for MVVM violations"
"Analyze DatabaseService for proper async patterns"
"Check if MainForm follows SRP (Single Responsibility Principle)"
```

---

## 8. Testing Patterns

### WPF ViewModel Testing
```csharp
[Fact]
public async Task SaveCommand_WithValidData_SavesUser()
{
    // Arrange
    var mockService = new Mock<IUserService>();
    var viewModel = new UserViewModel(mockService.Object);
    viewModel.UserName = "John Doe";

    // Act
    await viewModel.SaveCommand.ExecuteAsync(null);

    // Assert
    mockService.Verify(s => s.SaveUserAsync(It.IsAny<User>()), Times.Once);
}
```

### WinForms UI Testing (Manual)
```csharp
// For UI testing, use manual testing with test data
// Automated UI testing for WinForms is challenging
// Focus on unit testing business logic
```

---

## 9. Performance Optimization

### Virtual Lists for Large Data
```csharp
// WPF - Use virtualization
<ListView VirtualizingPanel.IsVirtualizing="True"
          VirtualizingPanel.VirtualizationMode="Recycling">
```

### Async Loading Patterns
```csharp
// Load data async, update UI incrementally
public async Task LoadLargeDatasetAsync()
{
    var batches = await _service.GetBatchesAsync();

    foreach (var batch in batches)
    {
        var data = await _service.LoadBatchAsync(batch);

        // Update UI after each batch (responsive)
        ObservableData.AddRange(data);
        await Task.Delay(10);  // Yield to UI thread
    }
}
```

---

## 10. Workflow Integration

### When Starting Work on Desktop C# Project

**1. Navigate to project:**
```bash
cd C:\Projects\claude-pm
# or
cd C:\Projects\nimbus-user-loader
```

**2. CLAUDE.md auto-loads with project context**

**3. Use MCPs intentionally:**
```bash
# For API questions
"How do I use ObservableCollection? use context7"

# For code analysis (when Roslyn MCP installed)
"Analyze MainViewModel complexity"

# For package discovery (when NuGet MCP available)
"Find latest Excel export package"
```

**4. Commit with context:**
```bash
git commit -m "WP-123: Implement user management ViewModel with CommunityToolkit.Mvvm"
```

---

## 11. Troubleshooting

### Context7 Not Working
```bash
# Check connection
claude mcp list

# Should show: context7: ... - ✓ Connected

# If not connected, reinstall
claude mcp remove context7
claude mcp add context7 -s user -- npx -y @upstash/context7-mcp
```

### Roslyn MCP Build Errors
```bash
# Ensure .NET 8 SDK
dotnet --list-sdks

# Clean rebuild
cd C:\Projects\RoslynMCP
dotnet clean
dotnet restore
dotnet build
```

---

## 12. Future Enhancements

**Planned:**
- 🔄 WpfAnalyzers integration (NuGet package for WPF-specific analyzers)
- ⏳ Custom ATO MCP (tax calculation validation)
- ⏳ Nimbus API MCP (Nimbus-specific patterns)

**Investigating:**
- MSBuild MCP (build automation)
- Visual Studio MCP (IDE integration)

---

## Summary: Expected Improvements

**Before Enhancement:**
- Generic C# patterns
- Outdated API suggestions
- Manual NuGet browsing
- Guesswork refactoring

**After Enhancement (Context7 + Roslyn):**
- ✅ Current .NET 8/9 patterns
- ✅ Accurate WPF/MVVM code
- ✅ Data-driven refactoring
- ✅ Symbol-level code navigation
- ✅ 60-70% time savings on "fix Claude's code"

**When NuGet MCP Available:**
- ✅ Real-time package discovery
- ✅ Automatic dependency resolution
- ✅ Security vulnerability detection

---

**Version**: 1.0
**Last Updated**: 2025-10-26
**Maintained By**: Claude Family
**Location**: C:\Projects\claude-family\shared\docs\csharp-desktop-mcp-guide.md

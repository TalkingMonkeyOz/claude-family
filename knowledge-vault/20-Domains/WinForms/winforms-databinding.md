---
synced: true
synced_at: '2025-12-21T14:40:40.019064'
---

# WinForms Data Binding

**Category**: winforms
**Tags**: #winforms #databinding #mvvm #dotnet8

---

## Binding Approaches

| Approach | .NET Version | Best For |
|----------|--------------|----------|
| Classic Binding | All | Simple forms, legacy code |
| MVVM | .NET 8+ | Complex apps, testability |

---

## Classic Binding

### Requirements

- Implement `INotifyPropertyChanged` on data class
- Use `BindingList<T>` for collections
- Use `BindingSource` as mediator

### Example Model

```csharp
public class Customer : INotifyPropertyChanged
{
    private string _name;

    public string Name
    {
        get => _name;
        set
        {
            if (_name != value)
            {
                _name = value;
                OnPropertyChanged();
            }
        }
    }

    public event PropertyChangedEventHandler? PropertyChanged;

    protected void OnPropertyChanged([CallerMemberName] string? name = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(name));
    }
}
```

### Binding in Code

```csharp
// Create binding source
var bindingSource = new BindingSource();
bindingSource.DataSource = customer;

// Bind controls
txtName.DataBindings.Add("Text", bindingSource, "Name",
    true, DataSourceUpdateMode.OnPropertyChanged);

// For collections
var listSource = new BindingSource();
listSource.DataSource = new BindingList<Customer>(customers);
dataGridView1.DataSource = listSource;
```

### Custom Conversion (Parse/Format)

```csharp
var binding = new Binding("Text", bindingSource, "BirthDate", true);
binding.Format += (s, e) =>
{
    if (e.Value is DateTime dt)
        e.Value = dt.ToString("dd/MM/yyyy");
};
binding.Parse += (s, e) =>
{
    if (DateTime.TryParse(e.Value?.ToString(), out var dt))
        e.Value = dt;
};
txtBirthDate.DataBindings.Add(binding);
```

---

## MVVM (.NET 8+)

### New APIs

| API | Purpose |
|-----|---------|
| `Control.DataContext` | Set ViewModel for control tree |
| `ButtonBase.Command` | Bind button to ICommand |
| `ToolStripItem.Command` | Bind menu/toolbar to ICommand |

### ViewModel with CommunityToolkit.Mvvm

```csharp
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

public partial class MainViewModel : ObservableObject
{
    [ObservableProperty]
    private string _customerName = "";

    [ObservableProperty]
    private bool _isLoading;

    [RelayCommand]
    private async Task SaveAsync()
    {
        IsLoading = true;
        try
        {
            await _repository.SaveAsync(CustomerName);
        }
        finally
        {
            IsLoading = false;
        }
    }
}
```

### MVVM Binding in Form

```csharp
public partial class MainForm : Form
{
    private readonly MainViewModel _viewModel;

    public MainForm()
    {
        InitializeComponent();

        _viewModel = new MainViewModel();
        this.DataContext = _viewModel;

        // Bind text
        txtCustomerName.DataBindings.Add("Text", _viewModel, "CustomerName",
            true, DataSourceUpdateMode.OnPropertyChanged);

        // Bind command
        btnSave.Command = _viewModel.SaveCommand;

        // Bind enabled state
        btnSave.DataBindings.Add("Enabled", _viewModel, "IsLoading",
            true, DataSourceUpdateMode.OnPropertyChanged,
            formatter: (v) => !(bool)v);
    }
}
```

---

## Designer DataSource Files

For Designer accessibility, create `.datasource` XML files:

**Location**: `Properties/DataSources/Customer.datasource`

```xml
<?xml version="1.0" encoding="utf-8"?>
<GenericObjectDataSource
    DisplayName="Customer"
    TypeName="MyApp.Models.Customer, MyApp"
    Version="1.0" />
```

This makes the type available in the Data Sources window.

---

## NuGet Packages

| Package | Purpose |
|---------|---------|
| CommunityToolkit.Mvvm | ObservableObject, RelayCommand |
| Microsoft.Extensions.DependencyInjection | DI container |

```xml
<PackageReference Include="CommunityToolkit.Mvvm" Version="8.*" />
```

---

**Version**: 1.0
**Source**: GitHub awesome-copilot WinFormsExpert.agent.md
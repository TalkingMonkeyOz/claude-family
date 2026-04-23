---
description: 'MVVM pattern for WPF applications'
applyTo: '**/ViewModels/**/*.cs,**/Views/**/*.xaml,**/Models/**/*.cs'
source: 'Claude Family + CommunityToolkit.Mvvm patterns'
---

# MVVM Pattern Guidelines

## Overview

Model-View-ViewModel (MVVM) separates UI from business logic. Use CommunityToolkit.Mvvm for minimal boilerplate.

## Project Structure

```
MyApp/
├── Models/           # Data classes, DTOs
├── ViewModels/       # UI logic, commands, state
├── Views/            # XAML pages/windows
├── Services/         # Business logic, data access
└── App.xaml          # Resources, DI setup
```

## ViewModel Base (CommunityToolkit.Mvvm)

```csharp
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

public partial class MainViewModel : ObservableObject
{
    // Observable property (generates PropertyChanged)
    [ObservableProperty]
    private string _title = "My App";

    // Observable property with notification to other properties
    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(FullName))]
    private string _firstName = "";

    [ObservableProperty]
    [NotifyPropertyChangedFor(nameof(FullName))]
    private string _lastName = "";

    // Computed property
    public string FullName => $"{FirstName} {LastName}";

    // Command (sync)
    [RelayCommand]
    private void Save()
    {
        // Save logic
    }

    // Command (async)
    [RelayCommand]
    private async Task LoadDataAsync()
    {
        // Async load logic
    }

    // Command with CanExecute
    [RelayCommand(CanExecute = nameof(CanSave))]
    private void SaveWithValidation() { }

    private bool CanSave() => !string.IsNullOrEmpty(FirstName);
}
```

## View Binding

```xml
<Page x:Class="MyApp.Views.MainPage"
      xmlns:vm="clr-namespace:MyApp.ViewModels"
      d:DataContext="{d:DesignInstance Type=vm:MainViewModel}">

    <!-- Text binding -->
    <TextBlock Text="{Binding Title}" />

    <!-- Two-way binding for input -->
    <TextBox Text="{Binding FirstName, UpdateSourceTrigger=PropertyChanged}" />

    <!-- Command binding -->
    <Button Content="Save" Command="{Binding SaveCommand}" />

    <!-- Async command with loading state -->
    <Button Content="Load"
            Command="{Binding LoadDataCommand}"
            IsEnabled="{Binding LoadDataCommand.IsRunning, Converter={StaticResource InverseBool}}" />

    <!-- Collection binding -->
    <ListView ItemsSource="{Binding Items}" SelectedItem="{Binding SelectedItem}">
        <ListView.ItemTemplate>
            <DataTemplate>
                <TextBlock Text="{Binding Name}" />
            </DataTemplate>
        </ListView.ItemTemplate>
    </ListView>
</Page>
```

## Dependency Injection

```csharp
// App.xaml.cs - Setup DI container
public partial class App : Application
{
    public static IServiceProvider Services { get; private set; } = null!;

    protected override void OnStartup(StartupEventArgs e)
    {
        var services = new ServiceCollection();

        // Register services
        services.AddSingleton<IDatabaseService, DatabaseService>();
        services.AddSingleton<INavigationService, NavigationService>();

        // Register ViewModels
        services.AddTransient<MainViewModel>();
        services.AddTransient<SettingsViewModel>();

        // Register Views
        services.AddTransient<MainWindow>();

        Services = services.BuildServiceProvider();

        var mainWindow = Services.GetRequiredService<MainWindow>();
        mainWindow.Show();
    }
}
```

## Navigation Pattern

```csharp
public interface INavigationService
{
    void NavigateTo<TViewModel>() where TViewModel : ObservableObject;
    void GoBack();
}

public partial class ShellViewModel : ObservableObject
{
    private readonly INavigationService _navigation;

    [ObservableProperty]
    private ObservableObject? _currentViewModel;

    [RelayCommand]
    private void NavigateToSettings()
    {
        _navigation.NavigateTo<SettingsViewModel>();
    }
}
```

## Observable Collections

```csharp
public partial class ListViewModel : ObservableObject
{
    // Use ObservableCollection for lists that change
    public ObservableCollection<Item> Items { get; } = new();

    [ObservableProperty]
    private Item? _selectedItem;

    [RelayCommand]
    private void AddItem()
    {
        Items.Add(new Item { Name = "New Item" });
    }

    [RelayCommand]
    private void RemoveSelected()
    {
        if (SelectedItem != null)
        {
            Items.Remove(SelectedItem);
            SelectedItem = null;
        }
    }
}
```

## Messaging (Loose Coupling)

```csharp
// Define message
public record ItemSavedMessage(Item Item);

// Send message
WeakReferenceMessenger.Default.Send(new ItemSavedMessage(item));

// Receive message (in ViewModel constructor)
WeakReferenceMessenger.Default.Register<ItemSavedMessage>(this, (r, m) =>
{
    // Handle message
    Items.Add(m.Item);
});
```

## Best Practices

1. **ViewModels should not reference Views** - Use interfaces/services
2. **Use [ObservableProperty]** - Avoid manual INotifyPropertyChanged
3. **Use [RelayCommand]** - Avoid manual ICommand implementations
4. **Inject services** - Don't create dependencies in ViewModels
5. **Keep Views dumb** - Logic belongs in ViewModels
6. **Use Messenger for cross-ViewModel communication**
7. **Async commands for I/O** - Keep UI responsive

## Testing ViewModels

```csharp
[Fact]
public async Task LoadDataCommand_PopulatesItems()
{
    // Arrange
    var mockService = new Mock<IDataService>();
    mockService.Setup(s => s.GetItemsAsync())
        .ReturnsAsync(new[] { new Item { Name = "Test" } });

    var vm = new MainViewModel(mockService.Object);

    // Act
    await vm.LoadDataCommand.ExecuteAsync(null);

    // Assert
    Assert.Single(vm.Items);
    Assert.Equal("Test", vm.Items[0].Name);
}
```

## NuGet Packages

```xml
<PackageReference Include="CommunityToolkit.Mvvm" Version="8.*" />
<PackageReference Include="Microsoft.Extensions.DependencyInjection" Version="8.*" />
```

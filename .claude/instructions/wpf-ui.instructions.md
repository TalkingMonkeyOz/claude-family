---
description: 'WPF UI library quick-reference: Essential patterns, gotchas, and setup for Fluent Design WPF apps'
applyTo: '**/*.xaml,**/Views/**/*.cs,**/ViewModels/**/*.cs,**/Windows/**/*.cs'
source: 'github.com/lepoco/wpfui + Claude Family'
version: '2.0'
---

# WPF UI Quick Reference

**For comprehensive patterns, see**: `.claude/skills/wpf-ui/SKILL.md`
**Examples**: `.claude/skills/wpf-ui/examples/`

---

## Critical Setup (Do This First!)

### App.xaml - REQUIRED

```xml
<Application xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml">
    <Application.Resources>
        <ResourceDictionary>
            <ResourceDictionary.MergedDictionaries>
                <ui:ThemesDictionary Theme="Dark" />
                <ui:ControlsDictionary />
            </ResourceDictionary.MergedDictionaries>
        </ResourceDictionary>
    </Application.Resources>
</Application>
```

**Without this, controls won't style correctly!**

---

## Essential Patterns

### 1. Use FluentWindow (Not Window)

```xml
<ui:FluentWindow x:Class="YourApp.MainWindow"
    xmlns:ui="http://schemas.lepo.co/wpfui/2022/xaml"
    ExtendsContentIntoTitleBar="True"
    WindowBackdropType="Mica">

    <ui:TitleBar Title="My App" Grid.Row="0" />
    <!-- Content -->
</ui:FluentWindow>
```

**Code-behind**: Inherit from `FluentWindow`, not `Window`

### 2. NavigationView for Multi-Page Apps

```xml
<ui:NavigationView x:Name="RootNavigation" PaneDisplayMode="Left">
    <ui:NavigationView.MenuItems>
        <ui:NavigationViewItem Content="Dashboard"
                               Icon="{ui:SymbolIcon Home24}"
                               TargetPageType="{x:Type pages:DashboardPage}" />
    </ui:NavigationView.MenuItems>
</ui:NavigationView>
```

### 3. Cards for Content Grouping

```xml
<!-- Simple card -->
<ui:Card Padding="16">
    <TextBlock Text="Content" />
</ui:Card>

<!-- Expandable card -->
<ui:CardExpander Header="Options" IsExpanded="True">
    <ui:ToggleSwitch Content="Setting" />
</ui:CardExpander>

<!-- Clickable card -->
<ui:CardAction Command="{Binding OpenCommand}">
    <TextBlock Text="Click me" />
</ui:CardAction>
```

---

## Theme Management

### Runtime Theme Switching

```csharp
using Wpf.Ui.Appearance;

// Apply theme with backdrop
ApplicationThemeManager.Apply(ApplicationTheme.Dark, WindowBackdropType.Mica);

// Auto-sync with Windows theme
SystemThemeWatcher.Watch(this);  // In FluentWindow constructor
```

### Backdrop Types (Windows 11)

- `Mica` - Subtle tinted (default)
- `Acrylic` - Transparent/blurred
- `Tabbed` - Blurred wallpaper
- `None` - Solid background

---

## Common Controls

### Buttons

```xml
<ui:Button Content="Save" Appearance="Primary" Icon="{ui:SymbolIcon Save24}" />
<ui:Button Content="Delete" Appearance="Danger" Icon="{ui:SymbolIcon Delete24}" />
<ui:Button Content="Cancel" Appearance="Secondary" />
```

**Appearances**: Primary, Secondary, Danger, Transparent

### Inputs

```xml
<ui:TextBox PlaceholderText="Name" Icon="{ui:SymbolIcon Person24}" />
<ui:PasswordBox PlaceholderText="Password" />
<ui:NumberBox Value="{Binding Count}" Minimum="0" Maximum="100" />
<ui:AutoSuggestBox PlaceholderText="Search..." />
```

### Notifications

```xml
<!-- Snackbar (toast) -->
<ui:Snackbar x:Name="NotificationBar" />
```

```csharp
NotificationBar.Show("Success", "Saved!", ControlAppearance.Success);
```

```xml
<!-- InfoBar (persistent) -->
<ui:InfoBar Title="Warning"
            Message="Cannot undo this action"
            Severity="Warning"
            IsOpen="True" />
```

**Severities**: Informational, Success, Warning, Error

---

## Icons

```xml
<ui:SymbolIcon Symbol="Home24" />
<ui:SymbolIcon Symbol="Settings24" />
<ui:SymbolIcon Symbol="Add24" />
<ui:SymbolIcon Symbol="Delete24" />
<ui:SymbolIcon Symbol="CheckmarkCircle24" />
<ui:SymbolIcon Symbol="Warning24" />
```

**Sizes**: 12, 16, 20, 24, 28, 32, 48
**Find icons**: https://github.com/microsoft/fluentui-system-icons

---

## Dashboard/Stats Pattern

```xml
<!-- Stats card grid (4 columns) -->
<UniformGrid Rows="1" Columns="4" Margin="16">
    <ui:Card Margin="0,0,8,0">
        <StackPanel>
            <ui:SymbolIcon Symbol="People24" FontSize="24"
                           Foreground="{ui:ThemeResource SystemAccentColorPrimaryBrush}" />
            <TextBlock Text="Total Users" FontSize="12"
                       Foreground="{ui:ThemeResource TextFillColorSecondaryBrush}" />
            <TextBlock Text="1,234" FontSize="32" FontWeight="Bold" />
        </StackPanel>
    </ui:Card>
    <!-- More cards... -->
</UniformGrid>
```

**See full pattern**: `.claude/skills/wpf-ui/SKILL.md` (Dashboard Layout section)

---

## Theme Resources

```xml
<!-- Text colors -->
<TextBlock Foreground="{ui:ThemeResource TextFillColorPrimaryBrush}" />
<TextBlock Foreground="{ui:ThemeResource TextFillColorSecondaryBrush}" />

<!-- Status colors -->
<TextBlock Foreground="{ui:ThemeResource SystemFillColorSuccessBrush}" />
<TextBlock Foreground="{ui:ThemeResource SystemFillColorCautionBrush}" />
<TextBlock Foreground="{ui:ThemeResource SystemFillColorCriticalBrush}" />

<!-- Background -->
<Border Background="{ui:ThemeResource CardBackgroundFillColorDefaultBrush}" />
<Border Background="{ui:ThemeResource ApplicationBackgroundBrush}" />
```

**Never hardcode colors!** Use dynamic theme resources.

---

## MVVM with DI (Production Apps)

```csharp
// App.xaml.cs
services.AddSingleton<INavigationService, NavigationService>();
services.AddSingleton<ISnackbarService, SnackbarService>();
services.AddSingleton<IContentDialogService, ContentDialogService>();

// MainWindow constructor
public MainWindow(
    MainWindowViewModel viewModel,
    INavigationService navigationService)
{
    ViewModel = viewModel;
    DataContext = this;
    InitializeComponent();
    navigationService.SetNavigationControl(RootNavigation);
}
```

**See full setup**: `.claude/skills/wpf-ui/SKILL.md` (MVVM section)

---

## Common Gotchas

### 1. Controls Not Styling

**Problem**: Controls look like default WPF
**Solution**: Check App.xaml has `ThemesDictionary` and `ControlsDictionary`

### 2. Window Doesn't Match Windows 11

**Problem**: Window looks like Windows 10
**Solution**: Use `ui:FluentWindow`, set `ExtendsContentIntoTitleBar="True"` and `WindowBackdropType="Mica"`

### 3. Navigation Not Working

**Problem**: Pages not loading in NavigationView
**Solution**:
- Set `TargetPageType="{x:Type pages:YourPage}"`
- Call `navigationService.SetNavigationControl(RootNavigation)`
- Ensure pages are registered in DI

### 4. Theme Not Switching

**Problem**: Theme change doesn't apply
**Solution**: Use `ApplicationThemeManager.Apply()`, not just changing `ThemesDictionary`

### 5. Backdrop Not Showing

**Problem**: Mica/Acrylic not visible
**Solution**: Requires Windows 11. Check OS version, gracefully degrade to `None` on Windows 10

### 6. Icons Not Found

**Problem**: `Symbol="SomeName24"` throws error
**Solution**: Check icon exists at https://github.com/microsoft/fluentui-system-icons. Include size suffix (24, 32, etc.)

---

## When to Use What

| Need | Use | Don't Use |
|------|-----|-----------|
| Window | `ui:FluentWindow` | `Window` |
| Main navigation | `ui:NavigationView` | `TabControl`, `Menu` |
| Content grouping | `ui:Card` | `GroupBox`, `Border` |
| Toast notification | `ui:Snackbar` | `MessageBox` |
| Persistent message | `ui:InfoBar` | `Label` with color |
| Primary action | `ui:Button Appearance="Primary"` | Styled `Button` |
| Stats display | `ui:Card` in `UniformGrid` | Plain `TextBlock` |
| Collapsible section | `ui:CardExpander` | `Expander` |

---

## Project Structure

```
YourApp/
├── App.xaml (theme setup)
├── Views/
│   ├── Windows/MainWindow.xaml
│   └── Pages/
│       ├── DashboardPage.xaml
│       └── SettingsPage.xaml
├── ViewModels/
│   ├── MainWindowViewModel.cs
│   └── DashboardViewModel.cs
└── Services/
```

---

## Resources

- **Full Skill**: `.claude/skills/wpf-ui/SKILL.md`
- **Examples**: `.claude/skills/wpf-ui/examples/`
- **Docs**: https://wpfui.lepo.co/
- **Icons**: https://github.com/microsoft/fluentui-system-icons
- **Gallery Source**: https://github.com/lepoco/wpfui/tree/main/src/Wpf.Ui.Gallery

---

**Version**: 2.0 (Focused quick-reference, comprehensive skill available)
**Created**: 2025-10-21
**Updated**: 2025-12-26
**Lines**: ~200

---
description: 'WinForms dark theme implementation patterns'
applyTo: '**/Forms/**/*.cs,**/Controls/**/*.cs,**/*Form.cs,**/*Control.cs'
source: 'Claude Family (original)'
---

# WinForms Dark Theme Guidelines

## Color Palette

Use these standard dark theme colors:

| Element | Light Mode | Dark Mode | Notes |
|---------|------------|-----------|-------|
| Background | `#FFFFFF` | `#1E1E1E` | Main form background |
| Surface | `#F5F5F5` | `#252526` | Panels, cards |
| Surface Alt | `#E8E8E8` | `#2D2D30` | Alternate rows, hover |
| Text Primary | `#1A1A1A` | `#CCCCCC` | Main text |
| Text Secondary | `#666666` | `#9D9D9D` | Labels, hints |
| Border | `#D0D0D0` | `#3F3F46` | Control borders |
| Accent | `#0078D4` | `#0078D4` | Links, selection |
| Error | `#D32F2F` | `#F44336` | Error states |
| Success | `#388E3C` | `#4CAF50` | Success states |

## Contrast Requirements (WCAG AA)

- **Normal text**: 4.5:1 minimum contrast ratio
- **Large text** (18px+ bold, 24px+ regular): 3:1 minimum
- **UI components**: 3:1 minimum

```csharp
// Test contrast: #CCCCCC on #1E1E1E = 10.5:1 ✓
// Test contrast: #9D9D9D on #1E1E1E = 5.9:1 ✓
```

## Theme Manager Pattern

```csharp
public static class ThemeManager
{
    public static bool IsDarkMode { get; private set; }

    public static Color BackColor => IsDarkMode
        ? Color.FromArgb(30, 30, 30)    // #1E1E1E
        : Color.White;

    public static Color ForeColor => IsDarkMode
        ? Color.FromArgb(204, 204, 204) // #CCCCCC
        : Color.FromArgb(26, 26, 26);   // #1A1A1A

    public static Color SurfaceColor => IsDarkMode
        ? Color.FromArgb(37, 37, 38)    // #252526
        : Color.FromArgb(245, 245, 245);

    public static Color BorderColor => IsDarkMode
        ? Color.FromArgb(63, 63, 70)    // #3F3F46
        : Color.FromArgb(208, 208, 208);

    public static void ApplyTheme(Control control)
    {
        control.BackColor = BackColor;
        control.ForeColor = ForeColor;

        foreach (Control child in control.Controls)
        {
            ApplyTheme(child);
        }
    }
}
```

## DataGridView Dark Theme

```csharp
private void ApplyDarkTheme(DataGridView dgv)
{
    dgv.BackgroundColor = ThemeManager.BackColor;
    dgv.GridColor = ThemeManager.BorderColor;

    dgv.DefaultCellStyle.BackColor = ThemeManager.SurfaceColor;
    dgv.DefaultCellStyle.ForeColor = ThemeManager.ForeColor;
    dgv.DefaultCellStyle.SelectionBackColor = Color.FromArgb(0, 120, 212);
    dgv.DefaultCellStyle.SelectionForeColor = Color.White;

    dgv.AlternatingRowsDefaultCellStyle.BackColor = ThemeManager.BackColor;

    dgv.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(45, 45, 48);
    dgv.ColumnHeadersDefaultCellStyle.ForeColor = ThemeManager.ForeColor;
    dgv.EnableHeadersVisualStyles = false;

    dgv.RowHeadersDefaultCellStyle.BackColor = Color.FromArgb(45, 45, 48);
}
```

## Button Styling

```csharp
private void StyleButton(Button btn, bool isPrimary = false)
{
    btn.FlatStyle = FlatStyle.Flat;
    btn.FlatAppearance.BorderColor = ThemeManager.BorderColor;
    btn.FlatAppearance.BorderSize = 1;

    if (isPrimary)
    {
        btn.BackColor = Color.FromArgb(0, 120, 212); // Accent
        btn.ForeColor = Color.White;
    }
    else
    {
        btn.BackColor = ThemeManager.SurfaceColor;
        btn.ForeColor = ThemeManager.ForeColor;
    }
}
```

## TextBox/ComboBox Styling

```csharp
private void StyleTextBox(TextBox txt)
{
    txt.BackColor = ThemeManager.SurfaceColor;
    txt.ForeColor = ThemeManager.ForeColor;
    txt.BorderStyle = BorderStyle.FixedSingle;
}

private void StyleComboBox(ComboBox cbo)
{
    cbo.BackColor = ThemeManager.SurfaceColor;
    cbo.ForeColor = ThemeManager.ForeColor;
    cbo.FlatStyle = FlatStyle.Flat;
}
```

## System Theme Detection (.NET 5+)

```csharp
using Microsoft.Win32;

public static bool IsSystemDarkMode()
{
    try
    {
        using var key = Registry.CurrentUser.OpenSubKey(
            @"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize");
        var value = key?.GetValue("AppsUseLightTheme");
        return value is int i && i == 0;
    }
    catch
    {
        return false;
    }
}
```

## Common Gotchas

1. **EnableHeadersVisualStyles = false** required for DataGridView header colors
2. **FlatStyle.Flat** required for button color customization
3. **BorderStyle.FixedSingle** for TextBox to show in dark mode
4. MenuStrip/ToolStrip need custom renderer for dark theme
5. TreeView/ListView BackColor works, but node colors need individual handling

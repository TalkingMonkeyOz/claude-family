---
description: 'WinForms development rules and best practices'
applyTo: '**/*.Designer.cs,**/Forms/**/*.cs,**/Controls/**/*.cs'
source: 'Claude Family (original)'
---

# WinForms Development Guidelines

## CRITICAL RULES

1. **NEVER directly edit .Designer.cs files** unless explicitly asked
2. Designer files are auto-generated - manual edits get overwritten
3. If you must edit Designer.cs, understand serialization rules below

## Designer.cs Serialization Rules

The Designer uses `CodeDOM` serialization with strict rules:

**ALLOWED in Designer.cs:**
- Simple property assignments: `this.button1.Text = "Click";`
- Object creation: `new System.Drawing.Point(10, 20)`
- Array initializers: `new string[] { "A", "B" }`
- Event handler assignment: `this.button1.Click += Button1_Click;`

**NOT ALLOWED in Designer.cs:**
- Lambda expressions: `() => { }`
- Control flow: `if`, `for`, `switch`
- Method calls (except specific patterns)
- String interpolation: `$"text"`
- LINQ expressions

## Layout Strategy (Priority Order)

1. **TableLayoutPanel** - Grid-based layouts
   - Use `AutoSize` for content-fitting
   - Use `Percent` for proportional sizing
   - Use `Absolute` only when necessary

2. **FlowLayoutPanel** - Button bars, tag lists
   - Set `WrapContents` appropriately
   - Use for horizontal/vertical flow

3. **Dock** - Edge and fill layouts
   - `Dock.Fill` for content areas
   - Dock order matters (first docked = outermost)

4. **Anchor** - Edge-relative positioning
   - Use for controls that should stretch with form

**Avoid:** Absolute positioning with `Location` property

## Control Naming Conventions

| Prefix | Control Type |
|--------|-------------|
| btn | Button |
| txt | TextBox |
| lbl | Label |
| cbo | ComboBox |
| chk | CheckBox |
| rad | RadioButton |
| dgv | DataGridView |
| lst | ListBox |
| pnl | Panel |
| grp | GroupBox |
| tab | TabControl |
| pic | PictureBox |
| prg | ProgressBar |
| tmr | Timer |

## Async Patterns in WinForms

```csharp
// Always wrap async event handlers in try/catch
private async void btnLoad_Click(object sender, EventArgs e)
{
    try
    {
        btnLoad.Enabled = false;
        var data = await LoadDataAsync();
        dgvResults.DataSource = data;
    }
    catch (Exception ex)
    {
        MessageBox.Show($"Error: {ex.Message}", "Error",
            MessageBoxButtons.OK, MessageBoxIcon.Error);
    }
    finally
    {
        btnLoad.Enabled = true;
    }
}
```

## Cross-Thread UI Updates (.NET 9+)

```csharp
// Use InvokeAsync for cross-thread updates
await this.InvokeAsync(() => {
    lblStatus.Text = "Updated from background thread";
});
```

## Data Binding

- Use `BindingSource` for complex binding scenarios
- Set `DataSource` after configuring columns
- Handle `DataError` event on DataGridView
- Use `INotifyPropertyChanged` for two-way binding

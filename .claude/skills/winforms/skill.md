---
name: winforms
description: WinForms development patterns and Designer file rules
model: haiku
agent: winforms-coder-haiku
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# WinForms Development Skill

**When to Use**: Working on Windows Forms applications

---

## Critical Rules

1. **NEVER** directly edit `.Designer.cs` files unless explicitly asked
2. Designer code follows **serialization rules** - no lambdas, no control flow
3. Regular code can use **modern C# features**
4. Prefer **layout controls** over absolute positioning

---

## Quick Patterns

### Layout

```csharp
// TableLayoutPanel for forms
tableLayoutPanel1.RowStyles.Add(new RowStyle(SizeType.AutoSize));  // Labels
tableLayoutPanel1.RowStyles.Add(new RowStyle(SizeType.Percent, 100));  // Content
tableLayoutPanel1.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));  // Labels
tableLayoutPanel1.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));  // Inputs

// FlowLayoutPanel for buttons (right-to-left)
flowLayoutPanel1.FlowDirection = FlowDirection.RightToLeft;
flowLayoutPanel1.Dock = DockStyle.Bottom;

// Responsive controls
textBox1.Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top;
dataGridView1.Dock = DockStyle.Fill;
```

### Async Event Handlers

```csharp
private async void btnProcess_Click(object sender, EventArgs e)
{
    try
    {
        btnProcess.Enabled = false;
        await DoWorkAsync();
    }
    catch (Exception ex)
    {
        MessageBox.Show($"Error: {ex.Message}");
    }
    finally
    {
        btnProcess.Enabled = true;
    }
}
```

### Cross-Thread UI (.NET 9+)

```csharp
await control.InvokeAsync(() => label1.Text = "Updated!");
```

---

## Naming Conventions

| Control | Prefix | Example |
|---------|--------|---------|
| Button | btn | btnSave |
| TextBox | txt | txtName |
| Label | lbl | lblTitle |
| ComboBox | cbo | cboCountry |
| CheckBox | chk | chkActive |
| DataGridView | dgv | dgvOrders |

---

## Workflow

1. **Read** existing `.Designer.cs` to understand structure
2. **Identify** if changes need designer or code-behind
3. For **designer changes**: Guide user to use VS Designer
4. For **code changes**: Edit the `.cs` file directly
5. **Test** with `dotnet build` to catch errors

---

## Related Knowledge

- `knowledge-vault/20-Domains/WinForms/winforms-designer-rules.md`
- `knowledge-vault/20-Domains/WinForms/winforms-layout-patterns.md`
- `knowledge-vault/20-Domains/WinForms/winforms-async-patterns.md`
- `knowledge-vault/20-Domains/WinForms/winforms-databinding.md`

---

## Spawn Agent

For complex WinForms tasks, spawn:
```
mcp__orchestrator__spawn_agent(agent_type="winforms-coder-haiku", task="...")
```

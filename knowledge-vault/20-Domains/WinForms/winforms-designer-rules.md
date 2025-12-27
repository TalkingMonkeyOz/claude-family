---
synced: true
synced_at: '2025-12-21T14:40:40.021101'
tags:
- winforms
- domain-knowledge
projects:
- claude-family-manager-v2
- mission-control-web
---

# WinForms Designer Rules

**Category**: winforms
**Tags**: #winforms #designer #csharp #critical

---

## Critical Rule

**NEVER directly edit .Designer.cs files unless explicitly asked by the user.**

Designer files are auto-generated and follow strict serialization rules.

---

## Two Contexts Principle

| Context | Rules Apply | Features Allowed |
|---------|-------------|------------------|
| Designer code (.Designer.cs, InitializeComponent) | Serialization rules | Limited, strict |
| Regular code (.cs) | Modern C# | Full language features |

---

## Prohibited in InitializeComponent

These will break the designer:

- Control flow: `if`, `for`, `foreach`, `while`, `switch`, `try/catch`
- Ternary operators: `? :`
- Null coalescing: `??`, `?.`, `?[]`
- Lambdas and local functions
- Collection expressions
- Complex logic or method definitions

---

## Required InitializeComponent Structure

```csharp
private void InitializeComponent()
{
    // 1. Instantiate controls
    this.button1 = new Button();
    this.textBox1 = new TextBox();

    // 2. Create components container
    this.components = new System.ComponentModel.Container();

    // 3. Suspend layout
    this.SuspendLayout();

    // 4. Configure controls (properties only)
    this.button1.Location = new Point(10, 10);
    this.button1.Name = "button1";
    this.button1.Size = new Size(75, 23);
    this.button1.Click += new EventHandler(this.button1_Click);

    // 5. Configure Form/UserControl LAST
    this.Controls.Add(this.button1);
    this.Name = "Form1";

    // 6. Resume layout
    this.ResumeLayout(false);
    this.PerformLayout();
}

// 7. Backing fields at end of file
private Button button1;
private TextBox textBox1;
```

---

## Event Binding Rules

**Allowed**: Method references only
```csharp
this.button1.Click += new EventHandler(this.button1_Click);
```

**NOT Allowed**: Lambdas
```csharp
// WRONG - will break designer
this.button1.Click += (s, e) => DoSomething();
```

---

## Naming Conventions

| Control Type | Prefix | Example |
|--------------|--------|---------|
| Button | btn | btnSave, btnCancel |
| TextBox | txt | txtCustomerName |
| Label | lbl | lblTitle |
| ComboBox | cbo | cboCountry |
| CheckBox | chk | chkActive |
| DataGridView | dgv | dgvOrders |
| Panel | pnl | pnlHeader |
| GroupBox | grp | grpSettings |

---

## What To Do Instead

When user asks to modify a form:

1. **Read** the .Designer.cs to understand current structure
2. **Describe** the changes needed
3. **Guide** the user to make changes in VS Designer
4. **Only edit** if user explicitly says "edit the designer file"

---

**Version**: 1.0
**Source**: GitHub awesome-copilot WinFormsExpert.agent.md
---
synced: true
synced_at: '2025-12-21T14:40:40.022781'
---

# WinForms Layout Patterns

**Category**: winforms
**Tags**: #winforms #layout #tablelayoutpanel #responsive

---

## Layout Control Hierarchy

Prefer layout controls over absolute positioning:

| Control | Use Case | Resizing |
|---------|----------|----------|
| TableLayoutPanel | Grid layouts, forms | Excellent |
| FlowLayoutPanel | Button bars, dynamic lists | Good |
| SplitContainer | Resizable panels | Excellent |
| Panel + Dock/Anchor | Simple layouts | Good |

---

## TableLayoutPanel Best Practices

### Row/Column Sizing Priority

1. **AutoSize** - Fits content (preferred for labels, buttons)
2. **Percent** - Proportional sizing (preferred for content areas)
3. **Absolute** - Fixed pixels (use sparingly)

### Structure Guidelines

- Keep grids to **2-4 columns** for readability
- Use **nested TableLayoutPanels** for logical sections
- Set minimum **3px margins** on cells
- **Padding has no effect** in TLP cells - use margins

### Container Sizing

```csharp
// GroupBox/Panel inside TLP
groupBox1.AutoSize = true;
groupBox1.AutoSizeMode = AutoSizeMode.GrowOnly;
// Parent TLP row should be AutoSize to prevent clipping
```

---

## Dock and Anchor

### Dock (fills container edge)

```csharp
// Fill entire container
control.Dock = DockStyle.Fill;

// Dock to edges
control.Dock = DockStyle.Top;    // Header
control.Dock = DockStyle.Bottom; // Status bar
control.Dock = DockStyle.Left;   // Sidebar
```

### Anchor (maintains distance from edges)

```csharp
// Stretch horizontally with form
textBox.Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top;

// Stay in bottom-right corner
button.Anchor = AnchorStyles.Bottom | AnchorStyles.Right;

// Stretch in all directions
dataGridView.Anchor = AnchorStyles.Top | AnchorStyles.Bottom
                    | AnchorStyles.Left | AnchorStyles.Right;
```

---

## Modal Dialog Button Placement

### Bottom-Right Buttons (OK/Cancel)

```csharp
// Use FlowLayoutPanel
flowLayoutPanel1.FlowDirection = FlowDirection.RightToLeft;
flowLayoutPanel1.Dock = DockStyle.Bottom;
flowLayoutPanel1.AutoSize = true;

// Add buttons (they appear right-to-left)
flowLayoutPanel1.Controls.Add(btnCancel);  // Rightmost
flowLayoutPanel1.Controls.Add(btnOK);      // Left of Cancel
```

### Top-Right Stacked Buttons

```csharp
flowLayoutPanel1.FlowDirection = FlowDirection.TopDown;
flowLayoutPanel1.Dock = DockStyle.Right;
```

---

## Dark Mode (.NET 9+)

```csharp
// Check dark mode
if (Application.IsDarkModeEnabled)
{
    // Use appropriate colors for owner-draw controls
}

// SystemColors auto-adjust, but custom painting needs handling
```

---

## Common Layout Patterns

### Form with Header, Content, Footer

```
┌─────────────────────────┐
│ Header (Dock.Top)       │
├─────────────────────────┤
│                         │
│ Content (Dock.Fill)     │
│                         │
├─────────────────────────┤
│ Footer (Dock.Bottom)    │
└─────────────────────────┘
```

### Settings Form (Label + Control Grid)

```
┌────────────┬────────────────────┐
│ Label:     │ [TextBox          ]│  AutoSize | Percent
├────────────┼────────────────────┤
│ Label:     │ [ComboBox    ▼   ]│  AutoSize | Percent
├────────────┼────────────────────┤
│ Label:     │ [x] CheckBox      │  AutoSize | AutoSize
└────────────┴────────────────────┘
```

---

**Version**: 1.0
**Source**: GitHub awesome-copilot WinFormsExpert.agent.md
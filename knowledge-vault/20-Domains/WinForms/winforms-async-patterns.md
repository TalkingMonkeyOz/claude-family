---
synced: true
synced_at: '2025-12-21T14:40:40.017207'
---

# WinForms Async Patterns

**Category**: winforms
**Tags**: #winforms #async #threading #dotnet9

---

## Critical Rule

**Always wrap async event handlers in try/catch to prevent crashes.**

```csharp
private async void button1_Click(object sender, EventArgs e)
{
    try
    {
        await DoWorkAsync();
    }
    catch (Exception ex)
    {
        MessageBox.Show($"Error: {ex.Message}");
        // Or log and handle appropriately
    }
}
```

Unhandled exceptions in async void methods crash the process.

---

## InvokeAsync (.NET 9+)

### Overloads

| Method | Use Case |
|--------|----------|
| `InvokeAsync(Action)` | Sync action on UI thread |
| `InvokeAsync(Func<CancellationToken, ValueTask>)` | Async operation, no return |
| `InvokeAsync<T>(Func<T>)` | Sync function returning T |
| `InvokeAsync<T>(Func<CancellationToken, ValueTask<T>>)` | Async operation returning T |

### Examples

```csharp
// Update UI from background thread
await control.InvokeAsync(() =>
{
    label1.Text = "Updated!";
});

// Async operation on UI thread
await control.InvokeAsync(async ct =>
{
    await Task.Delay(100, ct);
    label1.Text = "Done";
});

// Get value from UI thread
string text = await control.InvokeAsync(() => textBox1.Text);
```

---

## ShowAsync / ShowDialogAsync (.NET 9+)

```csharp
// Show form and wait for close
var form = new ChildForm();
await form.ShowAsync();
// Continues after form closes

// Modal dialog
var dialog = new SettingsDialog();
DialogResult result = await dialog.ShowDialogAsync();
if (result == DialogResult.OK)
{
    // Apply settings
}
```

---

## Background Work Pattern

```csharp
private async void btnProcess_Click(object sender, EventArgs e)
{
    try
    {
        btnProcess.Enabled = false;
        progressBar1.Visible = true;

        var progress = new Progress<int>(percent =>
        {
            progressBar1.Value = percent;
        });

        await Task.Run(() => DoHeavyWork(progress));

        MessageBox.Show("Complete!");
    }
    catch (Exception ex)
    {
        MessageBox.Show($"Error: {ex.Message}");
    }
    finally
    {
        btnProcess.Enabled = true;
        progressBar1.Visible = false;
    }
}

private void DoHeavyWork(IProgress<int> progress)
{
    for (int i = 0; i <= 100; i++)
    {
        Thread.Sleep(50); // Simulate work
        progress.Report(i);
    }
}
```

---

## Exception Handling

### Application-Level Handlers

```csharp
// Program.cs
Application.ThreadException += (s, e) =>
{
    // UI thread exceptions - can prevent crash
    LogError(e.Exception);
    MessageBox.Show("An error occurred.");
};

AppDomain.CurrentDomain.UnhandledException += (s, e) =>
{
    // Any thread - cannot prevent termination
    LogError((Exception)e.ExceptionObject);
};
```

### Preserving Stack Trace in Async

```csharp
catch (Exception ex)
{
    // Preserve original stack trace
    ExceptionDispatchInfo.Capture(ex).Throw();
}
```

---

## CancellationToken Pattern

```csharp
private CancellationTokenSource? _cts;

private async void btnStart_Click(object sender, EventArgs e)
{
    _cts = new CancellationTokenSource();

    try
    {
        await LongRunningOperationAsync(_cts.Token);
    }
    catch (OperationCanceledException)
    {
        lblStatus.Text = "Cancelled";
    }
}

private void btnCancel_Click(object sender, EventArgs e)
{
    _cts?.Cancel();
}

private async Task LongRunningOperationAsync(CancellationToken ct)
{
    for (int i = 0; i < 100; i++)
    {
        ct.ThrowIfCancellationRequested();
        await Task.Delay(100, ct);
    }
}
```

---

**Version**: 1.0
**Source**: GitHub awesome-copilot WinFormsExpert.agent.md
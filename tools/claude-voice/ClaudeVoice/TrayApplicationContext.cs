using ClaudeVoice.Services;

namespace ClaudeVoice;

/// <summary>
/// System tray application context. No visible form - just tray icon + context menu.
/// </summary>
public class TrayApplicationContext : ApplicationContext
{
    private readonly NotifyIcon _trayIcon;
    private readonly SpeechService _speechService;
    private readonly WezTermService _wezTermService;
    private readonly HotkeyForm _hotkeyForm;
    private readonly ToolStripMenuItem _voiceToggleItem;
    private readonly ToolStripMenuItem _statusItem;
    private SynchronizationContext? _syncContext;
    private bool _voiceEnabled = true;
    private bool _isListening;

    public TrayApplicationContext()
    {
        // SynchronizationContext may not exist yet; will be captured on first use
        _syncContext = SynchronizationContext.Current;

        _speechService = new SpeechService("en-AU");
        _wezTermService = new WezTermService();

        // Status display (non-clickable)
        _statusItem = new ToolStripMenuItem("Initializing...")
        {
            Enabled = false
        };

        _voiceToggleItem = new ToolStripMenuItem("Voice Input: ON", null, OnToggleVoice)
        {
            Checked = true
        };

        var contextMenu = new ContextMenuStrip();
        contextMenu.Items.Add(_statusItem);
        contextMenu.Items.Add(new ToolStripSeparator());
        contextMenu.Items.Add(_voiceToggleItem);
        contextMenu.Items.Add(new ToolStripSeparator());
        contextMenu.Items.Add("Exit", null, OnExit);

        _trayIcon = new NotifyIcon
        {
            Icon = CreateIcon(Color.Gray),
            Text = "Claude Voice - Initializing",
            ContextMenuStrip = contextMenu,
            Visible = true
        };

        // Hidden form to receive hotkey messages
        _hotkeyForm = new HotkeyForm();
        _hotkeyForm.HotkeyPressed += OnHotkeyPressed;
        _hotkeyForm.HotkeyReleased += OnHotkeyReleased;

        // Wire up speech events
        _speechService.HypothesisGenerated += OnHypothesis;
        _speechService.ResultGenerated += OnResult;
        _speechService.SessionCompleted += OnSessionCompleted;
        _speechService.Error += OnSpeechError;

        _ = InitializeAsync();
    }

    private async Task InitializeAsync()
    {
        try
        {
            await _speechService.InitializeAsync();

            bool wezAvailable = WezTermService.IsAvailable();

            var hotkey = _hotkeyForm.HotkeyDescription;
            UpdateStatus(wezAvailable
                ? $"Ready - Press {hotkey} to talk"
                : $"Ready - {hotkey} (WezTerm not detected, clipboard fallback)");

            SetTrayState(TrayState.Idle);
        }
        catch (Exception ex)
        {
            UpdateStatus($"Error: {ex.Message}");
            SetTrayState(TrayState.Error);
        }
    }

    private async void OnHotkeyPressed()
    {
        if (!_voiceEnabled || _isListening) return;

        _isListening = true;
        SetTrayState(TrayState.Listening);
        UpdateStatus("Listening...");

        try
        {
            await _speechService.StartListeningAsync();
        }
        catch (Exception ex)
        {
            UpdateStatus($"Error: {ex.Message}");
            SetTrayState(TrayState.Error);
            _isListening = false;
        }
    }

    private async void OnHotkeyReleased()
    {
        if (!_isListening) return;

        try
        {
            await _speechService.StopListeningAsync();
        }
        catch
        {
            // StopListening handles its own errors
        }
    }

    private void OnHypothesis(string text)
    {
        RunOnUI(() =>
        {
            _trayIcon.Text = $"Claude Voice - Hearing: {Truncate(text, 50)}";
            _trayIcon.ShowBalloonTip(1000, "Hearing...", text, ToolTipIcon.Info);
        });
    }

    private async void OnResult(string text)
    {
        RunOnUI(() =>
        {
            _trayIcon.ShowBalloonTip(3000, "Recognized", text, ToolTipIcon.Info);
            UpdateStatus($"Sent: {Truncate(text, 40)}");
        });

        bool sent = await _wezTermService.SendTextAsync(text);

        RunOnUI(() =>
        {
            if (sent)
            {
                _trayIcon.ShowBalloonTip(2000, "Sent to WezTerm", text, ToolTipIcon.Info);
            }
            else
            {
                Clipboard.SetText(text);
                _trayIcon.ShowBalloonTip(3000, "Copied to Clipboard",
                    $"{text}\n(WezTerm send failed - text is in your clipboard, Ctrl+V to paste)",
                    ToolTipIcon.Warning);
            }
        });
    }

    private void OnSessionCompleted()
    {
        _isListening = false;
        RunOnUI(() =>
        {
            SetTrayState(TrayState.Idle);
            UpdateStatus("Ready - Press {_hotkeyForm.HotkeyDescription} to talk");
        });
    }

    private void OnSpeechError(string error)
    {
        RunOnUI(() =>
        {
            UpdateStatus($"Error: {Truncate(error, 50)}");
            SetTrayState(TrayState.Error);
        });
    }

    private void OnToggleVoice(object? sender, EventArgs e)
    {
        _voiceEnabled = !_voiceEnabled;
        _voiceToggleItem.Text = _voiceEnabled ? "Voice Input: ON" : "Voice Input: OFF";
        _voiceToggleItem.Checked = _voiceEnabled;
        SetTrayState(_voiceEnabled ? TrayState.Idle : TrayState.Disabled);
    }

    private void OnExit(object? sender, EventArgs e)
    {
        _speechService.Dispose();
        _hotkeyForm.Dispose();
        _trayIcon.Visible = false;
        _trayIcon.Dispose();
        Application.Exit();
    }

    private void UpdateStatus(string status)
    {
        _statusItem.Text = Truncate(status, 60);
        _trayIcon.Text = $"Claude Voice - {Truncate(status, 50)}";
    }

    private void RunOnUI(Action action)
    {
        // Lazily capture the sync context once it's available
        _syncContext ??= SynchronizationContext.Current;

        if (_syncContext != null)
            _syncContext.Post(_ => action(), null);
        else
            action(); // Direct call as fallback
    }

    private enum TrayState { Idle, Listening, Error, Disabled }

    private void SetTrayState(TrayState state)
    {
        var color = state switch
        {
            TrayState.Idle => Color.FromArgb(100, 200, 100),      // Green
            TrayState.Listening => Color.FromArgb(100, 150, 255),  // Blue
            TrayState.Error => Color.FromArgb(255, 100, 100),      // Red
            TrayState.Disabled => Color.Gray,
            _ => Color.Gray
        };

        _trayIcon.Icon = CreateIcon(color);
    }

    private static Icon CreateIcon(Color color)
    {
        var bitmap = new Bitmap(16, 16);
        using var g = Graphics.FromImage(bitmap);
        g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
        g.Clear(Color.Transparent);

        // Microphone body
        using var brush = new SolidBrush(color);
        g.FillEllipse(brush, 4, 1, 8, 9);

        // Stand
        using var pen = new Pen(color, 1.5f);
        g.DrawArc(pen, 3, 5, 10, 8, 0, 180);
        g.DrawLine(pen, 8, 13, 8, 15);
        g.DrawLine(pen, 5, 15, 11, 15);

        return Icon.FromHandle(bitmap.GetHicon());
    }

    private static string Truncate(string text, int maxLength)
    {
        return text.Length <= maxLength ? text : text[..(maxLength - 3)] + "...";
    }
}

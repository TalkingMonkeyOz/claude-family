using ClaudeVoice.Services;
using System.Runtime.InteropServices;

namespace ClaudeVoice;

/// <summary>
/// Invisible form that receives global hotkey WM_HOTKEY messages.
/// Uses toggle mode: first press starts listening, second press stops.
/// RegisterHotKey doesn't support key-up events, so toggle is the reliable approach.
/// </summary>
public class HotkeyForm : Form
{
    private const int HOTKEY_ID = 9001;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    private const uint MOD_NONE = 0x0000;
    private const int WM_HOTKEY = 0x0312;

    private bool _isActive;
    private bool _registered;

    public event Action? HotkeyPressed;
    public event Action? HotkeyReleased;

    public string HotkeyDescription { get; private set; } = "None";

    public HotkeyForm()
    {
        // Invisible form
        ShowInTaskbar = false;
        WindowState = FormWindowState.Minimized;
        FormBorderStyle = FormBorderStyle.None;
        Opacity = 0;

        // Try hotkeys in order of preference until one works
        var candidates = new (uint mod, Keys key, string name)[]
        {
            (MOD_NONE, Keys.F9, "F9"),
            (0x0002 | 0x0004, Keys.Space, "Ctrl+Shift+Space"),  // MOD_CONTROL | MOD_SHIFT
            (0x0002 | 0x0001, Keys.Space, "Ctrl+Alt+Space"),    // MOD_CONTROL | MOD_ALT
            (MOD_NONE, Keys.F8, "F8"),
        };

        foreach (var (mod, key, name) in candidates)
        {
            if (RegisterHotKey(Handle, HOTKEY_ID, mod, (uint)key))
            {
                _registered = true;
                HotkeyDescription = name;
                break;
            }
        }

        if (!_registered)
        {
            MessageBox.Show(
                "Failed to register any hotkey (F9, Ctrl+Shift+Space, Ctrl+Alt+Space, F8).\n" +
                "All key combinations may be in use by other applications.",
                "Claude Voice", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == WM_HOTKEY && m.WParam.ToInt32() == HOTKEY_ID)
        {
            if (!_isActive)
            {
                _isActive = true;
                HotkeyPressed?.Invoke();
            }
            else
            {
                _isActive = false;
                HotkeyReleased?.Invoke();
            }
            return;
        }

        base.WndProc(ref m);
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            UnregisterHotKey(Handle, HOTKEY_ID);
        }
        base.Dispose(disposing);
    }

    // Prevent the form from showing
    protected override void SetVisibleCore(bool value)
    {
        base.SetVisibleCore(false);
    }
}

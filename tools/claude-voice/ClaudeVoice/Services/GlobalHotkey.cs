using System.Runtime.InteropServices;

namespace ClaudeVoice.Services;

/// <summary>
/// Manages global hotkey registration via Win32 RegisterHotKey API.
/// </summary>
public sealed class GlobalHotkey : IDisposable
{
    private const int WM_HOTKEY = 0x0312;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    // Modifier flags
    public const uint MOD_NONE = 0x0000;
    public const uint MOD_ALT = 0x0001;
    public const uint MOD_CONTROL = 0x0002;
    public const uint MOD_SHIFT = 0x0004;
    public const uint MOD_WIN = 0x0008;

    private readonly int _id;
    private readonly IntPtr _hwnd;
    private bool _disposed;

    public event Action? Pressed;

    public GlobalHotkey(IntPtr hwnd, int id, uint modifiers, Keys key)
    {
        _hwnd = hwnd;
        _id = id;

        if (!RegisterHotKey(hwnd, id, modifiers, (uint)key))
        {
            int error = Marshal.GetLastWin32Error();
            throw new InvalidOperationException(
                $"Failed to register hotkey (error {error}). The key combination may already be in use.");
        }
    }

    public bool ProcessMessage(ref Message m)
    {
        if (m.Msg == WM_HOTKEY && m.WParam.ToInt32() == _id)
        {
            Pressed?.Invoke();
            return true;
        }
        return false;
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            UnregisterHotKey(_hwnd, _id);
            _disposed = true;
        }
    }
}

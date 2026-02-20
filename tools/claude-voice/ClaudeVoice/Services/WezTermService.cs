using System.Diagnostics;

namespace ClaudeVoice.Services;

/// <summary>
/// Sends recognized text to WezTerm terminal panes.
/// </summary>
public class WezTermService
{
    private string? _targetPaneId;

    public string? TargetPaneId
    {
        get => _targetPaneId;
        set => _targetPaneId = value;
    }

    /// <summary>
    /// Send text to the active WezTerm pane (or a specific pane if configured).
    /// </summary>
    public async Task<bool> SendTextAsync(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return false;

        try
        {
            var args = "cli send-text --no-paste";
            if (!string.IsNullOrEmpty(_targetPaneId))
                args += $" --pane-id {_targetPaneId}";

            var psi = new ProcessStartInfo
            {
                FileName = "wezterm",
                Arguments = args,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var process = Process.Start(psi);
            if (process == null)
                return false;

            await process.StandardInput.WriteAsync(text);
            process.StandardInput.Close();

            await process.WaitForExitAsync();
            return process.ExitCode == 0;
        }
        catch (Exception ex)
        {
            Debug.WriteLine($"WezTerm send failed: {ex.Message}");
            return false;
        }
    }

    /// <summary>
    /// Check if WezTerm CLI is available.
    /// </summary>
    public static bool IsAvailable()
    {
        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = "wezterm",
                Arguments = "cli list",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var process = Process.Start(psi);
            if (process == null) return false;
            process.WaitForExit(3000);
            return process.ExitCode == 0;
        }
        catch
        {
            return false;
        }
    }
}

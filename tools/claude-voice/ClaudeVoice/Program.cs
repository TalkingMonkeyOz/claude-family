namespace ClaudeVoice;

static class Program
{
    [STAThread]
    static void Main()
    {
        // Single instance check
        using var mutex = new Mutex(true, "ClaudeVoice_SingleInstance", out bool isNew);
        if (!isNew)
        {
            MessageBox.Show("Claude Voice is already running.", "Claude Voice",
                MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        ApplicationConfiguration.Initialize();
        Application.Run(new TrayApplicationContext());
    }
}

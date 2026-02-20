using System.Globalization;
using System.Speech.Recognition;

namespace ClaudeVoice.Services;

/// <summary>
/// Speech recognition using System.Speech (SAPI 5.4).
/// Works offline, no privacy settings needed, reliable on desktop WinForms.
/// </summary>
public sealed class SpeechService : IDisposable
{
    private SpeechRecognitionEngine? _engine;
    private bool _isListening;
    private bool _disposed;
    private readonly string _language;

    public event Action<string>? HypothesisGenerated;
    public event Action<string>? ResultGenerated;
    public event Action? SessionCompleted;
    public event Action<string>? Error;

    public bool IsListening => _isListening;

    public SpeechService(string language = "en-AU")
    {
        _language = language;
    }

    public Task InitializeAsync()
    {
        try
        {
            // Try to create engine with requested culture, fall back to default
            CultureInfo culture;
            try
            {
                culture = new CultureInfo(_language);
            }
            catch
            {
                culture = CultureInfo.CurrentCulture;
            }

            try
            {
                _engine = new SpeechRecognitionEngine(culture);
            }
            catch
            {
                // If requested culture not available, use system default
                _engine = new SpeechRecognitionEngine();
            }

            // Load free-form dictation grammar
            _engine.LoadGrammar(new DictationGrammar());

            // Use default audio input (system microphone)
            _engine.SetInputToDefaultAudioDevice();

            // Wire up events
            _engine.SpeechHypothesized += OnHypothesized;
            _engine.SpeechRecognized += OnRecognized;
            _engine.RecognizeCompleted += OnCompleted;

            // Timeouts
            _engine.InitialSilenceTimeout = TimeSpan.FromSeconds(15);
            _engine.BabbleTimeout = TimeSpan.FromSeconds(10);
            _engine.EndSilenceTimeout = TimeSpan.FromSeconds(1);
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Speech init failed:\n\n{ex.GetType().Name}: {ex.Message}\n\nMake sure a microphone is connected.",
                "Claude Voice - Init Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            Error?.Invoke($"Speech init failed: {ex.Message}");
            throw;
        }

        return Task.CompletedTask;
    }

    public Task StartListeningAsync()
    {
        if (_engine == null)
            throw new InvalidOperationException("SpeechService not initialized.");

        if (_isListening) return Task.CompletedTask;

        try
        {
            // RecognizeAsync with Multiple mode keeps recognizing until cancelled
            _engine.RecognizeAsync(RecognizeMode.Multiple);
            _isListening = true;
        }
        catch (Exception ex)
        {
            _isListening = false;
            MessageBox.Show(
                $"Start listening failed:\n\n{ex.GetType().Name}: {ex.Message}",
                "Claude Voice - Speech Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            Error?.Invoke($"Start listening failed: {ex.Message}");
        }

        return Task.CompletedTask;
    }

    public Task StopListeningAsync()
    {
        if (_engine == null || !_isListening) return Task.CompletedTask;

        try
        {
            _engine.RecognizeAsyncCancel();
        }
        catch (Exception ex)
        {
            Error?.Invoke($"Stop listening failed: {ex.Message}");
        }
        finally
        {
            _isListening = false;
            SessionCompleted?.Invoke();
        }

        return Task.CompletedTask;
    }

    private void OnHypothesized(object? sender, SpeechHypothesizedEventArgs e)
    {
        if (!string.IsNullOrWhiteSpace(e.Result?.Text))
        {
            HypothesisGenerated?.Invoke(e.Result.Text);
        }
    }

    private void OnRecognized(object? sender, SpeechRecognizedEventArgs e)
    {
        if (e.Result?.Text != null && e.Result.Confidence > 0.3f)
        {
            ResultGenerated?.Invoke(e.Result.Text);
        }
    }

    private void OnCompleted(object? sender, RecognizeCompletedEventArgs e)
    {
        _isListening = false;

        if (e.Error != null)
        {
            Error?.Invoke($"Recognition error: {e.Error.Message}");
        }

        SessionCompleted?.Invoke();
    }

    public void Dispose()
    {
        if (!_disposed)
        {
            if (_isListening)
            {
                try { _engine?.RecognizeAsyncCancel(); } catch { }
            }
            _engine?.Dispose();
            _disposed = true;
        }
    }
}

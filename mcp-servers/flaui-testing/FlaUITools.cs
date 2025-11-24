using System.ComponentModel;
using System.Text.Json;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Conditions;
using FlaUI.Core.Definitions;
using FlaUI.UIA3;
using ModelContextProtocol.Server;
using FlaUIApp = FlaUI.Core.Application;

[McpServerToolType]
public class FlaUITools
{
    private readonly DatabaseService _db;
    private readonly AppConfiguration _config;

    public FlaUITools(DatabaseService db, AppConfiguration config)
    {
        _db = db;
        _config = config;
    }

    [McpServerTool, Description("Create a new UI test and store it in the database")]
    public async Task<CreateTestResponse> CreateTest(
        string testName,
        string description,
        string stepsJson,
        string? category = null,
        string? assertionsJson = null,
        string? tagsJson = null)
    {
        try
        {
            var steps = JsonDocument.Parse(stepsJson);
            var assertions = assertionsJson != null ? JsonDocument.Parse(assertionsJson) : null;
            var tags = tagsJson != null ? JsonSerializer.Deserialize<string[]>(tagsJson) : null;

            var testId = await _db.CreateTest(testName, description, category ?? "general", steps, assertions, tags);

            return new CreateTestResponse
            {
                Success = true,
                TestId = testId.ToString(),
                Message = $"Test '{testName}' created successfully for project '{_config.ProjectName}'"
            };
        }
        catch (Exception ex)
        {
            return new CreateTestResponse
            {
                Success = false,
                Message = $"Failed to create test: {ex.Message}"
            };
        }
    }

    [McpServerTool, Description("Execute a UI test by ID or name")]
    public async Task<RunTestResponse> RunTest(string testIdOrName)
    {
        var startTime = DateTime.Now;
        string? screenshotPath = null;
        var stepsExecuted = new List<StepResult>();

        try
        {
            // Load test from database
            Guid testId;
            TestScript? test;

            if (Guid.TryParse(testIdOrName, out testId))
            {
                test = await _db.GetTest(testId);
            }
            else
            {
                // TODO: Add GetTestByName method to DatabaseService
                return new RunTestResponse
                {
                    Success = false,
                    Message = "Searching by test name not yet implemented - please use test ID"
                };
            }

            if (test == null)
            {
                return new RunTestResponse
                {
                    Success = false,
                    Message = $"Test not found: {testIdOrName}"
                };
            }

            // Parse test steps
            var steps = JsonSerializer.Deserialize<TestStep[]>(test.TestSteps);
            if (steps == null || steps.Length == 0)
            {
                return new RunTestResponse
                {
                    Success = false,
                    Message = "Test has no steps defined"
                };
            }

            // Execute test
            using var automation = new UIA3Automation();
            FlaUIApp? app = null;

            foreach (var step in steps)
            {
                var stepResult = new StepResult { Action = step.Action };

                try
                {
                    switch (step.Action.ToLower())
                    {
                        case "launch_app":
                            app = FlaUIApp.Launch(step.ExePath!);
                            System.Threading.Thread.Sleep(2000); // Wait for app to initialize
                            stepResult.Success = true;
                            stepResult.Message = $"Launched {step.ExePath}";
                            break;

                        case "find_element":
                            if (app == null) throw new Exception("App not launched");
                            var window = app.GetMainWindow(automation);
                            var element = FindElement(window, step.AutomationId!, step.Timeout ?? 5000);
                            stepResult.Success = element != null;
                            stepResult.Message = element != null
                                ? $"Found element {step.AutomationId}"
                                : $"Element {step.AutomationId} not found";
                            break;

                        case "click":
                            if (app == null) throw new Exception("App not launched");
                            var clickWindow = app.GetMainWindow(automation);
                            var clickElement = FindElement(clickWindow, step.AutomationId!, step.Timeout ?? 5000);
                            if (clickElement == null) throw new Exception($"Element {step.AutomationId} not found");
                            clickElement.Click();
                            stepResult.Success = true;
                            stepResult.Message = $"Clicked {step.AutomationId}";
                            break;

                        case "type_text":
                            if (app == null) throw new Exception("App not launched");
                            var typeWindow = app.GetMainWindow(automation);
                            var textElement = FindElement(typeWindow, step.AutomationId!, step.Timeout ?? 5000);
                            if (textElement == null) throw new Exception($"Element {step.AutomationId} not found");

                            textElement.Focus();
                            System.Threading.Thread.Sleep(100);
                            textElement.AsTextBox().Text = step.Text!;
                            stepResult.Success = true;
                            stepResult.Message = $"Typed text into {step.AutomationId}";
                            break;

                        case "assert_element_exists":
                            if (app == null) throw new Exception("App not launched");
                            var assertWindow = app.GetMainWindow(automation);
                            var assertElement = FindElement(assertWindow, step.AutomationId!, step.Timeout ?? 10000);
                            stepResult.Success = assertElement != null;
                            stepResult.Message = assertElement != null
                                ? $"Assertion passed: {step.AutomationId} exists"
                                : $"Assertion failed: {step.AutomationId} not found";
                            break;

                        case "wait":
                            System.Threading.Thread.Sleep(step.WaitMs ?? 1000);
                            stepResult.Success = true;
                            stepResult.Message = $"Waited {step.WaitMs}ms";
                            break;

                        default:
                            stepResult.Success = false;
                            stepResult.Message = $"Unknown action: {step.Action}";
                            break;
                    }
                }
                catch (Exception ex)
                {
                    stepResult.Success = false;
                    stepResult.Message = ex.Message;

                    // Take screenshot on failure
                    if (app != null)
                    {
                        screenshotPath = TakeScreenshot(app, test.TestId);
                    }
                }

                stepsExecuted.Add(stepResult);

                // Stop on first failure
                if (!stepResult.Success)
                {
                    break;
                }
            }

            // Cleanup
            app?.Close();

            // Calculate duration
            var duration = (int)(DateTime.Now - startTime).TotalMilliseconds;

            // Determine overall status
            var allPassed = stepsExecuted.All(s => s.Success);
            var status = allPassed ? "passed" : "failed";

            // Save results to database
            var stepsJson = JsonSerializer.Serialize(stepsExecuted);
            var stepsDoc = JsonDocument.Parse(stepsJson);
            var resultId = await _db.SaveTestResult(
                test.TestId,
                status,
                duration,
                allPassed ? null : stepsExecuted.FirstOrDefault(s => !s.Success)?.Message,
                screenshotPath,
                stepsDoc
            );

            return new RunTestResponse
            {
                Success = allPassed,
                ResultId = resultId.ToString(),
                Status = status,
                DurationMs = duration,
                StepsExecuted = stepsExecuted.Count,
                ScreenshotPath = screenshotPath,
                Message = allPassed
                    ? $"Test passed! {stepsExecuted.Count} steps completed in {duration}ms"
                    : $"Test failed at step {stepsExecuted.Count}: {stepsExecuted.Last().Message}"
            };
        }
        catch (Exception ex)
        {
            var duration = (int)(DateTime.Now - startTime).TotalMilliseconds;

            return new RunTestResponse
            {
                Success = false,
                Status = "error",
                DurationMs = duration,
                Message = $"Test execution error: {ex.Message}",
                ScreenshotPath = screenshotPath
            };
        }
    }

    [McpServerTool, Description("List all tests for this project")]
    public string ListTests(string? category = null)
    {
        // TODO: Implement when needed
        return $"List tests not yet implemented. Project: {_config.ProjectName}, Category: {category ?? "all"}";
    }

    [McpServerTool, Description("Get test execution results")]
    public string GetResults(string? testId = null, int limit = 10)
    {
        // TODO: Implement when needed
        return $"Get results not yet implemented. TestId: {testId ?? "all"}, Limit: {limit}";
    }

    [McpServerTool, Description("Find UI elements for debugging")]
    public string FindElements(string? automationId = null, string? controlType = null)
    {
        // TODO: Implement when needed
        return $"Find elements not yet implemented. AutomationId: {automationId}, ControlType: {controlType}";
    }

    [McpServerTool, Description("Take a screenshot of the current application")]
    public string TakeScreenshot(string windowTitle)
    {
        // TODO: Implement when needed
        return $"Screenshot not yet implemented for window: {windowTitle}";
    }

    // Helper methods
    private AutomationElement? FindElement(Window window, string automationId, int timeoutMs)
    {
        var endTime = DateTime.Now.AddMilliseconds(timeoutMs);

        while (DateTime.Now < endTime)
        {
            var element = window.FindFirstDescendant(cf => cf.ByAutomationId(automationId));
            if (element != null)
            {
                return element;
            }

            System.Threading.Thread.Sleep(500);
        }

        return null;
    }

    private string TakeScreenshot(FlaUIApp app, Guid testId)
    {
        try
        {
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd_HH-mm-ss");
            var directory = Path.Combine("C:\\Projects\\test-screenshots", _config.ProjectName, testId.ToString());
            Directory.CreateDirectory(directory);

            var filename = $"{timestamp}_failure.png";
            var fullPath = Path.Combine(directory, filename);

            var window = app.GetMainWindow(new UIA3Automation());
            var screenshot = window.Capture();
            screenshot.Save(fullPath);

            return fullPath;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Failed to take screenshot: {ex.Message}");
            return $"screenshot_failed_{ex.Message}";
        }
    }
}

// Request/Response models
public class CreateTestResponse
{
    public bool Success { get; set; }
    public string? TestId { get; set; }
    public string Message { get; set; } = string.Empty;
}

public class RunTestResponse
{
    public bool Success { get; set; }
    public string? ResultId { get; set; }
    public string Status { get; set; } = string.Empty;
    public int DurationMs { get; set; }
    public int StepsExecuted { get; set; }
    public string? ScreenshotPath { get; set; }
    public string Message { get; set; } = string.Empty;
}

// Test step model
public class TestStep
{
    public string Action { get; set; } = string.Empty;
    public string? ExePath { get; set; }
    public string? AutomationId { get; set; }
    public string? Text { get; set; }
    public int? Timeout { get; set; }
    public int? WaitMs { get; set; }
}

public class StepResult
{
    public string Action { get; set; } = string.Empty;
    public bool Success { get; set; }
    public string Message { get; set; } = string.Empty;
}

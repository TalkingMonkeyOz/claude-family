using Npgsql;
using System.Text.Json;

public class DatabaseService
{
    private readonly string _connectionString;
    private readonly string _projectName;

    public DatabaseService(AppConfiguration config)
    {
        _connectionString = config.DatabaseConnectionString;
        _projectName = config.ProjectName;
    }

    public async Task<Guid> CreateTest(string testName, string description, string category, JsonDocument steps, JsonDocument? assertions = null, string[]? tags = null)
    {
        await using var conn = new NpgsqlConnection(_connectionString);
        await conn.OpenAsync();

        var testId = Guid.NewGuid();
        var sql = @"
            INSERT INTO claude_family.ui_test_scripts
            (test_id, project_name, test_name, description, category, test_steps, assertions, tags, created_at)
            VALUES (@id, @project, @name, @desc, @category, @steps, @assertions, @tags, NOW())
            RETURNING test_id";

        await using var cmd = new NpgsqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("id", testId);
        cmd.Parameters.AddWithValue("project", _projectName);
        cmd.Parameters.AddWithValue("name", testName);
        cmd.Parameters.AddWithValue("desc", description ?? (object)DBNull.Value);
        cmd.Parameters.AddWithValue("category", category ?? (object)DBNull.Value);
        cmd.Parameters.AddWithValue("steps", NpgsqlTypes.NpgsqlDbType.Jsonb, steps.RootElement.ToString());

        if (assertions != null)
        {
            cmd.Parameters.AddWithValue("assertions", NpgsqlTypes.NpgsqlDbType.Jsonb, assertions.RootElement.ToString());
        }
        else
        {
            cmd.Parameters.AddWithValue("assertions", DBNull.Value);
        }

        cmd.Parameters.AddWithValue("tags", tags ?? (object)DBNull.Value);

        var result = await cmd.ExecuteScalarAsync();
        return (Guid)result!;
    }

    public async Task<TestScript?> GetTest(Guid testId)
    {
        await using var conn = new NpgsqlConnection(_connectionString);
        await conn.OpenAsync();

        var sql = @"
            SELECT test_id, test_name, description, category, test_steps, assertions, tags
            FROM claude_family.ui_test_scripts
            WHERE test_id = @id AND is_active = true";

        await using var cmd = new NpgsqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("id", testId);

        await using var reader = await cmd.ExecuteReaderAsync();
        if (await reader.ReadAsync())
        {
            return new TestScript
            {
                TestId = reader.GetGuid(0),
                TestName = reader.GetString(1),
                Description = reader.IsDBNull(2) ? null : reader.GetString(2),
                Category = reader.IsDBNull(3) ? null : reader.GetString(3),
                TestSteps = reader.GetString(4),
                Assertions = reader.IsDBNull(5) ? null : reader.GetString(5),
                Tags = reader.IsDBNull(6) ? null : (string[])reader.GetValue(6)
            };
        }

        return null;
    }

    public async Task<Guid> SaveTestResult(Guid testId, string status, int durationMs, string? errorMessage, string? screenshotPath, JsonDocument stepsExecuted)
    {
        await using var conn = new NpgsqlConnection(_connectionString);
        await conn.OpenAsync();

        var resultId = Guid.NewGuid();
        var sql = @"
            INSERT INTO claude_family.ui_test_results
            (result_id, test_id, status, duration_ms, error_message, screenshot_path, steps_executed, run_at)
            VALUES (@id, @testId, @status, @duration, @error, @screenshot, @steps, NOW())
            RETURNING result_id";

        await using var cmd = new NpgsqlCommand(sql, conn);
        cmd.Parameters.AddWithValue("id", resultId);
        cmd.Parameters.AddWithValue("testId", testId);
        cmd.Parameters.AddWithValue("status", status);
        cmd.Parameters.AddWithValue("duration", durationMs);
        cmd.Parameters.AddWithValue("error", errorMessage ?? (object)DBNull.Value);
        cmd.Parameters.AddWithValue("screenshot", screenshotPath ?? (object)DBNull.Value);
        cmd.Parameters.AddWithValue("steps", NpgsqlTypes.NpgsqlDbType.Jsonb, stepsExecuted.RootElement.ToString());

        var result = await cmd.ExecuteScalarAsync();
        return (Guid)result!;
    }
}

public class TestScript
{
    public Guid TestId { get; set; }
    public string TestName { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string? Category { get; set; }
    public string TestSteps { get; set; } = string.Empty;
    public string? Assertions { get; set; }
    public string[]? Tags { get; set; }
}

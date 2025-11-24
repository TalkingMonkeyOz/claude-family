using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using ModelContextProtocol;

var builder = Host.CreateApplicationBuilder(args);

// Get configuration from command line args
var projectName = args.Contains("--project") ? args[Array.IndexOf(args, "--project") + 1] : "unknown";
var dbConnection = args.Contains("--db-connection") ? args[Array.IndexOf(args, "--db-connection") + 1] : "postgresql://postgres:password@localhost/ai_company_foundation";

// Configure services
builder.Services.AddSingleton(new AppConfiguration
{
    ProjectName = projectName,
    DatabaseConnectionString = dbConnection
});

builder.Services.AddSingleton<DatabaseService>();

// Configure MCP Server
builder.Services
    .AddMcpServer()
    .WithStdioServerTransport()
    .WithToolsFromAssembly(); // Auto-discover tools with [McpServerTool] attribute

await builder.Build().RunAsync();

public class AppConfiguration
{
    public string ProjectName { get; set; } = string.Empty;
    public string DatabaseConnectionString { get; set; } = string.Empty;
}

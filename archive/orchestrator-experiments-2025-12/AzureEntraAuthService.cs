using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Data.SqlClient;
using Newtonsoft.Json;

namespace NimbusUserLoader.Services
{
    /// <summary>
    /// Azure Entra Device Code Flow authentication service for SQL access.
    /// Implements OAuth2 Device Code Flow for MFA-enabled Azure AD accounts.
    /// </summary>
    public class AzureEntraAuthService
    {
        // Azure Entra constants
        private const string AZURE_SQL_SCOPE = "https://database.windows.net/.default";
        private const string AZURE_CLI_CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46";
        private const string AZURE_COMMON_TENANT = "common";
        private const string DEVICE_CODE_ENDPOINT = "https://login.microsoftonline.com/{0}/oauth2/v2.0/devicecode";
        private const string TOKEN_ENDPOINT = "https://login.microsoftonline.com/{0}/oauth2/v2.0/token";

        // Poll timings
        private const int DEFAULT_POLL_INTERVAL_MS = 1000;
        private const int DEFAULT_TIMEOUT_SECONDS = 900; // 15 minutes

        private readonly HttpClient _httpClient;
        private readonly string _tenantId;

        public AzureEntraAuthService(string tenantId = AZURE_COMMON_TENANT)
        {
            _httpClient = new HttpClient();
            _tenantId = tenantId;
        }

        /// <summary>
        /// Interface for progress reporting during authentication flow.
        /// </summary>
        public interface IAuthenticationProgress
        {
            void ReportDeviceCode(string userCode, string verificationUri);
            void ReportPollingStarted();
            void ReportPollingProgress(int secondsElapsed);
            void ReportAuthenticationComplete();
            void ReportError(string errorMessage);
        }

        /// <summary>
        /// Authenticates user via Device Code Flow and returns an access token.
        /// </summary>
        /// <param name="progress">Optional progress reporter</param>
        /// <param name="cancellationToken">Cancellation token for the operation</param>
        /// <returns>Access token for SQL connection</returns>
        public async Task<string> AuthenticateAsync(
            IAuthenticationProgress progress = null,
            CancellationToken cancellationToken = default)
        {
            try
            {
                // Step 1: Request device code from Azure
                var deviceCodeResponse = await GetDeviceCodeAsync(cancellationToken);
                
                // Step 2: Report user code and verification URI
                progress?.ReportDeviceCode(
                    deviceCodeResponse.UserCode,
                    deviceCodeResponse.VerificationUri);

                // Step 3: Poll for token completion
                progress?.ReportPollingStarted();
                var accessToken = await PollForTokenAsync(
                    deviceCodeResponse,
                    progress,
                    cancellationToken);

                progress?.ReportAuthenticationComplete();
                return accessToken;
            }
            catch (OperationCanceledException)
            {
                progress?.ReportError("Authentication was cancelled");
                throw;
            }
            catch (Exception ex)
            {
                progress?.ReportError($"Authentication failed: {ex.Message}");
                throw;
            }
        }

        /// <summary>
        /// Gets a device code from Azure AD.
        /// </summary>
        private async Task<DeviceCodeResponse> GetDeviceCodeAsync(CancellationToken cancellationToken)
        {
            var endpoint = string.Format(DEVICE_CODE_ENDPOINT, _tenantId);
            
            var requestBody = new Dictionary<string, string>
            {
                { "client_id", AZURE_CLI_CLIENT_ID },
                { "scope", AZURE_SQL_SCOPE }
            };

            var request = new HttpRequestMessage(HttpMethod.Post, endpoint)
            {
                Content = new FormUrlEncodedContent(requestBody)
            };

            var response = await _httpClient.SendAsync(request, cancellationToken);
            response.EnsureSuccessStatusCode();

            var responseContent = await response.Content.ReadAsStringAsync();
            var deviceCodeResponse = JsonConvert.DeserializeObject<DeviceCodeResponse>(responseContent);

            if (deviceCodeResponse == null)
            {
                throw new InvalidOperationException("Failed to deserialize device code response");
            }

            return deviceCodeResponse;
        }

        /// <summary>
        /// Polls the token endpoint until authentication completes or times out.
        /// </summary>
        private async Task<string> PollForTokenAsync(
            DeviceCodeResponse deviceCodeResponse,
            IAuthenticationProgress progress,
            CancellationToken cancellationToken)
        {
            var endpoint = string.Format(TOKEN_ENDPOINT, _tenantId);
            var stopwatch = System.Diagnostics.Stopwatch.StartNew();
            var expiresIn = deviceCodeResponse.ExpiresIn ?? DEFAULT_TIMEOUT_SECONDS;

            while (stopwatch.ElapsedMilliseconds / 1000 < expiresIn)
            {
                try
                {
                    var requestBody = new Dictionary<string, string>
                    {
                        { "grant_type", "urn:ietf:params:oauth:grant-type:device_code" },
                        { "client_id", AZURE_CLI_CLIENT_ID },
                        { "device_code", deviceCodeResponse.DeviceCode }
                    };

                    var request = new HttpRequestMessage(HttpMethod.Post, endpoint)
                    {
                        Content = new FormUrlEncodedContent(requestBody)
                    };

                    var response = await _httpClient.SendAsync(request, cancellationToken);
                    var responseContent = await response.Content.ReadAsStringAsync();
                    var tokenResponse = JsonConvert.DeserializeObject<TokenResponse>(responseContent);

                    if (tokenResponse == null)
                    {
                        throw new InvalidOperationException("Failed to deserialize token response");
                    }

                    // Check for authorization_pending
                    if (tokenResponse.Error == "authorization_pending")
                    {
                        progress?.ReportPollingProgress((int)(stopwatch.ElapsedMilliseconds / 1000));
                        
                        // Wait before next poll
                        var interval = deviceCodeResponse.Interval ?? DEFAULT_POLL_INTERVAL_MS;
                        await Task.Delay(interval, cancellationToken);
                        continue;
                    }

                    // Check for errors
                    if (!string.IsNullOrEmpty(tokenResponse.Error))
                    {
                        throw new InvalidOperationException(
                            $"Authentication error: {tokenResponse.Error} - {tokenResponse.ErrorDescription}");
                    }

                    // Success - return access token
                    if (string.IsNullOrEmpty(tokenResponse.AccessToken))
                    {
                        throw new InvalidOperationException("No access token in response");
                    }

                    return tokenResponse.AccessToken;
                }
                catch (HttpRequestException ex)
                {
                    throw new InvalidOperationException("Failed to poll token endpoint", ex);
                }
            }

            throw new TimeoutException($"Authentication timed out after {expiresIn} seconds");
        }

        /// <summary>
        /// Creates and opens a SQL connection with the authenticated token.
        /// </summary>
        /// <param name="sqlConnectionString">SQL Server connection string (without credentials)</param>
        /// <param name="accessToken">Access token from authentication</param>
        /// <returns>Configured SqlConnection ready to use</returns>
        public static SqlConnection CreateSqlConnection(string sqlConnectionString, string accessToken)
        {
            if (string.IsNullOrEmpty(sqlConnectionString))
            {
                throw new ArgumentNullException(nameof(sqlConnectionString), "Connection string cannot be null or empty");
            }

            if (string.IsNullOrEmpty(accessToken))
            {
                throw new ArgumentNullException(nameof(accessToken), "Access token cannot be null or empty");
            }

            var connection = new SqlConnection(sqlConnectionString);
            connection.AccessToken = accessToken;
            return connection;
        }

        /// <summary>
        /// Response from device code endpoint.
        /// </summary>
        private class DeviceCodeResponse
        {
            [JsonProperty("device_code")]
            public string DeviceCode { get; set; }

            [JsonProperty("user_code")]
            public string UserCode { get; set; }

            [JsonProperty("verification_uri")]
            public string VerificationUri { get; set; }

            [JsonProperty("expires_in")]
            public int? ExpiresIn { get; set; }

            [JsonProperty("interval")]
            public int? Interval { get; set; }
        }

        /// <summary>
        /// Response from token endpoint.
        /// </summary>
        private class TokenResponse
        {
            [JsonProperty("access_token")]
            public string AccessToken { get; set; }

            [JsonProperty("token_type")]
            public string TokenType { get; set; }

            [JsonProperty("expires_in")]
            public int? ExpiresIn { get; set; }

            [JsonProperty("error")]
            public string Error { get; set; }

            [JsonProperty("error_description")]
            public string ErrorDescription { get; set; }
        }
    }

    /// <summary>
    /// Simple console-based progress reporter for authentication flow.
    /// Useful for testing and CLI scenarios.
    /// </summary>
    public class ConsoleAuthenticationProgress : AzureEntraAuthService.IAuthenticationProgress
    {
        public void ReportDeviceCode(string userCode, string verificationUri)
        {
            Console.WriteLine();
            Console.WriteLine("╔════════════════════════════════════════════════════════════╗");
            Console.WriteLine("║         Azure Entra Device Code Authentication            ║");
            Console.WriteLine("╚════════════════════════════════════════════════════════════╝");
            Console.WriteLine();
            Console.WriteLine($"Your device code: {userCode}");
            Console.WriteLine();
            Console.WriteLine($"Opening browser to: {verificationUri}");
            Console.WriteLine();
            Console.WriteLine("Please complete the sign-in process in your browser.");
            Console.WriteLine("This will timeout in 15 minutes if not completed.");
            Console.WriteLine();
        }

        public void ReportPollingStarted()
        {
            Console.WriteLine("Waiting for sign-in completion...");
        }

        public void ReportPollingProgress(int secondsElapsed)
        {
            // Could be noisy - optional logging
            if (secondsElapsed % 5 == 0)
            {
                Console.WriteLine($"  Still waiting... ({secondsElapsed}s)");
            }
        }

        public void ReportAuthenticationComplete()
        {
            Console.WriteLine("✓ Authentication successful!");
            Console.WriteLine();
        }

        public void ReportError(string errorMessage)
        {
            Console.WriteLine($"✗ Error: {errorMessage}");
            Console.WriteLine();
        }
    }
}

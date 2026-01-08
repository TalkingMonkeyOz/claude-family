---
category: nimbus-api
confidence: 100
created: 2026-01-07
projects:
- nimbus-mui
- nimbus-import
- nimbus-user-loader
synced: false
tags:
- nimbus
- authentication
- rest
- api
- credential-storage
title: Nimbus Authentication Flow
type: sop
source: nimbus-user-loader/Constants/ApiEndpoints.cs, NimbusConnectionManager.cs
---

# Nimbus Authentication Flow

## Summary

Nimbus uses username/password authentication via REST API. Returns `AuthenticationToken` and `UserID` for subsequent requests. Credentials stored securely in Windows Credential Manager.

## Authentication Endpoint

```http
POST {baseUrl}/RESTApi/Authenticate
Content-Type: application/json

{
  "Username": "user@example.com",
  "Password": "password123"
}
```

**CRITICAL**: Endpoint is `/RESTApi/Authenticate` NOT `/Account/Login` or `/Authentication`!

## Response Structure (PascalCase!)

```json
{
  "AuthenticationToken": "abc123...",
  "UserID": 42,
  "UserName": "user@example.com"
}
```

**TypeScript Interface**:
```typescript
interface NimbusAuthResponse {
  AuthenticationToken: string;
  UserID: number;
  UserName?: string;
}
```

## Token Usage (Headers)

All authenticated API calls require these headers:

```http
AuthenticationToken: {token}
UserID: {userId}
Authorization: Bearer {token}
```

The `Authorization: Bearer` header is also accepted as an alternative.

## OAuth2 Fallback (Cloud Instances)

Some cloud instances (e.g., `test-ssc.nimbus.cloud`) use OAuth2:

```http
POST {baseUrl}/connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=...&password=...&client_id=...&scope=NimbusAPI
```

**Fallback Logic**: If `/RESTApi/Authenticate` returns 404, try `/connect/token`.

## Credential Storage (Tauri/Rust)

Uses `keyring` crate for Windows Credential Manager:

| Field | Value |
|-------|-------|
| Service | `nimbus-mui` |
| Key | `profile:{profileName}` |
| Password | JSON: `{base_url, user_id, auth_token}` |

```rust
let entry = Entry::new("nimbus-mui", "profile:Production")?;
entry.set_password(&credentials_json)?;
```

## Auto-Login Flow

1. Load credentials from keyring by profile name
2. Test connection with simple OData query (`Users?$top=1`)
3. If valid, use stored credentials
4. If invalid/expired, delete and prompt for re-login

## Code Example (TypeScript)

```typescript
// Authenticate
const response = await invoke<HttpResponse>('execute_rest_post', {
  url: `${baseUrl}/RESTApi/Authenticate`,
  body: { Username: username, Password: password },
  headers: { 'Content-Type': 'application/json' }
});

// Parse PascalCase response
const { AuthenticationToken, UserID } = JSON.parse(response.body);

// Save to keyring
await invoke('save_credentials', {
  profileName: 'Production',
  credentials: { base_url: baseUrl, user_id: UserID, auth_token: AuthenticationToken }
});
```

## Error Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 401 | Invalid credentials |
| 404 | Wrong endpoint (check URL) |
| 500+ | Server error |

## Important Notes

- Tokens may expire - implement connection testing
- Never store passwords - only auth tokens
- Base URL must NOT have trailing slash
- PascalCase in API responses, normalize to camelCase internally

## Source Files

- `nimbus-user-loader\src\nimbus-user-loader\Constants\ApiEndpoints.cs`
- `nimbus-user-loader\src\nimbus-user-loader\NimbusConnectionManager.cs`
- `nimbus-user-loader\src\nimbus-user-loader\Services\AuthenticationService.cs`

## Related

- [[nimbus-rest-crud-pattern]]
- [[nimbus-odata-field-naming]]
- [[nimbus-api-endpoints]]

---

**Version**: 2.0 (Corrected from nimbus-user-loader source)
**Created**: 2026-01-07
**Updated**: 2026-01-07
**Location**: 20-Domains/APIs/nimbus-authentication.md

# API Standards

**Document Type**: Standard
**Version**: 1.0
**Created**: 2025-12-07
**Status**: Active
**Enforcement**: MANDATORY - All API work MUST follow these standards

---

## Purpose

Define consistent API patterns for all backend services built by Claude. These standards ensure:
- Predictable API behavior across projects
- Clear error handling and responses
- Secure and performant endpoints
- Easy client integration

---

## 1. URL Structure

### 1.1 Resource Naming

```
# Pattern: /{version}/{resource}/{id}/{sub-resource}

# Collections (plural nouns)
GET    /api/v1/users              # List users
POST   /api/v1/users              # Create user
GET    /api/v1/users/123          # Get user
PUT    /api/v1/users/123          # Update user
DELETE /api/v1/users/123          # Delete user

# Sub-resources
GET    /api/v1/users/123/sessions     # User's sessions
POST   /api/v1/users/123/sessions     # Create session for user

# Actions (when CRUD doesn't fit)
POST   /api/v1/users/123/activate     # Custom action
POST   /api/v1/reports/generate       # Trigger operation
```

**Rules:**
- Use plural nouns for resources: `/users`, `/projects`, `/sessions`
- Use lowercase with hyphens: `/build-tasks`, `/api-keys`
- No trailing slashes: `/users` not `/users/`
- No verbs in URLs (actions are exceptions): `/users` not `/getUsers`

### 1.2 Query Parameters

```
# Pagination
GET /api/v1/users?page=1&pageSize=20

# Filtering
GET /api/v1/users?status=active&role=admin

# Sorting
GET /api/v1/users?sort=created_at&order=desc
GET /api/v1/users?sort=name,created_at&order=asc,desc

# Field selection
GET /api/v1/users?fields=id,name,email

# Search
GET /api/v1/users?q=john

# Combined
GET /api/v1/users?status=active&sort=name&page=1&pageSize=20
```

---

## 2. HTTP Methods

### 2.1 Method Semantics

| Method | Purpose | Idempotent | Request Body | Success Code |
|--------|---------|------------|--------------|--------------|
| GET | Read resource | Yes | No | 200 |
| POST | Create resource | No | Yes | 201 |
| PUT | Replace resource | Yes | Yes | 200 |
| PATCH | Partial update | Yes | Yes | 200 |
| DELETE | Remove resource | Yes | No/Optional | 204 |

### 2.2 Idempotency

**Idempotent** = Same request multiple times = same result

```typescript
// GET - Always safe to retry
GET /api/v1/users/123  // Always returns same user

// PUT - Safe to retry (full replace)
PUT /api/v1/users/123  // Same data = same result

// DELETE - Safe to retry
DELETE /api/v1/users/123  // First call deletes, subsequent return 404

// POST - NOT safe to retry (may create duplicates)
POST /api/v1/users  // Each call may create new user
```

**For non-idempotent operations**, use idempotency keys:

```typescript
// Client sends unique key
POST /api/v1/payments
Headers: Idempotency-Key: abc-123-xyz

// Server stores key and result
// Same key = return cached result (no duplicate charge)
```

---

## 3. Request Format

### 3.1 Headers

```
# Required headers
Content-Type: application/json
Accept: application/json

# Authentication
Authorization: Bearer <token>

# Optional
X-Request-ID: <uuid>           # For tracing
X-Idempotency-Key: <key>       # For POST requests
```

### 3.2 Request Body (JSON)

```typescript
// POST /api/v1/users
{
  "email": "john@example.com",
  "name": "John Doe",
  "role": "user",
  "settings": {
    "notifications": true,
    "theme": "dark"
  }
}

// PATCH /api/v1/users/123 (partial update)
{
  "name": "John Smith"
  // Only changed fields
}
```

**Rules:**
- Use camelCase for JSON keys
- Send only necessary fields
- Null values explicitly remove/clear fields
- Arrays replace entirely (not merge)

---

## 4. Response Format

### 4.1 Success Responses

**Single Resource:**
```json
{
  "data": {
    "id": "123",
    "email": "john@example.com",
    "name": "John Doe",
    "createdAt": "2025-12-07T10:00:00Z",
    "updatedAt": "2025-12-07T10:00:00Z"
  }
}
```

**Collection (with pagination):**
```json
{
  "data": [
    { "id": "123", "name": "John" },
    { "id": "124", "name": "Jane" }
  ],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "totalItems": 156,
    "totalPages": 8
  }
}
```

**Created Resource:**
```json
// Status: 201 Created
// Header: Location: /api/v1/users/125
{
  "data": {
    "id": "125",
    "email": "new@example.com",
    "name": "New User",
    "createdAt": "2025-12-07T12:00:00Z"
  }
}
```

**No Content:**
```
// Status: 204 No Content
// Body: empty
```

### 4.2 Error Responses

**Standard error format:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid data",
    "details": {
      "email": "Email is required",
      "name": "Name must be at least 2 characters"
    },
    "requestId": "req-abc-123"
  }
}
```

### 4.3 HTTP Status Codes

**Success (2xx):**
| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | GET, PUT, PATCH success |
| 201 | Created | POST success |
| 204 | No Content | DELETE success |

**Client Errors (4xx):**
| Code | Meaning | When to Use |
|------|---------|-------------|
| 400 | Bad Request | Invalid JSON, missing required fields |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Valid auth but no permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate entry, version conflict |
| 422 | Unprocessable | Valid JSON but business logic fails |
| 429 | Too Many Requests | Rate limit exceeded |

**Server Errors (5xx):**
| Code | Meaning | When to Use |
|------|---------|-------------|
| 500 | Internal Error | Unexpected server failure |
| 502 | Bad Gateway | Upstream service failed |
| 503 | Service Unavailable | Server overloaded/maintenance |
| 504 | Gateway Timeout | Upstream service timeout |

---

## 5. Error Codes

### 5.1 Standard Error Codes

```typescript
const ERROR_CODES = {
  // Validation
  VALIDATION_ERROR: "Request validation failed",
  MISSING_FIELD: "Required field is missing",
  INVALID_FORMAT: "Field format is invalid",

  // Authentication
  UNAUTHORIZED: "Authentication required",
  INVALID_TOKEN: "Token is invalid or expired",

  // Authorization
  FORBIDDEN: "Permission denied",
  INSUFFICIENT_SCOPE: "Token lacks required scope",

  // Resources
  NOT_FOUND: "Resource not found",
  ALREADY_EXISTS: "Resource already exists",
  CONFLICT: "Resource conflict",

  // Rate Limiting
  RATE_LIMITED: "Too many requests",

  // Server
  INTERNAL_ERROR: "Internal server error",
  SERVICE_UNAVAILABLE: "Service temporarily unavailable",
};
```

### 5.2 Error Implementation

```typescript
// API route handler
export async function POST(req: Request) {
  try {
    const body = await req.json();

    // Validate
    const validation = validateUser(body);
    if (!validation.success) {
      return Response.json({
        error: {
          code: "VALIDATION_ERROR",
          message: "Invalid request data",
          details: validation.errors
        }
      }, { status: 400 });
    }

    // Create
    const user = await createUser(body);

    return Response.json({ data: user }, { status: 201 });

  } catch (error) {
    if (error instanceof UniqueConstraintError) {
      return Response.json({
        error: {
          code: "ALREADY_EXISTS",
          message: "User with this email already exists"
        }
      }, { status: 409 });
    }

    // Log unexpected errors
    console.error("Unexpected error:", error);

    return Response.json({
      error: {
        code: "INTERNAL_ERROR",
        message: "An unexpected error occurred"
      }
    }, { status: 500 });
  }
}
```

---

## 6. Authentication

### 6.1 Bearer Token (JWT)

```typescript
// Request
GET /api/v1/users
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

// JWT Payload
{
  "sub": "user-123",          // Subject (user ID)
  "email": "john@example.com",
  "role": "admin",
  "scope": ["read:users", "write:users"],
  "iat": 1701936000,          // Issued at
  "exp": 1701939600           // Expires at
}
```

### 6.2 API Keys

```typescript
// Request (for service-to-service)
GET /api/v1/data
X-API-Key: sk_live_abc123...

// Or in Authorization header
Authorization: ApiKey sk_live_abc123...
```

### 6.3 Auth Middleware

```typescript
export async function authMiddleware(req: Request) {
  const authHeader = req.headers.get("Authorization");

  if (!authHeader?.startsWith("Bearer ")) {
    return Response.json({
      error: { code: "UNAUTHORIZED", message: "Missing authentication" }
    }, { status: 401 });
  }

  const token = authHeader.slice(7);

  try {
    const payload = await verifyToken(token);
    return { user: payload };
  } catch (error) {
    return Response.json({
      error: { code: "INVALID_TOKEN", message: "Token is invalid or expired" }
    }, { status: 401 });
  }
}
```

---

## 7. Pagination

### 7.1 Offset-Based (Default)

```typescript
// Request
GET /api/v1/users?page=2&pageSize=20

// Response
{
  "data": [...],
  "meta": {
    "page": 2,
    "pageSize": 20,
    "totalItems": 156,
    "totalPages": 8
  }
}
```

**Limits:**
- Default pageSize: 20
- Max pageSize: 100
- Offset > 10000: Use cursor pagination

### 7.2 Cursor-Based (For Large Datasets)

```typescript
// Request
GET /api/v1/events?cursor=abc123&limit=50

// Response
{
  "data": [...],
  "meta": {
    "nextCursor": "def456",
    "hasMore": true
  }
}
```

---

## 8. Filtering and Sorting

### 8.1 Filter Syntax

```
# Equality
?status=active

# Multiple values (OR)
?status=active,pending

# Comparison (use suffix)
?created_at_gte=2025-01-01
?created_at_lte=2025-12-31
?amount_gt=100
?amount_lt=1000

# Text search
?q=john
?name_contains=smith

# Null check
?manager_id_null=true
```

### 8.2 Sort Syntax

```
# Single field
?sort=name&order=asc

# Multiple fields
?sort=status,created_at&order=asc,desc

# Shorthand (prefix with -)
?sort=-created_at,name  # desc created_at, asc name
```

---

## 9. Versioning

### 9.1 URL Versioning (Preferred)

```
/api/v1/users
/api/v2/users
```

### 9.2 Version Lifecycle

| Version State | Meaning |
|---------------|---------|
| Current | Latest stable, recommended |
| Supported | Previous version, still works |
| Deprecated | Will be removed, shows warnings |
| Sunset | Removed, returns 410 Gone |

**Deprecation header:**
```
Sunset: Sat, 01 Jun 2026 00:00:00 GMT
Deprecation: true
Link: </api/v2/users>; rel="successor-version"
```

---

## 10. Rate Limiting

### 10.1 Headers

```
# Response headers
X-RateLimit-Limit: 1000          # Max requests per window
X-RateLimit-Remaining: 998       # Remaining in current window
X-RateLimit-Reset: 1701940000    # Unix timestamp when window resets
Retry-After: 60                  # Seconds to wait (when limited)
```

### 10.2 Limits by Tier

| Tier | Rate Limit | Burst |
|------|------------|-------|
| Free | 100/hour | 10/minute |
| Pro | 1000/hour | 100/minute |
| Enterprise | 10000/hour | 1000/minute |

---

## 11. CORS

### 11.1 Headers

```typescript
// For browser clients
const corsHeaders = {
  "Access-Control-Allow-Origin": "https://app.example.com",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Access-Control-Max-Age": "86400",
};
```

### 11.2 Preflight

```typescript
// Handle OPTIONS request
export async function OPTIONS() {
  return new Response(null, {
    status: 204,
    headers: corsHeaders
  });
}
```

---

## 12. Security

### 12.1 Input Validation

```typescript
// ALWAYS validate input
const schema = z.object({
  email: z.string().email(),
  name: z.string().min(2).max(100),
  role: z.enum(["user", "admin"]),
});

const result = schema.safeParse(body);
if (!result.success) {
  // Return 400 with field errors
}
```

### 12.2 Output Sanitization

```typescript
// Never expose internal IDs or sensitive data
function sanitizeUser(user: DbUser): ApiUser {
  return {
    id: user.public_id,  // Use public ID, not DB ID
    name: user.name,
    email: user.email,
    // Don't include: password_hash, internal_notes, etc.
  };
}
```

### 12.3 SQL Injection Prevention

```typescript
// NEVER string concatenate SQL
// BAD
const sql = `SELECT * FROM users WHERE id = '${userId}'`;

// GOOD - parameterized queries
const result = await db.query(
  "SELECT * FROM users WHERE id = $1",
  [userId]
);
```

---

## Quick Reference Checklist

Before deploying an API:

- [ ] RESTful URL structure (plural nouns)
- [ ] Consistent response format (data/error/meta)
- [ ] Proper HTTP status codes
- [ ] Standard error codes and messages
- [ ] Authentication/authorization implemented
- [ ] Pagination on all list endpoints
- [ ] Input validation on all inputs
- [ ] Rate limiting configured
- [ ] CORS headers for browser clients
- [ ] No sensitive data in responses
- [ ] Parameterized SQL queries
- [ ] Request logging with IDs

---

## Related Documents

- DEVELOPMENT_STANDARDS.md - Code conventions
- DATABASE_STANDARDS.md - Database patterns
- UI_COMPONENT_STANDARDS.md - Frontend integration

---

**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-07 | Initial version |

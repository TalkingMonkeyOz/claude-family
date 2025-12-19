# Nimbus Import - LocationGroup and ScheduleGroup Commands

Integration guide for adding entity creation commands to your Tauri app.

## Overview

Two new REST API commands for Nimbus entity creation:
- `create_location_group` - Creates location groups
- `create_schedule_group` - Creates schedule groups

## Files to Create/Modify

### 1. Create `src-tauri/src/commands/entities.rs`

See `entities.rs` in this directory for the complete implementation.

Key features:
- Request/response structs with serde serialization
- Async Tauri commands with proper error handling
- Matching auth header patterns from `auth.rs`
- Unit tests for request serialization

### 2. Update `src-tauri/src/lib.rs`

Add the new commands to your invoke handler:

```rust
use commands::entities::{create_location_group, create_schedule_group};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            // ... existing commands ...
            create_location_group,
            create_schedule_group,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### 3. Update `src-tauri/src/commands/mod.rs`

Ensure entities module is declared:

```rust
pub mod auth;
pub mod entities;  // Add this line
// ... other modules ...
```

## Usage Examples

### Creating a Location Group

```rust
// From your Tauri frontend (TypeScript/JavaScript)
const response = await invoke('create_location_group', {
    baseUrl: 'https://api.nimbus.example.com',
    token: 'your-auth-token',
    request: {
        description: 'West Coast Locations',
        locationIds: [101, 102, 103]
    }
});

console.log(`Created location group: ${response.location_group_id}`);
```

### Creating a Schedule Group

```rust
const response = await invoke('create_schedule_group', {
    baseUrl: 'https://api.nimbus.example.com',
    token: 'your-auth-token',
    request: {
        description: 'Q1 2025 Schedule',
        locationGroupId: 42,
        startDate: '2025-01-01',
        endDate: '2025-03-31',
        learningPeriod: '30'
    }
});

console.log(`Created schedule group: ${response.schedule_group_id}`);
```

## API Payload Details

### LocationGroup Creation

**Endpoint**: `POST /RESTApi/LocationGroup`

**Request Body**:
```json
{
    "Description": "West Coast Locations",
    "Active": true,
    "Locations": [
        {"LocationID": 101},
        {"LocationID": 102},
        {"LocationID": 103}
    ]
}
```

**Response**:
```json
{
    "LocationGroupID": 42
}
```

### ScheduleGroup Creation

**Endpoint**: `POST /RESTApi/ScheduleGroup`

**Request Body**:
```json
{
    "Description": "Q1 2025 Schedule",
    "Active": true,
    "LocationGroupID": 42,
    "GroupStartDate": "2025-01-01",
    "GroupEndDate": "2025-03-31",
    "AdhocFields": [
        {
            "FieldName": "adhoc_LearningPeriod",
            "Value": "30"
        }
    ]
}
```

**Response**:
```json
{
    "ScheduleGroupID": 99
}
```

## Authentication Headers

Both commands send the following headers (matching `auth.rs` patterns):

```
AuthenticationToken: <token>
Authorization: Bearer <token>
Accept: application/json
Content-Type: application/json
```

## Dependencies

Ensure your `Cargo.toml` includes:

```toml
[dependencies]
tauri = { version = "1.0", features = ["shell-open"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
reqwest = { version = "0.11", features = ["json"] }
tokio = { version = "1", features = ["full"] }
```

## Error Handling

Both commands return `Result<Response, String>`:

- **Network errors**: "Failed to create [entity]: {error}"
- **API errors**: "API error (status): {response body}"
- **Parse errors**: "Failed to parse response: {error}"
- **Missing fields**: "[EntityID] not found in response"

Handle in frontend:

```javascript
try {
    const result = await invoke('create_location_group', { /* ... */ });
    console.log('Success:', result);
} catch (error) {
    console.error('Command failed:', error);
    // Show error to user
}
```

## Testing

Unit tests are included in `entities.rs`:

```bash
cargo test -p src-tauri
```

For integration testing, mock the HTTP responses:

```rust
#[tokio::test]
async fn test_create_location_group_success() {
    // Mock HTTP client setup
    // ...
}
```

## Integration with Existing Code

The implementation follows the same patterns as your existing `auth.rs`:

| Pattern | Location |
|---------|----------|
| Header construction | `entities.rs` lines 95-119 |
| Error handling | Lines 122-129 |
| Response parsing | Lines 131-139 |
| Async/await | Function signatures use `async` |
| Tauri command macro | `#[tauri::command]` decorator |

## Debugging

Enable request/response logging:

```rust
// In entities.rs, after building the request:
eprintln!("POST {}", url);
eprintln!("Headers: {:?}", headers);
eprintln!("Payload: {}", serde_json::to_string_pretty(&payload).unwrap());

// After response:
eprintln!("Status: {}", response.status());
eprintln!("Body: {}", response_body);
```

## Next Steps

1. Copy `entities.rs` to `src-tauri/src/commands/`
2. Update `lib.rs` with invoke handler registration
3. Update `commands/mod.rs` to declare the entities module
4. Run `cargo test` to verify compilation
5. Test with your frontend code
6. Add error handling UI in your Tauri app

## Notes

- Date format must be `YYYY-MM-DD` (validated in frontend)
- Location IDs and group IDs are i64 (Nimbus API standard)
- All requests require valid authentication token
- API responses assume standard Nimbus field names (LocationGroupID, ScheduleGroupID)
- The learning_period field is passed as a string to match Nimbus expectations
